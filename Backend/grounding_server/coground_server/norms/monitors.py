"""実行中に見張る条件（monitors）と、台車の動きに対する判定（R2・R4）。

台車が動く間に調べるルール（monitored()）を、ルールごとに 1 つの監視にする。応答は内容の登録（vocabulary.py）が決める:

  response = replan  領域への進入の禁止（R2）。入りそうになったら境界の手前で待ち、領域を避ける経路を計画し直す
  response = hold    それ以外（R4: 子供が近くにいる間は台車を止める）。条件が解けるまで台車を止めておく
  response = stop    いまは使っていない（スキルを取り消す。hold と違い、続きから再開しない）

route_verdicts()   計画した経路（台車の予測軌跡）を、進入の禁止で判定する（動作計画と、hold のあとの再検証で使う）
motion_verdicts()  いまの位置から少し進んだら違反するか、を判定する（実行中の監視）
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field

from ..models import Verdict
from .depends import depends_on
from .evaluate import evaluate
from .geometry import FOOTPRINT_RADIUS, Point, densify, polygon_distance
from .model import NormRule
from .predicates import PersonAt, WorldSample
from .vocabulary import CONTENTS

Response = Literal["stop", "hold", "replan"]

ROUTE_STEP = 0.05   # 経路を判定するときの刻み [m]
MOVING_SPEED = 0.4  # 「動いたら」を調べるときに仮定する速さ [m/s]


class MonitorSpec(BaseModel):
    rule_id: str
    predicate: str
    entities: list[str] = Field(default_factory=list, description="見張る相手（領域の ID、child など）")
    response: Response


def is_zone_entry(rule: NormRule) -> bool:
    """領域に入る／中にいることの禁止（避ける経路を計画し直して応じるルール）。"""
    entry = CONTENTS.get(rule.requirement.predicate)
    return (rule.norm == "prohibition" and rule.target.kind == "zone" and rule.target.id is not None
            and entry is not None and entry.response == "replan")


def monitored(norms: list[NormRule]) -> list[NormRule]:
    """台車が動く間に調べるルール（許可は除く）。

    スキルで絞らず、すべてのルールを見て、内容か条件が台車の動きに関係するものを選ぶ:
    内容が「台車が動く間に調べる」もの（vocabulary の checked = motion）か、条件が台車の位置・速さを読むもの。"""
    return [r for r in norms if r.norm != "permission" and _moves_with_base(r)]


def _moves_with_base(rule: NormRule) -> bool:
    entry = CONTENTS.get(rule.requirement.predicate)
    if entry is not None and "motion" in entry.checked:
        return True
    return bool(depends_on(rule) & {"base_pose", "base_speed"})


def spec_for(rule: NormRule) -> MonitorSpec:
    if is_zone_entry(rule):
        return MonitorSpec(rule_id=rule.id, predicate=rule.requirement.predicate, entities=[rule.target.id or ""],
                           response="replan")
    leaves = rule.scope.when.leaves() if rule.scope.when is not None else []
    people = [leaf for leaf in leaves if leaf.predicate in ("near_child", "near_person")]
    if people:
        kind = "child" if people[0].predicate == "near_child" else str(people[0].args.get("kind") or "any")
        entities = ["person" if kind == "any" else kind]
    else:
        entities = [rule.target.id] if rule.target.id else []
    return MonitorSpec(rule_id=rule.id, predicate=(leaves[0].predicate or "") if leaves else rule.requirement.predicate,
                       entities=entities, response="hold")


def build_monitors(norms: list[NormRule]) -> list[MonitorSpec]:
    return [spec_for(r) for r in monitored(norms)]


def _permissions(norms: list[NormRule]) -> list[NormRule]:
    return [n for n in norms if n.norm == "permission"]


def route_verdicts(
    norms: list[NormRule], track: list[list[float]], start: datetime, zones: dict[str, list[Point]], *,
    requester: str | None = None, now: datetime | None = None, spans: list[tuple[float, float]] | None = None,
    holding: set[str] | None = None,
) -> list[Verdict]:
    """台車の予測軌跡 track = [[t, x, y, yaw], ...]（t は start からの秒）を、領域への進入の禁止で判定する。

    spans を渡すと、その時間の範囲（台車が動く区間）だけを調べる。
    通る時刻は start + t。禁止が効いていない時刻に通るなら非適用（17:58 に入る経路は、18 時からの禁止に反しない）。
    """
    rules = [r for r in monitored(norms) if is_zone_entry(r)]
    if not rules:
        return []
    points: list[list[float]] = []
    for t0, t1 in spans if spans is not None else [(track[0][0], track[-1][0])] if track else []:
        points.extend(densify(track, ROUTE_STEP, t0, t1))
    trace = [WorldSample(t=start + timedelta(seconds=p[0]), phase="base_motion", base=(p[1], p[2], p[3]),
                         base_speed=MOVING_SPEED, zones=zones, holding=holding) for p in points]
    return [evaluate(r, trace, None, basis="predicted", requester=requester, exceptions=_permissions(norms), now=now)
            for r in rules]


def motion_verdicts(
    norms: list[NormRule], base: tuple[float, float, float] | None, heading: Point | None, reach: float, now: datetime,
    zones: dict[str, list[Point]], people: list[PersonAt] | None, *, speed: float | None = 0.0,
    requester: str | None = None, skip_zones: frozenset[str] | set[str] = frozenset(),
    holding: set[str] | None = None,
) -> list[tuple[MonitorSpec, Verdict]]:
    """いまの位置 base から heading の向きへ reach [m] 進んだら違反するか（予測）。

    最初の時点はいまの状態（速さは speed）、その先は「動いている」と仮定した状態。
    skip_zones の領域は、経路がもう避けているので調べない。holding は、いま持っている物体（分からなければ None）。
    """
    out: list[tuple[MonitorSpec, Verdict]] = []
    samples = [WorldSample(t=now, phase="base_motion", base=base, base_speed=speed, zones=zones, people=people, holding=holding)]
    if base is None:
        samples.append(WorldSample(t=now, phase="base_motion", base=None, base_speed=MOVING_SPEED, zones=zones, people=people, holding=holding))
    else:
        norm = math.hypot(*heading) if heading is not None else 0.0
        steps = max(1, math.ceil(reach / 0.1)) if norm > 0 else 1
        for k in range(1, steps + 1):
            d = reach * k / steps if norm > 0 else 0.0
            ux, uy = (heading[0] / norm, heading[1] / norm) if norm > 0 and heading is not None else (0.0, 0.0)
            samples.append(WorldSample(
                t=now + timedelta(seconds=d / MOVING_SPEED), phase="base_motion",
                base=(base[0] + ux * d, base[1] + uy * d, base[2]), base_speed=MOVING_SPEED, zones=zones, people=people, holding=holding))
    for rule in monitored(norms):
        spec = spec_for(rule)
        if spec.response == "replan" and rule.target.id in skip_zones:
            continue
        out.append((spec, evaluate(rule, samples, None, basis="predicted", requester=requester,
                                   exceptions=_permissions(norms), now=now)))
    return out


def entity_distance(rule: NormRule, base: tuple[float, float, float] | None, zones: dict[str, list[Point]],
                    people: list[PersonAt] | None) -> float | None:
    """台車と、そのルールが見張る相手との距離 [m]（領域なら外形から境界まで、子供なら中心から）。分からなければ None"""
    if base is None:
        return None
    if is_zone_entry(rule):
        polygon = zones.get(rule.target.id or "")
        return None if polygon is None else round(max(0.0, polygon_distance((base[0], base[1]), polygon) - FOOTPRINT_RADIUS), 3)
    if people is None:
        return None
    children = [p for p in people if p.kind in ("child", "unknown")]
    if not children:
        return None
    return round(min(math.hypot(p.xy[0] - base[0], p.xy[1] - base[1]) for p in children), 3)
