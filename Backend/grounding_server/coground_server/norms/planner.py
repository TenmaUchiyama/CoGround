"""依頼（TaskRecord）から Plan の step を作る（設計ガイド §8 の PLAN の、動作計画より前の部分）。

対象は依頼したときに決めた行。行ごとに次の順で調べ、結果を行に記録する:
  1. 収納先   収納先を決める義務（placed_in）のうち、条件（Scope）と対象の両方に合うものから決める。
              「満杯なら別の箱」（条件 region_full）は、前の行までに置く物を数えたうえで、その物の空きがあるかで決める。
              手で指定した行き先（plan.place）があれば、そちらを使う
  2. 接触     物体についてのルールのうち、内容が「つかむ時点で調べる」もの（触る・持つ）を、つかむ時点の予測で判定する。
              スキルでルールを絞らない: すべてのルールを見て、内容の登録（vocabulary.py の checked）で調べる時点を決める
  2''. 置くことの禁止  内容が「置いた時点で調べる」ルールのうち収納先を決めないもの（「…には置くな」）を、計画した置き先で判定する
  2'. 経路    動作計画が「禁止に反しない経路が無い」と判定した物（route_blocks。領域への進入の禁止など）は保留
  3. 置き位置 収納先の領域の中で、ほかの物と重ならない場所を選ぶ。行の並び順（= 作業の順序）どおりに調べる:
              前の行までに動かせた物は置き先に、まだ動かしていない物・動かせない物は元の場所にあるものとして数える。
              空きが無ければ、その物は動かさない（infeasible。シンクやごみ箱などの入れ物は重なってよい）

住人がシーケンスの編集で指定した置き先（row.requested_destination）は、収納先を決めるルールと照合する。
ルールの収納先と違えば保留にする（手の指定 plan.place は、これまでどおりルールを確かめない）。

依頼の間だけのルール（origin = task。例: 全部 box_1 に入れて）は、収納先を決めるときに常設のルールより先に立つ。
合えばそれを使い、別の収納先を指していた常設のルールは row.overridden_rule_ids と step の message に残す（黙って捨てない）。
先に立つのは収納先だけ。接触の禁止・置くことの禁止は、依頼の間だけのルールがあっても、これまでどおり調べる。

行ごとの結果:
  step（ok）        つかんでよく、収納先が 1 つに決まった
  step（deferred）  保留。禁止に反する予測、判定する情報が足りない、収納先を決める取り決めが無い。
                    収納先が分かっていれば to に入れる（「指定先は上段だが、触れないので保留」を見せられる）
  step（ambiguous / unmatched）  収納先が複数ある / 収納先の領域がシーンに無い（planner.py と同じ意味）
  step（infeasible） 置き先に空きが無い（to は「置くならここ」、message に理由）
  step なし         もう収納先にある（行は done）、またはシーンに見えていない（行はそのまま）

運べない物があっても、ほかの物は個別に調べて計画する。保留した物は行に残り、依頼の未達成として数える。
"""

from __future__ import annotations

from datetime import datetime

from .. import planner
from ..models import MissingFact, Placement, Pose, SceneObject, SceneSnapshot, Step, Verdict
from .evaluate import applies, contact_trace, evaluate, placement_trace
from .model import NormRule, Tri
from .predicates import WorldSample
from .task import RouteBlock, TaskRecord, TaskRow
from .vocabulary import CONTENTS

# 計画が pending / deferred に書き換えてよい行の状態。
# 実行中・観測待ちの行は実行側が進める。配置先違い・未確認は、やり直す（exec.retry）か、収納先で観測されるまで残す
REPLANNABLE = ("pending", "deferred", "done", "failed")


