"""ルールを状態列に当てて判定する（設計ガイド §6）。計画（予測）と実行（観測）で同じ関数を使う。

    適用条件  A(t, b) = S(t, b) ∧ T(b)        有効な例外があれば、その分だけ狭める
              S は時刻・依頼者と、状態についての条件（Scope.when。「子供が 5 m 以内にいるとき」）
    違反      禁止: ∃t ∈ W. A ∧ φ             義務: ∃t ∈ W. A ∧ ¬φ

結果:
  violated        違反の証拠がある
  undetermined    違反は見つかっていないが、不明な項目があって結論が変わりうる（missing に足りない項目）
  compliant       評価した時点のどこかで適用され、違反が無い
  not_applicable  適用される時点が無い（対象に合わない、時間外、評価区間に該当する時点が無い）

許可は、選ばなくても違反にならない。単独で評価すると not_applicable を返す。
exception_of を持つ許可は、元の禁止を評価するときに exceptions として渡すと、その適用範囲を狭める。
"""

from __future__ import annotations

from datetime import datetime

from ..models import SceneObject
from .depends import PREDICATE_DEPENDS, attribute_key
from .model import WINDOW_PHASES, Basis, Condition, MissingFact, NormRule, Tri, Verdict, and3, not3, or3
from .predicates import WorldSample, known
from .vocabulary import CONTENTS, PREDICATES


def contact_trace(obj: SceneObject, t: datetime | None = None) -> list[WorldSample]:
    """物体をつかむ候補の予測状態列（つかむ時点で、その物体に触れている）。"""
    return [WorldSample(t=t, phase="contact", contact={obj.id}, holding={obj.id})]


def placement_trace(obj: SceneObject, region_id: str | None, t: datetime | None = None,
                    region_full: dict[str, bool] | None = None) -> list[WorldSample]:
    """配置が終わった時点の状態列（予測なら計画した置き先、観測なら見えた場所）。

    region_full は、収納先を決めるときに調べた「その領域に空きが無いか」（条件 region_full が読む）。"""
    return [WorldSample(t=t, phase="place_complete", object_regions={obj.id: region_id}, holding=set(),
                        region_full=dict(region_full or {}))]


def applies(rule: NormRule, sample: WorldSample, obj: SceneObject | None = None, *,
            requester: str | None = None) -> tuple[Tri, list[MissingFact]]:
    """その時点で、ルールが適用されるか（条件 ∧ 対象）。不明なら、足りない事実も返す。

    収納先を決める義務を選ぶときに使う（内容は見ない）。"""
    missing: dict[tuple[str | None, str], MissingFact] = {}

    def need(entity_id: str | None, key: str) -> None:
        missing.setdefault((entity_id, key), MissingFact(entity_id=entity_id, key=key))

    scope = _scope(rule, sample, obj, requester)
    target = rule.target.matches(obj)
    value = and3(scope, target)
    if value is None:
        if scope is None:
            _need_scope(rule, sample, obj, requester, need)
        if target is None:
            _need_target(rule, obj, need)
    return value, list(missing.values())


def evaluate(
    rule: NormRule,
    trace: list[WorldSample],
    obj: SceneObject | None = None,
    *,
    basis: Basis,
    requester: str | None = None,
    exceptions: list[NormRule] | None = None,
    now: datetime | None = None,
) -> Verdict:
    entity = obj.id if obj is not None else rule.target.id

    def verdict(value: str, detail: str = "", t: datetime | None = None,
                missing: list[MissingFact] | None = None) -> Verdict:
        return Verdict(rule_id=rule.id, value=value, basis=basis, entity_id=entity, t=t,  # type: ignore[arg-type]
                       missing=missing or [], detail=detail, evaluated_at=now)

    if rule.norm == "permission":
        return verdict("not_applicable", "Permissions don't cause violations when not exercised")
    predicate = PREDICATES.get(rule.requirement.predicate)
    if predicate is None:
        raise ValueError(f"{rule.id}: no predicate {rule.requirement.predicate!r}")

    args = _args(rule)
    # 状態ではなく変化を見るか。ルールに書いてあればそれ、無ければ内容の登録（「入る」は外から内へ）
    entry = CONTENTS.get(rule.requirement.predicate)
    tr = rule.requirement.transition
    change = (tr.from_, tr.to) if tr is not None else (entry.transition if entry is not None else None)
    target = rule.target.matches(obj)
    if target is False:
        return verdict("not_applicable", "Doesn't match the target condition")
    phases = WINDOW_PHASES[rule.requirement.window]
    samples = [s for s in trace if s.phase in phases]
    if not samples:
        return verdict("not_applicable", "No moment within the evaluation window")
    active_exceptions = [e for e in exceptions or [] if e.exception_of == rule.id]

    missing: dict[tuple[str | None, str], MissingFact] = {}

    def need(entity_id: str | None, key: str) -> None:
        missing.setdefault((entity_id, key), MissingFact(entity_id=entity_id, key=key))

    applied = False
    previous: Tri = None
    for i, sample in enumerate(samples):
        scope = _scope(rule, sample, obj, requester)
        hits = [(e, and3(_scope(e, sample, obj, requester), e.target.matches(obj))) for e in active_exceptions]
        excepted = or3(*(hit for _, hit in hits))
        applies = and3(scope, target, not3(excepted))

        state = predicate(sample, obj, args)
        phi = state
        if change is not None:
            # 最初の時点には「前」が無いので、変化は起きていない（すでに領域内にいても進入ではない）
            phi = False if i == 0 else and3(_equals(previous, change[0]), _equals(state, change[1]))
        previous = state
        breach = and3(applies, phi if rule.norm == "prohibition" else not3(phi))

        if breach is True:
            what = "a forbidden state / change occurs" if rule.norm == "prohibition" else "the required state isn't reached"
            return verdict("violated", what, t=sample.t)
        if applies is True:
            applied = True
        if breach is None:
            # 何が分かれば結論が出るかを集める
            if scope is None:
                _need_scope(rule, sample, obj, requester, need)
            if target is None:
                _need_target(rule, obj, need)
            if excepted is None:
                for e, hit in hits:
                    if hit is None:
                        _need_scope(e, sample, obj, requester, need)
                        _need_target(e, obj, need)
            if phi is None:
                _need_predicate(rule.requirement.predicate, args, sample, obj, entity, need)

    if missing:
        return verdict("undetermined", "The conclusion depends on missing observations", missing=list(missing.values()))
    if not applied:
        return verdict("not_applicable", "No moment where it applies")
    return verdict("compliant")


