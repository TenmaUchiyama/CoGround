"""サーバーが持つ全体状態（シーン、ルール、計画）。データの型は models.py。

状態が変わるたびに version を 1 増やし、全体を state.updated で全クライアントに送る。
差分は送らないので、取りこぼしても次の state.updated（または state.get）で最新に戻れる。

シーン、ルール、手で指定した行き先（placements）のどれかが変わるたびに、同じ version の中で Plan を作り直す（norms/planner.py）。
ルールは片付けルール（rules.set）も家庭ルール（norms.set）も 1 つの並び（_norms）に持つ。依頼が無いときは、運ぶ物すべてを暗黙の依頼にする。
- 収納先を決めるルールも placements も無ければ plan は None
- placements（物体 ID -> 領域 ID）は plan.place で入れる。ルールより先に使い、ルールに合うかは確かめない。
  物体がその領域に入ったら（運び終わったら）、その指定は消す。
  ただし、消すとルールがその物をよそへ運び直す場合は残す（plan.unplace で消せる）
- step の中身が前と同じなら、Plan はそのまま残す（Unity が同じシーンを送り直しても id / version が変わらない）
- 中身が変わったら、新しい id（plan_1, plan_2, ...）の Plan にする

座標はすべて Unity のワールド座標（メートル、左手系、Y 上）。物体 ID は Unity が決め、
MoveIt の collision object 名と揃える。
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Callable

from .models import (
    Attribute, AttributeValue, MissingFact, Person, Plan, Quat, Rule, SceneObject, SceneRegion, SceneSnapshot, Vec3, Verdict,
)
from .norms import vocabulary
from .norms.attributes import attribute_defs
from .norms.report import judgments
from .norms.depends import affected_by, attribute_key
from .norms.clock import HomeClock
from .norms.evaluate import evaluate, placement_trace
from .norms.geometry import Point, region_polygon, unity_xy
from .norms.predicates import PersonAt, WorldSample
from .norms.task import ExecState
from .norms.model import NormRule, PendingRule, Scope
from .norms.planner import plan_task
from .norms.task import AttributeCorrection, CorrectionKind, RouteBlock, RowChange, TaskRecord, TaskRow
from .vlm import AttributeProvider, annotate_scene, make_attribute_provider

PEOPLE_TIMEOUT = 2.0  # 人の位置がこの秒数届かなければ「観測できていない」とみなす。COGROUND_PEOPLE_TIMEOUT で変える（0 で無効）

__all__ = ["Plan", "Quat", "Rule", "SceneObject", "SceneRegion", "SceneSnapshot", "StateStore", "Vec3"]


class StateStore:
    def __init__(self) -> None:
        self._version = 0
        self._scene_version = 0  # シーンが届く（または書き換える）たびに増える。配置のあとに観測があったかを見る
        self._updated_at: str | None = None
        self._scene = SceneSnapshot()
        self._raw_scene = self._scene  # 届いたままのシーン。_scene は、これに住人の訂正を重ねたもの
        # 住人が訂正した属性: 物体 ID -> キー -> 値。scene.update はシーン全体を置き換えるので、別に持って毎回重ねる
        self._corrections: dict[str, dict[str, Attribute]] = {}
        # 訂正のうち、ファイルに残すもの（画像から判断できない属性。持ち主など）。物体 ID -> {属性のキー: 登録したときの物体の種類}
        self._durable: dict[str, dict[str, str]] = {}
        # ファイルから戻した訂正。物体の種類が登録したときと違えば重ねない（再起動で ID が別の物体に付いたときの歯止め）
        self._from_file: set[tuple[str, str]] = set()
        self._correction_count = 0
        self._placements: dict[str, str] = {}  # 手で指定した行き先: 物体 ID -> 領域 ID（指定した順）
        self._plan: Plan | None = None  # まだ計画が無ければ None
        self._plan_count = 0
        # 依頼の記録。Plan とは別に持ち、シーンが変わっても対象を選び直さない（norms/task.py）
        self._tasks: list[TaskRecord] = []
        self._norms: list[NormRule] = []  # ルールはすべてここ。片付けルール（rules.set）も収納先の義務に直して持つ（origin = tidy）
        self.clock = HomeClock()  # 家の時計（差し替えられる）
        # 住人が決めた領域（進入禁止の範囲など）: 領域 ID -> 領域。scene.update では消えない（zones.define / zones.update）
        self._zones: dict[str, SceneRegion] = {}
        # 人の位置（people.update）。None は、まだ一度も届いていない
        self._people: list[Person] | None = None
        self._people_seen: float | None = None  # 届いた時刻（time.monotonic）
        self._people_valid_for: float | None = None
        self.people_timeout = float(os.environ.get("COGROUND_PEOPLE_TIMEOUT") or PEOPLE_TIMEOUT)
        # 経路が家庭ルールに反するので運べない物: 物体 ID -> 理由と探した条件（動作計画・実行中の再計画が入れる）
        self._route_blocks: dict[str, RouteBlock] = {}
        self._pending: list[PendingRule] = []  # 登録の途中のルール（rules.confirm で確定する）
        # 検出した物体に属性を付ける VLM（vlm.py。COGROUND_VLM。既定は何もしない）。テストでは差し替える
        self.attributes: AttributeProvider = make_attribute_provider()
        # ルールをファイルに残す（rulebank.py）。None なら残さない。Services が COGROUND_RULE_BANK を見て付ける
        self.rule_bank: Any = None

    @property
    def version(self) -> int:
        return self._version

    @property
    def scene(self) -> SceneSnapshot:
        return self._scene

    @property
    def rules(self) -> list[Rule]:
        """片付けルール（rules.set で入れた分）を、属性 = 値 → 行き先 の形で。中身は家庭ルール（norms）の一部。
        訂正して片付けルールの形で書けなくなったものは入らない（norms には残る）。"""
        out = []
        for n in self._norms:
            legacy = n.to_legacy() if n.origin == "tidy" else None
            if legacy is not None:
                out.append(legacy)
        return out

    @property
    def placements(self) -> dict[str, str]:
        return self._placements

    @property
    def plan(self) -> Plan | None:
        return self._plan

    @property
    def task(self) -> TaskRecord | None:
        """いまの依頼（いちばん新しいもの）。まだ無ければ None"""
        return self._tasks[-1] if self._tasks else None

    @property
    def tasks(self) -> list[TaskRecord]:
        return self._tasks

    def open_task(self, text: str, object_ids: list[str], *, requester: str | None = None,
                  source_region: str | None = None, created_at: datetime | None = None,
                  rules: list[NormRule] | None = None) -> TaskRecord:
        """依頼を記録する。対象（object_ids）はここで決まり、あとで増減しない。

        rules は、この依頼の間だけ効くルール（例: 全部 box_1 に入れて）。ID は付け直す（T1, T2, ...）。"""
        by_id = {o.id: o for o in self._scene.objects}
        unknown = [i for i in object_ids if i not in by_id]
        if unknown:
            raise ValueError(f"Objects not in the scene: {unknown}")
        if len(set(object_ids)) != len(object_ids):
            raise ValueError("Duplicate target object IDs")
        region_ids = {r.id for r in self._scene.regions}
        task_rules: list[NormRule] = []
        taken = {n.id for n in self._norms} | {p.rule.id for p in self._pending}
        for rule in rules or []:
            region = rule.destination
            if region is not None and region not in region_ids:
                raise ValueError(f"Zone {region!r} is not in the scene")
            rule_id = self.new_norm_id("T", taken)
            taken.add(rule_id)
            task_rules.append(rule.model_copy(update={"id": rule_id, "origin": "task"}))
        if self.active_task is not None:
            self.active_task.closed_at = created_at or self.clock.now()  # 前の依頼は閉じる（記録は残る）
        self._route_blocks.clear()  # 経路による保留は、前の依頼のもの
        task = TaskRecord(
            id=f"task_{len(self._tasks) + 1}", text=text, requester=requester, source_region=source_region,
            created_at=created_at or self.clock.now(),
            rows=[TaskRow(object_id=i, label=by_id[i].category) for i in object_ids],
            rules=task_rules,
        )
        self._tasks.append(task)
        self._bump(replan=True)
        return task

    @property
    def active_task(self) -> TaskRecord | None:
        """Plan に使う依頼（いちばん新しく、閉じていないもの）。"""
        task = self.task
        return task if task is not None and task.closed_at is None else None

    def close_task(self) -> int:
        """いまの依頼を閉じる（記録は残る）。Plan は、依頼なしの作り方（旧 Rule と手の指定）に戻る。"""
        if self.active_task is not None:
            self.active_task.closed_at = self.clock.now()
        return self._bump(replan=True)

    # ------------------------------------------------------------------ シーケンスの編集（住人が作業の順序を変える）

    def _editable_task(self) -> TaskRecord:
        task = self.active_task
        if task is None:
            raise ValueError("No open request (ask for a task first)")
        return task

    def _step_objects(self) -> list[str]:
        return [s.object_id for s in self._plan.steps] if self._plan else []

    def sequence_add(self, object_id: str, target_region: str | None = None, index: int | None = None) -> int:
        """物体を運ぶ step を足す。index は Plan の step の並びでの挿入位置（省略すると最後）。

        target_region を渡すと、そこを置き先にする（収納先を決めるルールと照合する）。省略するとルールが決める。
        戻り値は、最初に影響を受ける step の位置（ここから後ろを検証し直す）。
        """
        task = self._editable_task()
        obj = next((o for o in self._scene.objects if o.id == object_id), None)
        if obj is None:
            raise ValueError(f"Object {object_id!r} is not in the scene")
        if task.row(object_id) is not None and object_id in self._step_objects():
            raise ValueError(f"{object_id} is already in the sequence")
        if target_region is not None:
            if target_region not in {r.id for r in self._scene.regions}:
                raise ValueError(f"Zone {target_region!r} is not in the scene")
            if target_region == object_id:
                raise ValueError("An object can't be placed in its own zone")
        steps = self._step_objects()
        at = len(steps) if index is None else max(0, min(index, len(steps)))
        task.rows = [r for r in task.rows if r.object_id != object_id]  # 見えなくなっていた行などは作り直す
        row = TaskRow(object_id=object_id, label=obj.category, requested_destination=target_region, added=True)
        if at >= len(steps):
            task.rows.append(row)
        else:
            before = next(i for i, r in enumerate(task.rows) if r.object_id == steps[at])
            task.rows.insert(before, row)
        if object_id in task.removed:
            task.removed.remove(object_id)
        task.sequence_version += 1
        self._bump(replan=True)
        return at

    def sequence_remove(self, object_id: str) -> int:
        """step を外す（その物体は動かさない）。戻り値は、外した step の位置。"""
        task = self._editable_task()
        if task.row(object_id) is None:
            raise ValueError(f"{object_id} is not in the sequence")
        steps = self._step_objects()
        at = steps.index(object_id) if object_id in steps else len(steps)
        task.rows = [r for r in task.rows if r.object_id != object_id]
        task.removed.append(object_id)
        self._placements.pop(object_id, None)
        self._route_blocks.pop(object_id, None)
        task.sequence_version += 1
        self._bump(replan=True)
        return at

    def sequence_reorder(self, object_ids: list[str]) -> int:
        """step の順序を変える。object_ids は、いまの Plan の step の物体を並べ替えたもの。

        戻り値は、最初に順序が変わった step の位置。step にならない行（もう収納先にある物など）の位置は変えない。
        """
        task = self._editable_task()
        steps = self._step_objects()
        if sorted(object_ids) != sorted(steps) or len(set(object_ids)) != len(object_ids):
            raise ValueError(f"The order must list each step's object exactly once: {steps}")
        first = next((i for i, (a, b) in enumerate(zip(steps, object_ids)) if a != b), None)
        if first is None:
            return len(steps)
        by_id = {r.object_id: r for r in task.rows}
        order = iter(object_ids)
        task.rows = [by_id[next(order)] if r.object_id in steps else r for r in task.rows]
        task.sequence_version += 1
        self._bump(replan=True)
        return first

    @property
    def norms(self) -> list[NormRule]:
        return self._norms

    def set_norms(self, norms: list[NormRule]) -> int:
        """片付けルール（origin = tidy）以外を置き換える。"""
        self._norms = [*(n for n in self._norms if n.origin == "tidy"), *(n.model_copy(update={"origin": "norm"}) for n in norms)]
        self._drop_route_blocks()
        return self._bump(replan=True)

    # ------------------------------------------------------------------ 領域（進入禁止の範囲など）

    @property
    def zones(self) -> dict[str, SceneRegion]:
        return self._zones

    def define_zone(self, zone: SceneRegion) -> int:
        """住人が決めた領域を登録する（同じ ID があれば置き換える）。scene.update のあとも残る。"""
        self._zones[zone.id] = zone
        self._drop_route_blocks()
        return self._bump(replan=True)

    def remove_zone(self, zone_id: str) -> int:
        self._zones.pop(zone_id, None)
        self._drop_route_blocks()
        return self._bump(replan=True)

    def zone_polygons(self) -> dict[str, list[Point]]:
        """領域 ID -> 床の多角形（ROS の x, y）。シーンの領域と、住人が決めた領域（同じ ID なら、こちらを使う）。"""
        out = {r.id: region_polygon(r) for r in self._scene.regions}
        out.update({z.id: region_polygon(z) for z in self._zones.values()})
        return out

    def keepout_payload(self, zone_ids: list[str]) -> list[dict[str, Any]]:
        """ロボットに渡す進入禁止の範囲（ROS の x, y）。形が分からない領域は入れない。"""
        polygons = self.zone_polygons()
        return [{"id": z, "polygon": [[round(x, 4), round(y, 4)] for x, y in polygons[z]]} for z in zone_ids if z in polygons]

    # ------------------------------------------------------------------ 人

    def set_people(self, people: list[Person], valid_for: float | None = None) -> bool:
        """人の位置を置き換える（空のリストは「見えている範囲に誰もいない」）。valid_for 秒たつと、観測できていない扱いになる。

        戻り値は、見せる中身が変わったか（だれがいるか、5 cm 以上動いたか、観測できていなかったのが届いたか）。
        変わっていなければ version は上げない（1 秒に何度も届くので、そのたびに全体状態を配らないため）。
        """
        def key(items: list[Person] | None) -> list[tuple[str, str, int, int]] | None:
            return None if items is None else [(p.id, p.kind, round(p.position[0] * 20), round(p.position[2] * 20)) for p in items]

        changed = not self.people_observed or key(self._people) != key(people)
        self._people, self._people_seen, self._people_valid_for = list(people), time.monotonic(), valid_for
        if changed:
            self._scene = self._compose(self._raw_scene)
            self._bump()
        return changed

    @property
    def people_observed(self) -> bool:
        if self._people is None or self._people_seen is None:
            return False
        limit = self._people_valid_for if self._people_valid_for is not None else self.people_timeout
        return limit <= 0 or time.monotonic() - self._people_seen <= limit

    def people_samples(self) -> list[PersonAt] | None:
        """判定に使う人の位置（ROS の x, y）。観測できていなければ None"""
        if not self.people_observed:
            return None
        return [PersonAt(id=p.id, kind=p.kind, xy=unity_xy(p.position)) for p in self._people or []]

    # ------------------------------------------------------------------ 経路の判定（動作計画・実行中の監視が呼ぶ）

    @property
    def route_blocks(self) -> dict[str, RouteBlock]:
        return self._route_blocks

    def set_route_block(self, object_id: str, block: RouteBlock) -> int:
        """その物体を運ぶ経路が家庭ルールに反する（または判定できない）。依頼の行は保留になる。"""
        self._route_blocks[object_id] = block
        return self._bump(replan=True)

    def clear_route_blocks(self, object_ids: list[str] | None = None) -> int:
        """経路による保留を解く（object_ids が None なら全部）。動作計画をやり直す前に呼ぶ。"""
        self._drop_route_blocks(object_ids)
        return self._bump(replan=True)

    def _drop_route_blocks(self, object_ids: list[str] | None = None) -> None:
        dropped = [o for o in self._route_blocks if object_ids is None or o in object_ids]
        task = self.active_task
        for object_id in dropped:
            block = self._route_blocks.pop(object_id)
            row = task.row(object_id) if task is not None else None
            if row is None:
                continue
            for v in block.verdicts:  # 前の経路の判定は、もう当てにならない
                row.record(Verdict(rule_id=v.rule_id, value="undetermined", basis="predicted", entity_id=v.entity_id,
                                   missing=[MissingFact(key="base_pose")], detail="Undetermined until the path is replanned",
                                   evaluated_at=self.clock.now()))

    def record_route(self, object_id: str, verdicts: list[Verdict], searched: dict[str, Any] | None = None) -> None:
        """経路の判定（予測）と探した条件を、依頼の行に記録する。"""
        row = self.active_task.row(object_id) if self.active_task is not None else None
        if row is None:
            return
        for v in verdicts:
            row.record(v)
        if searched is not None:
            row.route = searched

    def record_observed(self, object_id: str | None, verdicts: list[Verdict]) -> None:
        """実行中に観測した状態に対する判定を、依頼の行に記録する。"""
        row = self.active_task.row(object_id) if self.active_task is not None and object_id is not None else None
        if row is not None:
            for v in verdicts:
                row.record(v)

    def recheck(self) -> int:
        """つかむ直前に、いまの時刻・属性で判定をやり直す（訂正や、時刻で変わるルールに対応する）。"""
        return self._bump(replan=True)

    def all_norms(self) -> list[NormRule]:
        """判定に使うルール: 旧 Rule（収納先の義務に直す）と家庭ルール、いまの依頼の間だけのルール（origin = task）。"""
        task = self.active_task
        return [*self._norms, *(task.rules if task is not None else [])]

    def replan(self) -> int:
        """時計を変えたときなど、シーンもルールも変わっていないが判定をやり直したいときに呼ぶ。
        経路による保留も解く（通る時刻が変わると、経路の判定も変わるので、動作計画をやり直す）。"""
        self._drop_route_blocks()
        return self._bump(replan=True)

    def snapshot(self) -> dict[str, Any]:
        return {
            "version": self._version,
            "updated_at": self._updated_at,
            "scene": self._scene.model_dump(mode="json"),
            "rules": [r.model_dump(mode="json") for r in self.rules],  # 片付けルールの形で見たもの（中身は norms にもある）
            "placements": [{"object_id": o, "target_region": t} for o, t in self._placements.items()],
            "plan": self._plan.model_dump(mode="json") if self._plan else None,
            "norms": [n.model_dump(mode="json") for n in self._norms],
            # いまのルールが使っている属性（VLM への質問のもと。visual = false は住人が登録する）
            "attributes": [a.model_dump(mode="json") for a in attribute_defs(self.all_norms())],
            # 運ぶ物ごとの、ルールの対象条件との照合（合わなかったものも含む。norms/report.py の judgments）
            "judgments": {o.id: judgments(o, self.all_norms()) for o in self._scene.objects if o.role == "item"},
            # ルールに書ける内容と条件（表示する側は、説明の言い方をここから読む）
            "vocabulary": vocabulary.export(),
            "task": self.task.model_dump(mode="json") if self.task else None,
            "clock": self.clock.snapshot(),
            "corrections": [{"object_id": o, "key": k, "value": a.value}
                            for o, attrs in self._corrections.items() for k, a in attrs.items()],
            "zones": [z.model_dump(mode="json") for z in self._zones.values()],
            "people": {"observed": self.people_observed,
                       "people": [p.model_dump(mode="json") for p in self._people or []]},
            "route_blocks": {o: b.model_dump(mode="json") for o, b in self._route_blocks.items()},
            "pending_rules": [p.model_dump(mode="json") for p in self._pending],
        }

    @property
    def scene_version(self) -> int:
        return self._scene_version

    def region_of(self, object_id: str) -> str | None:
        return next((o.region_id for o in self._scene.objects if o.id == object_id), None)

    def mark_row(self, object_id: str, exec_state: ExecState, reason: str = "") -> None:
        """依頼の行の実行の状態を変える（実行側が呼ぶ）。依頼が無い・対象でない物体なら何もしない。"""
        row = self.active_task.row(object_id) if self.active_task is not None else None
        if row is not None:
            row.set_state(exec_state, reason)

    def record_placement(self, object_id: str, outcome: ExecState, reason: str = "") -> None:
        """配置のあとの観測の結果を、依頼の行に記録する（実行側が呼ぶ）。

        outcome: done（収納先で観測） / misplaced（別の場所で観測） / unverified（観測が来なかった）。
        収納先を決めた義務を、観測した場所（unverified なら場所不明）で判定して残す。
        """
        task = self.active_task
        row = task.row(object_id) if task is not None else None
        obj = next((o for o in self._scene.objects if o.id == object_id), None)
        if task is None or row is None or obj is None:
            return
        now = self.clock.now()
        trace = ([WorldSample(t=now, phase="place_complete")] if outcome == "unverified"
                 else placement_trace(obj, obj.region_id, now, row.region_full))
        for rule in self.all_norms():
            if rule.id in row.destination_rule_ids:
                row.record(evaluate(rule, trace, obj, basis="observed", requester=task.requester, now=now))
        row.set_state(outcome, reason)

    def set_scene(self, scene: SceneSnapshot) -> int:
        self._scene_version += 1
        # VLM の属性は届いたシーンの一部として持つ（訂正のたびに付け直さない）。訂正はこのあと重ねるので VLM より優先
        scene = annotate_scene(scene, self.attributes)
        self._raw_scene = scene
        if scene.people is not None:  # シーンと一緒に人の位置も届いた
            self._people, self._people_seen, self._people_valid_for = list(scene.people), time.monotonic(), None
        self._scene = self._compose(scene)
        return self._bump(replan=True)

    def _compose(self, scene: SceneSnapshot) -> SceneSnapshot:
        """届いたシーンに、住人の訂正と、いまの人の位置を重ねる。"""
        return self._with_corrections(scene).model_copy(update={"people": list(self._people or [])})

    @property
    def corrections(self) -> dict[str, dict[str, Attribute]]:
        return self._corrections

    def _with_corrections(self, scene: SceneSnapshot) -> SceneSnapshot:
        if not self._corrections:
            return scene
        def kept(o: Any) -> dict[str, Attribute]:
            return {k: a for k, a in self._corrections[o.id].items()
                    if (o.id, k) not in self._from_file or self._durable.get(o.id, {}).get(k) == o.category}

        return scene.model_copy(update={"objects": [
            o.model_copy(update={"attributes": {**o.attributes, **kept(o)}})
            if o.id in self._corrections else o
            for o in scene.objects
        ]})

    def _mark_durable(self, object_id: str, key: str, category: str | None) -> None:
        """訂正をファイルに残すかどうかを決める。残すのは、画像から判断できない属性（visual = false）の訂正だけ。

        画像から判断できる属性（割れ物、汚れなど）はその場の状態で、次に見たときに VLM が答え直すので残さない。
        category = None は訂正の取り消し。
        """
        self._from_file.discard((object_id, key))
        definition = next((a for a in attribute_defs(self.all_norms()) if a.name == key), None)
        if category is not None and definition is not None and not definition.visual:
            self._durable.setdefault(object_id, {})[key] = category
            return
        self._durable.get(object_id, {}).pop(key, None)
        if not self._durable.get(object_id):
            self._durable.pop(object_id, None)

    def durable_corrections(self) -> list[dict[str, Any]]:
        """ファイルに残す訂正（rulebank.py）。"""
        return [{"object_id": o, "key": k, "value": self._corrections[o][k].value, "category": category}
                for o, keys in sorted(self._durable.items()) for k, category in sorted(keys.items())
                if k in self._corrections.get(o, {})]

    def set_attribute(self, object_id: str, key: str, value: AttributeValue | None) -> AttributeCorrection:
        """住人が属性を訂正する（value = None なら訂正を取り消し、届いた値に戻す）。

        訂正はシーンとは別に持ち、次の scene.update のあとも効く。依頼があれば判定をやり直し、
        訂正の前後で変わった行と項目を返す（依頼の corrections にも残す）。
        変わるのは、その属性を読むルールの判定と、それで決まる収納先・実行の状態だけ。
        """
        raw = next((o for o in self._raw_scene.objects if o.id == object_id), None)
        if raw is None:
            raise ValueError(f"Object {object_id!r} is not in the scene")
        if key in ("category", "group", "role"):
            raise ValueError(f"{key} is not an attribute, so it can't be corrected")
        current = next(o for o in self._scene.objects if o.id == object_id).value(key)
        task = self.active_task
        before = task.digest() if task is not None else {}

        if value is None:
            self._corrections.get(object_id, {}).pop(key, None)
            if not self._corrections.get(object_id):
                self._corrections.pop(object_id, None)
        else:
            self._corrections.setdefault(object_id, {})[key] = Attribute(value=value, source="user", confidence=1.0)
        self._mark_durable(object_id, key, raw.category if value is not None else None)
        self._scene = self._compose(self._raw_scene)
        self._bump(replan=True)
        return self._correction("attribute", object_id, key, current, value,
                                [r.id for r in affected_by(attribute_key(key), self.all_norms())], before, object_id=object_id)

    def _correction(self, kind: CorrectionKind, entity_id: str, key: str, before_value: Any, after_value: Any,
                    affected: list[str], before: dict[str, dict[str, Any]], object_id: str | None = None) -> AttributeCorrection:
        """訂正の記録を作る。before は訂正の前の task.digest()。いまの digest と比べて、変わった行と項目を入れる。"""
        task = self.active_task
        self._correction_count += 1
        after = task.digest() if task is not None else {}
        correction = AttributeCorrection(
            id=f"correction_{self._correction_count}", t=self.clock.now(), kind=kind, object_id=object_id,
            entity_id=entity_id, key=key, before=before_value, after=after_value, affected_rule_ids=affected,
            changes=[
                RowChange(object_id=oid, what=what, before=before.get(oid, {}).get(what), after=row.get(what))
                for oid, row in after.items()
                for what in sorted({*row, *before.get(oid, {})})
                if before.get(oid, {}).get(what) != row.get(what)
            ],
        )
        if task is not None:
            task.corrections.append(correction)
        return correction

    def _digest(self) -> dict[str, dict[str, Any]]:
        return self.active_task.digest() if self.active_task is not None else {}

    # ------------------------------------------------------------------ ルール・領域の訂正と、登録の途中のルール

    def update_norm(self, rule_id: str, change: Callable[[NormRule], NormRule]) -> AttributeCorrection:
        """家庭ルールの Scope を訂正する（「19 時からにして」）。判定をやり直し、訂正の前後で変わった行と項目を返す。"""
        index = next((i for i, n in enumerate(self._norms) if n.id == rule_id), None)
        if index is None:
            raise ValueError(f"No household rule {rule_id!r}")
        old = self._norms[index]
        new = change(old)
        before = self._digest()
        self._norms[index] = new
        self._drop_route_blocks()
        self._bump(replan=True)
        affected = [rule_id, *(n.id for n in self._norms if n.exception_of == rule_id)]
        return self._correction("rule", rule_id, "scope", old.scope.model_dump(mode="json", by_alias=True),
                                new.scope.model_dump(mode="json", by_alias=True), affected, before)

    def update_zone(self, zone: SceneRegion) -> AttributeCorrection:
        """領域の範囲を訂正する。その領域を読むルールの判定をやり直す。"""
        old = self._zones.get(zone.id) or next((r for r in self._scene.regions if r.id == zone.id), None)
        if old is None:
            raise ValueError(f"No zone {zone.id!r} (use zones.define to define a new one)")
        before = self._digest()
        self._zones[zone.id] = zone
        self._drop_route_blocks()
        self._bump(replan=True)
        affected = [n.id for n in self.all_norms() if n.target.kind == "zone" and n.target.id == zone.id]
        return self._correction("zone", zone.id, "shape", old.model_dump(mode="json"), zone.model_dump(mode="json"),
                                affected, before)

    def add_exception(self, rule: NormRule) -> AttributeCorrection:
        """元の禁止に例外（許可）を足す。判定をやり直し、訂正の前後で変わった行と項目を返す。"""
        base = next((n for n in self.all_norms() if n.id == rule.exception_of), None)
        if base is None or base.norm != "prohibition":
            raise ValueError(f"No original prohibition {rule.exception_of!r}")
        if any(n.id == rule.id for n in self.all_norms()):
            raise ValueError(f"Rule ID {rule.id!r} is already in use")
        before = self._digest()
        self._norms.append(rule)
        self._drop_route_blocks()
        self._bump(replan=True)
        return self._correction("exception", base.id, "exception", None, rule.model_dump(mode="json", by_alias=True),
                                [base.id, rule.id], before)

    def new_norm_id(self, prefix: str = "N", taken: set[str] | None = None) -> str:
        used = {n.id for n in self.all_norms()} | {p.rule.id for p in self._pending} | (taken or set())
        n = 1
        while f"{prefix}{n}" in used:
            n += 1
        return f"{prefix}{n}"

    @property
    def pending_rules(self) -> list[PendingRule]:
        return self._pending

    def add_norms(self, norms: list[NormRule], pending: list[PendingRule] | None = None) -> int:
        """確定したルールを足し、登録の途中のルールを覚える（norms.compile）。"""
        self._norms.extend(norms)
        self._pending.extend(pending or [])
        self._drop_route_blocks()
        return self._bump(replan=True)

    def drop_pending(self, rule_id: str) -> int:
        self._pending = [p for p in self._pending if p.rule.id != rule_id]
        return self._bump()

    def confirm_pending(self, rule_id: str, refs: dict[str, str], *, until: str | None = None,
                        keep_open: bool = False) -> NormRule:
        """登録の途中のルールを確定する。

        refs: 仮の参照（zone_ref_1 など）-> 領域の ID（決めてある領域か、シーンの領域）
        until: 解除時刻（HH:MM）。言われていないままにするなら keep_open = True（その日のうちは効き続ける）
        足りないものがあれば ValueError（勝手に補わない）。
        """
        item = next((p for p in self._pending if p.rule.id == rule_id), None)
        if item is None:
            raise ValueError(f"No pending rule {rule_id!r}")
        rule = item.rule
        known = set(self.zone_polygons())
        missing = [r.ref for r in item.pending_refs if r.ref not in refs]
        if missing:
            raise ValueError(f"Unresolved references: {missing} (define the region with zones.define and pass it in refs)")
        unknown = sorted({z for z in refs.values() if z not in known})
        if unknown:
            raise ValueError(f"No such zones: {unknown}")
        if rule.target.id in refs:
            rule = rule.model_copy(update={"target": rule.target.model_copy(update={"id": refs[rule.target.id]})})
        args = {k: refs.get(v, v) if isinstance(v, str) else v for k, v in rule.requirement.args.items()}
        rule = rule.model_copy(update={"requirement": rule.requirement.model_copy(update={"args": args})})
        if "scope.until" in item.unresolved:
            if until is not None:
                scope = Scope.model_validate({**rule.scope.model_dump(by_alias=True), "until": until})
                rule = rule.model_copy(update={"scope": scope})
            elif not keep_open:
                raise ValueError("Expiry time (until) is undecided. Pass a time, or explicitly leave it open with keep_open = true")
        self._pending = [p for p in self._pending if p.rule.id != rule_id]
        self._norms.append(rule)
        self._drop_route_blocks()
        self._bump(replan=True)
        return rule

    def set_rules(self, rules: list[Rule]) -> int:
        """片付けルール（origin = tidy）だけを置き換える。家庭ルールとして持ち、ほかの家庭ルールより前に並べる。"""
        self._norms = [*(NormRule.from_legacy(r) for r in rules), *(n for n in self._norms if n.origin != "tidy")]
        self._drop_route_blocks()
        return self._bump(replan=True)

    def set_placement(self, object_id: str, target_region: str) -> int:
        """物体の行き先を手で指定する（同じ物体の前の指定は置き換える）。"""
        self._placements.pop(object_id, None)  # 指定し直したら順番も最後にする
        self._placements[object_id] = target_region
        return self._bump(replan=True)

    def clear_placements(self, object_id: str | None = None) -> int:
        """手で指定した行き先を消す（object_id が None なら全部）。"""
        if object_id is None:
            self._placements.clear()
        else:
            self._placements.pop(object_id, None)
        return self._bump(replan=True)

    def move_object(self, object_id: str, position: Vec3, rotation: Quat, region_id: str | None) -> int:
        """物体を動かす（Unity がいないとき、Executor が置いた結果を書き込むのに使う）。Plan を作り直す。"""
        self._scene_version += 1
        self._raw_scene = self._raw_scene.model_copy(update={"objects": [
            o.model_copy(update={"position": position, "rotation": rotation, "region_id": region_id})
            if o.id == object_id else o
            for o in self._raw_scene.objects
        ]})
        self._scene = self._compose(self._raw_scene)
        return self._bump(replan=True)

    def touch(self) -> int:
        """シーンやルール以外（実行の状態など）が変わったときに、version だけ上げる。"""
        return self._bump()

    def set_plan(self, plan: Plan | None) -> int:
        self._plan = plan
        return self._bump()

    def _bump(self, replan: bool = False) -> int:
        self._version += 1
        if replan:
            self._replan()
        self._updated_at = datetime.now(timezone.utc).isoformat()
        if self.rule_bank is not None:
            self.rule_bank.save_if_changed(self)  # ルールが変わっていれば書き出す（同じなら何もしない）
        return self._version

    def restore_rule_bank(self, norms: list[NormRule], zones: list[SceneRegion], pending: list[PendingRule],
                          attributes: list[dict[str, Any]] | None = None) -> int:
        """ファイルに残したルールバンクを入れる（起動時。rulebank.py）。いまのルール・領域・登録の途中のルールは置き換える。

        attributes は、住人が登録した属性のうち残したもの（durable_corrections の形）。
        """
        self._norms = list(norms)
        self._zones = {z.id: z for z in zones}
        self._pending = list(pending)
        for a in attributes or []:
            object_id, key = str(a["object_id"]), str(a["key"])
            self._corrections.setdefault(object_id, {})[key] = Attribute(value=a["value"], source="user", confidence=1.0)
            self._durable.setdefault(object_id, {})[key] = str(a["category"])
            self._from_file.add((object_id, key))
        self._scene = self._compose(self._raw_scene)
        self._drop_route_blocks()
        return self._bump(replan=True)

    def _replan(self) -> None:
        task = self.active_task
        if task is not None:
            # 依頼があるとき: 対象は依頼したときの行。行ごとに家庭ルールを判定して step か保留かを決める（norms/planner.py）。
            # 手で指定した行き先は、着いても消さない（行が done になり、step は出ない）
            steps = plan_task(self._scene, self.all_norms(), task, self._placements, now=self.clock.now(),
                              route_blocks=self._route_blocks)
            if self._plan is None or self._plan.steps != steps:
                self._plan_count += 1
                self._plan = Plan(id=f"plan_{self._plan_count}", base_scene_version=self._version, steps=steps)
            return
        # 行き先に入った物の指定は役目を終えたので消す（あとで物を戻しても、また運ばせない）。
        # ただし、消すとルールがその物をよそへ運び直すなら、残す（手の指定はルールより強い。実行すると往復してしまう）
        # 依頼が無いとき: シーンの運ぶ物すべてを暗黙の依頼にして、同じ判定（収納先・接触の禁止など）で計画する。
        # 収納先を決める取り決めがどれも当てはまらない物は step にしない。
        region_of = {o.id: o.region_id for o in self._scene.objects}
        has_destination = any(n.destination is not None for n in self._norms)
        arrived = {o for o, t in self._placements.items() if region_of.get(o) == t}
        if arrived and has_destination:
            rest = {o: t for o, t in self._placements.items() if o not in arrived}
            moved_by_rule = {s.object_id for s in self._implicit_steps(rest) if s.to is not None}
            arrived -= moved_by_rule
        self._placements = {o: t for o, t in self._placements.items() if o not in arrived}
        if not has_destination and not self._placements:
            self._plan = None  # 収納先を決める取り決めも手の指定も無い（禁止だけでは運ぶ物が決まらない）
            return
        steps = self._implicit_steps(self._placements)
        if self._plan is not None and self._plan.steps == steps:
            return
        self._plan_count += 1
        self._plan = Plan(id=f"plan_{self._plan_count}", base_scene_version=self._version, steps=steps)

    def _implicit_steps(self, placements: dict[str, str]) -> list:
        """依頼が無いときの暗黙の依頼（運ぶ物と、手で行き先を指定した物）で計画する。行の記録は残さない。"""
        rows = [TaskRow(object_id=o.id, label=o.category) for o in self._scene.objects
                if o.role == "item" or o.id in placements]
        task = TaskRecord(id="implicit", text="", rows=rows)
        return plan_task(self._scene, self.all_norms(), task, placements, now=self.clock.now(),
                         route_blocks=self._route_blocks, only_ruled=True)