def plan_task(scene: SceneSnapshot, norms: list[NormRule], task: TaskRecord, placements: dict[str, str] | None = None,
              *, now: datetime | None = None, route_blocks: dict[str, RouteBlock] | None = None,
              only_ruled: bool = False) -> list[Step]:
    """only_ruled = True なら、収納先を決める取り決めがどれも当てはまらない行は step にしない（保留にもしない）。
    依頼が無いときの暗黙の依頼（シーンの運ぶ物すべて）に使う。ルールに関係ない物を「保留」で並べないため。"""
    placements = placements or {}
    route_blocks = route_blocks or {}
    regions = {r.id: r for r in scene.regions}
    objects = {o.id: o for o in scene.objects}
    obligations = [n for n in norms if n.destination is not None]
    permissions = [n for n in norms if n.norm == "permission"]
    # 物体についてのルールを、内容が決めている時点で調べる（スキルでは絞らない）
    object_rules = [n for n in norms if n.norm != "permission" and n.target.kind == "object"]
    grasp_rules = [n for n in object_rules if "grasp" in _checked(n)]
    place_rules = [n for n in object_rules if "place" in _checked(n) and n.destination is None]
    receptacles = {o.id for o in scene.objects if o.role == "receptacle"}

    # すべての物がいまの場所にある状態から始める（置き位置と、「満杯か」の判定に使う）
    occupied: dict[str, list[planner.Disc]] = {}
    home: dict[str, planner.Disc] = {}
    for o in scene.objects:
        if o.region_id is not None:
            home[o.id] = planner._disc(o, o.position)
            occupied.setdefault(o.region_id, []).append(home[o.id])
    tentative = {k: list(v) for k, v in occupied.items()}  # 前の行までに置く物を足していく（満杯かの判定用）

    # 1・2. 行ごとに、収納先と接触を調べる
    drafts: list[_Draft] = []
    for row in task.rows:
        obj = objects.get(row.object_id)
        if obj is None:
            continue  # いま見えていない。行は消さない
        manual = placements.get(obj.id)
        draft = _Draft(row=row, obj=obj, locked=manual is not None)

        def full(region_id: str, obj: SceneObject = obj) -> Tri:
            """その領域に、この物を置く空きが無いか。領域がシーンに無ければ不明。

            領域の持ち主（箱など）に属性 full があれば、それを使う（VLM の答えか、住人の訂正）。
            無ければ置き位置の空きで決める。入れ物（ごみ箱など。物が重なってよい）は、空きでは満杯にならない。"""
            region = regions.get(region_id)
            if region is None:
                return None
            owner = objects.get(region.object_id or "")
            stated = owner.value("full") if owner is not None else None
            if isinstance(stated, bool):
                return stated
            if region.object_id in receptacles:
                return False
            return not planner._choose_position(obj, region, tentative.get(region_id, []))[1]

        _decide_destination(draft, obligations, manual, full, now, task.requester)
        row.region_full = dict(draft.region_full)
        if manual is None and row.requested_destination is not None:
            _apply_requested(draft, row.requested_destination, task, now)
        if only_ruled and draft.no_rule:
            continue
        row.destination, row.destination_rule_ids = draft.destination, [r.id for r in draft.rules]
        row.overridden_rule_ids = [r.id for r in draft.overridden]

        if draft.destination is not None and obj.region_id == draft.destination:
            # もう収納先にある（観測）
            for rule in draft.rules:
                row.record(evaluate(rule, placement_trace(obj, obj.region_id, now, draft.region_full), obj, basis="observed",
                                    requester=task.requester, now=now))
            if row.exec_state != "in_progress":
                row.set_state("done")
            continue

        for rule in grasp_rules:
            v = evaluate(rule, contact_trace(obj, now if rule.scope.uses_clock else None), obj, basis="predicted",
                         requester=task.requester, exceptions=permissions, now=now)
            row.record(v)
            draft.verdicts.append(v)
            if v.value == "violated" and draft.blocked is None:
                draft.blocked = f"Left in place without touching it, because it violates \"{rule.original_text}\" ({rule.id})"
            elif v.value == "undetermined":
                draft.missing.extend(v.missing)
                draft.unknown = draft.unknown or f"Not enough information to evaluate \"{rule.original_text}\" ({rule.id})"
        if draft.destination is not None and draft.blocked is None:
            # 「…には置くな」: 計画した置き先で判定する
            for rule in place_rules:
                v = evaluate(rule, placement_trace(obj, draft.destination, now if rule.scope.uses_clock else None,
                                                   draft.region_full), obj, basis="predicted",
                             requester=task.requester, exceptions=permissions, now=now)
                row.record(v)
                draft.verdicts.append(v)
                if v.value == "violated" and draft.blocked is None:
                    draft.blocked = (f"Left in place, because putting it in {draft.destination} violates "
                                     f"\"{rule.original_text}\" ({rule.id})")
                elif v.value == "undetermined":
                    draft.missing.extend(v.missing)
                    draft.unknown = draft.unknown or f"Not enough information to evaluate \"{rule.original_text}\" ({rule.id})"
        block = route_blocks.get(obj.id)
        if block is not None:
            # 経路が禁止に反する（動作計画・実行中の再計画の結果）。つかめても、運ぶ道が無いので保留
            for v in block.verdicts:
                row.record(v)
                draft.verdicts.append(v)
            row.route = block.searched
            if any(v.value == "violated" for v in block.verdicts) or not block.missing:
                draft.blocked = draft.blocked or block.reason
            else:
                draft.unknown = draft.unknown or block.reason
                draft.missing.extend(block.missing)
        drafts.append(draft)
        if draft.will_move and draft.destination in regions:
            # この物が置かれる分を数えておく（次の行の「満杯か」に効く）
            spot, free = planner._choose_position(obj, regions[draft.destination], tentative.get(draft.destination, []))
            if free:
                tentative.setdefault(draft.destination, []).append(planner._disc(obj, spot))

    # 置き位置は作業の順序どおりに決める。最初は、すべての物がいまの場所にある（occupied）

    # 3. 置き位置を決めて step にする
    steps: list[Step] = []
    for d in drafts:
        index = len(steps)
        common = {
            "id": f"s{index + 1}", "index": index, "object_id": d.obj.id,
            "from": Placement(region_id=d.obj.region_id, pose=d.obj.pose),
            "locked": d.locked, "rule_id": d.rules[0].id if d.rules else None,
            "verdicts": [v.timeless() for v in d.verdicts],
        }
        region = regions.get(d.destination) if d.destination is not None else None
        reason = d.blocked or d.unknown or d.problem

        if reason is None and d.destination is not None and region is None:
            reason = f"Storage zone {d.destination!r} is not in the scene"
            steps.append(Step(**common, status="unmatched", message=reason))
        elif reason is None and region is not None:
            # この物は、つかんだ時点で元の場所からいなくなる
            own = home.get(d.obj.id)
            origin = occupied.get(d.obj.region_id or "", [])
            if own is not None and own in origin:
                origin.remove(own)
            taken = occupied.setdefault(region.id, [])
            position, free = planner._choose_position(d.obj, region, taken)
            owner_is_receptacle = any(o.id == region.object_id and o.role == "receptacle" for o in scene.objects)
            if not free and not owner_is_receptacle:
                # 置ける空きが無い: 動かさない（元の場所に残る）
                if own is not None:
                    origin.append(own)
                reason = f"No free space to place it in {region.label or region.id}"
                steps.append(Step(**common, status="infeasible", message=reason,
                                  to=Placement(region_id=region.id, pose=Pose(position=position, rotation=d.obj.rotation))))
                if d.row.exec_state in REPLANNABLE:
                    d.row.set_state("deferred", reason)
                continue
            taken.append(planner._disc(d.obj, position))
            verdicts = list(d.verdicts)
            for rule in d.rules:  # 計画した置き先は、収納先の義務に適合する（予測）
                v = evaluate(rule, placement_trace(d.obj, region.id, now if rule.scope.uses_clock else None, d.region_full),
                             d.obj, basis="predicted", requester=task.requester, now=now)
                d.row.record(v)
                verdicts.append(v)
            steps.append(Step(
                **{**common, "verdicts": [v.timeless() for v in verdicts]},
                to=Placement(region_id=region.id, pose=Pose(position=position, rotation=d.obj.rotation)),
                status="ok", message=_override_note(d),
            ))
            if d.row.exec_state in REPLANNABLE:
                d.row.set_state("pending")
            continue
        else:
            to = None
            if region is not None:  # 収納先は分かっている。場所は取らずに、置くならここ、を入れておく
                position, _ = planner._choose_position(d.obj, region, occupied.get(region.id, []))
                to = Placement(region_id=region.id, pose=Pose(position=position, rotation=d.obj.rotation))
            steps.append(Step(**common, to=to, status="ambiguous" if d.ambiguous and not (d.blocked or d.unknown) else "deferred",
                              candidate_rule_ids=[r.id for r in d.candidates], message=reason))
        if d.row.exec_state in REPLANNABLE:
            d.row.set_state("deferred", reason or "", _unique(d.missing))
    return steps