def _equals(value: Tri, expected: bool) -> Tri:
    return None if value is None else value == expected


def _args(rule: NormRule) -> dict:  # type: ignore[type-arg]
    """述語に渡す引数。対象が領域のルールは、その領域を zone として渡す（台車が「その領域」に重なるか）。"""
    args = dict(rule.requirement.args)
    if rule.target.kind == "zone" and rule.target.id is not None:
        args.setdefault("zone", rule.target.id)
    return args


def _when(rule: NormRule, sample: WorldSample, obj: SceneObject | None) -> Tri:
    when = rule.scope.when
    return True if when is None else _condition(rule, when, sample, obj)


def _condition(rule: NormRule, c: Condition, sample: WorldSample, obj: SceneObject | None) -> Tri:
    """条件を評価する。all は AND、negate は NOT（どちらも 3 値）。"""
    if c.predicate is not None:
        predicate = PREDICATES.get(c.predicate)
        if predicate is None:
            raise ValueError(f"{rule.id}: no predicate {c.predicate!r}")
        value = predicate(sample, obj, c.args)
    else:
        value = and3(*(_condition(rule, child, sample, obj) for child in c.all))
    return not3(value) if c.negate else value


def _scope(rule: NormRule, sample: WorldSample, obj: SceneObject | None, requester: str | None) -> Tri:
    return and3(rule.scope.active(sample.t, requester), _when(rule, sample, obj))


# 物体でも領域でもない項目（台車、人、時計）は、対象の ID を付けない
GLOBAL_KEYS = ("base_pose", "base_speed", "person_pose", "holding")


def _need_predicate(name: str, args: dict, sample: WorldSample, obj: SceneObject | None,  # type: ignore[type-arg]
                    entity: str | None, need) -> None:  # type: ignore[no-untyped-def]
    """述語が不明のとき、読む項目のうち状態から分からないものを集める（どれも分かるなら、全部を挙げる）。"""
    keys = sorted(PREDICATE_DEPENDS.get(name, frozenset()))
    lacking = [k for k in keys if not known(k, sample, obj, args)] or keys
    for key in lacking:
        if key in GLOBAL_KEYS:
            need(None, key)
        elif key == "zone_shape":
            need(args.get("zone") or entity, key)
        elif key == "region_capacity":
            need(args.get("region"), key)
        else:
            need(entity, key)


def _need_scope(rule: NormRule, sample: WorldSample, obj: SceneObject | None, requester: str | None, need) -> None:  # type: ignore[no-untyped-def]
    if rule.scope.uses_clock and sample.t is None:
        need(None, "clock")
    if rule.scope.requester is not None and requester is None:
        need(None, "requester")
    if rule.scope.when is not None and _when(rule, sample, obj) is None:
        for leaf in rule.scope.when.leaves():
            if _condition(rule, leaf.model_copy(update={"negate": False}), sample, obj) is None:
                _need_predicate(leaf.predicate or "", leaf.args, sample, obj, None, need)


def _need_target(rule: NormRule, obj: SceneObject | None, need) -> None:  # type: ignore[no-untyped-def]
    if rule.target.where is not None and rule.target.matches(obj) is None:
        need(obj.id if obj is not None else None, attribute_key(rule.target.where.attribute))