class _Draft:
    """行 1 つについて調べた結果。"""

    def __init__(self, row: TaskRow, obj: SceneObject, locked: bool) -> None:
        self.row, self.obj, self.locked = row, obj, locked
        self.destination: str | None = None
        self.rules: list[NormRule] = []       # 収納先を決めた義務
        self.candidates: list[NormRule] = []  # 収納先が複数あるときの候補
        self.ambiguous = False
        self.problem: str | None = None       # 収納先が決まらない理由
        self.no_rule = False                  # 収納先を決める取り決めが、どれも当てはまらない
        self.overridden: list[NormRule] = []  # 依頼の間だけのルールが先に立ち、使わなかった常設のルール
        self.blocked: str | None = None       # 禁止に反する
        self.unknown: str | None = None       # 判定する情報が足りない
        self.missing: list[MissingFact] = []
        self.verdicts: list[Verdict] = []
        self.region_full: dict[str, bool] = {}  # 収納先を決めるときに調べた、領域 -> 空きが無いか

    @property
    def will_move(self) -> bool:
        return self.destination is not None and not (self.blocked or self.unknown or self.problem)


def _checked(rule: NormRule) -> frozenset[str]:
    """そのルールの内容を、どの時点の予測で調べるか（vocabulary.py）。"""
    entry = CONTENTS.get(rule.requirement.predicate)
    return entry.checked if entry is not None else frozenset()


def _decide_destination(d: _Draft, obligations: list[NormRule], manual: str | None, full=None,  # type: ignore[no-untyped-def]
                        now: datetime | None = None, requester: str | None = None) -> None:
    """収納先を決める義務のうち、条件（Scope）と対象の両方に合うものを選ぶ。

    full(region_id) は「その領域に、この物を置く空きが無いか」（条件 region_full が読む）。"""
    if manual is not None:  # 手の指定はルールより先（ルールに合うかは確かめない）
        d.destination = manual
        return

    def judge(rule: NormRule) -> tuple[Tri, list[MissingFact]]:
        if rule.scope.when is not None and full is not None:
            for leaf in rule.scope.when.leaves():
                region = leaf.args.get("region")
                if leaf.predicate == "region_full" and isinstance(region, str) and region not in d.region_full:
                    value = full(region)
                    if value is not None:
                        d.region_full[region] = value
        sample = WorldSample(t=now, phase="place_complete", holding=set(), region_full=dict(d.region_full))
        return applies(rule, sample, d.obj, requester=requester)

    standing = [r for r in obligations if r.origin != "task"]
    for_task = [r for r in obligations if r.origin == "task"]
    judged = [(r, *judge(r)) for r in standing]
    specific = [(r, value, missing) for r, value, missing in judged if not r.target.fallback]
    matched = [r for r, value, _ in specific if value is True]

    # 依頼の間だけのルールは、常設のルールより先に立つ
    task_matched = [r for r in for_task if judge(r)[0] is True]
    if task_matched:
        targets = {r.destination for r in task_matched}
        if len(targets) > 1:
            d.ambiguous, d.candidates = True, task_matched
            d.problem = "Multiple instructions in this request match with different storage locations"
            return
        destination = task_matched[0].destination
        if not matched:
            matched = [r for r, value, _ in judged if r.target.fallback and value is True]
        d.overridden = [r for r in matched if r.destination != destination]
        d.destination, d.rules = destination, task_matched
        return

    if not matched:
        unknown = [(r, missing) for r, value, missing in specific if value is None]
        if unknown:
            d.unknown = "Not enough information to tell whether a storage-deciding agreement applies"
            d.candidates = [r for r, _ in unknown]
            d.missing.extend(m for _, missing in unknown for m in missing)
            return
        matched = [r for r, value, _ in judged if r.target.fallback and value is True]  # 「それ以外」
    if not matched:
        d.problem = "No agreement decides the storage location"
        d.no_rule = True
        return
    targets = {r.destination for r in matched}
    if len(targets) > 1:
        d.ambiguous, d.candidates = True, matched
        d.problem = "Multiple agreements match with different storage locations"
        return
    d.destination, d.rules = matched[0].destination, matched


def _apply_requested(d: _Draft, requested: str, task: TaskRecord, now: datetime | None) -> None:
    """住人が指定した置き先を使う。収納先を決めるルールが別の場所を指していれば、その判定を残して保留にする。"""
    ruled, rules = d.destination, list(d.rules)
    d.destination = requested
    # ルールが決まらない（当てはまらない・複数ある）ことによる問題は、住人の指定で解ける
    d.problem, d.no_rule, d.ambiguous = None, False, False
    if ruled is None or ruled == requested:
        return
    for rule in rules:
        v = evaluate(rule, placement_trace(d.obj, requested, now if rule.scope.uses_clock else None, d.region_full), d.obj,
                     basis="predicted", requester=task.requester, now=now)
        d.row.record(v)
        d.verdicts.append(v)
    rule = rules[0] if rules else None
    # 接触の禁止など（このあと調べる）のほうが先に立つ理由なので、problem に入れる
    d.problem = (
        f"Left in place: \"{rule.original_text}\" ({rule.id}) says it belongs in {ruled}, not {requested}"
        if rule is not None else f"Left in place: the rules say it belongs in {ruled}, not {requested}")


def _override_note(d: _Draft) -> str | None:
    """依頼の間だけのルールが、常設のルールより先に立ったことの説明（人が読む）。"""
    if not d.overridden or not d.rules:
        return None
    by = d.rules[0]
    over = ", ".join(f"\"{r.original_text}\" ({r.id}, {r.destination})" for r in d.overridden)
    return f"For this request, \"{by.original_text}\" ({by.id}) takes priority over {over}"


def _unique(missing: list[MissingFact]) -> list[MissingFact]:
    seen: dict[tuple[str | None, str], MissingFact] = {}
    for m in missing:
        seen.setdefault((m.entity_id, m.key), m)
    return list(seen.values())
