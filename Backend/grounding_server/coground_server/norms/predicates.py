"""述語: ある時点の状態（WorldSample）について True / False / None（不明）を返す関数。

    f(sample, obj, args) -> Tri

ここには関数だけを置く。名前・読む項目・調べる時点・実行中の応答・説明文は vocabulary.py に 1 件ずつ登録する
（内容や条件を足すときは、ここに関数を書き、vocabulary.py に 1 件足す）。
known() は「その項目が状態から分かるか」を答える（未確定のとき、足りない事実を挙げるのに使う）。
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel, Field

from ..models import PersonKind, SceneObject
from .geometry import FOOTPRINT_RADIUS, Point, circle_overlaps
from .model import Phase, Tri

STOPPED_SPEED = 0.02  # これより遅ければ止まっているとみなす [m/s]
DEFAULT_PERSON_DISTANCE = 5.0
DEFAULT_CHILD_DISTANCE = DEFAULT_PERSON_DISTANCE


class PersonAt(BaseModel):
    """ある時点の人の位置（ROS の world の x, y）。"""

    id: str
    kind: PersonKind = "unknown"
    xy: Point


class WorldSample(BaseModel):
    """ある時点の状態。計画の予測（τπ）も実行中の観測（τobs）も同じ形にする。

    分からない項目は入れない（object_regions にキーが無い = その物体の場所は不明）。
    """

    t: datetime | None = Field(default=None, description="家の時計の時刻。分からなければ null")
    phase: Phase = "other"
    contact: set[str] = Field(default_factory=set, description="ロボットが触れている物体の ID")
    object_regions: dict[str, str | None] = Field(
        default_factory=dict, description="物体 ID -> いまある領域の ID（領域の外なら null）")
    base: tuple[float, float, float] | None = Field(
        default=None, description="台車（base_link）の位置 [x, y, yaw]（ROS の world）。分からなければ null")
    base_speed: float | None = Field(default=None, description="台車の速さ [m/s]。分からなければ null")
    zones: dict[str, list[Point]] = Field(default_factory=dict, description="領域 ID -> 床の多角形（ROS の x, y）")
    people: list[PersonAt] | None = Field(default=None, description="人の位置。観測できていなければ null")
    holding: set[str] | None = Field(default=None, description="ロボットが持っている物体の ID。分からなければ null")
    region_full: dict[str, bool] = Field(
        default_factory=dict, description="領域 ID -> その物を置く空きが無いか。キーが無ければ不明")


Predicate = Callable[[WorldSample, SceneObject | None, dict[str, Any]], Tri]


def contact(sample: WorldSample, obj: SceneObject | None, args: dict[str, Any]) -> Tri:
    """ロボットがその物体に触れている。"""
    if obj is None:
        return None
    return obj.id in sample.contact


def placed_in(sample: WorldSample, obj: SceneObject | None, args: dict[str, Any]) -> Tri:
    """その物体が args["region"] の領域にある。場所が分からなければ不明。"""
    if obj is None or obj.id not in sample.object_regions:
        return None
    return sample.object_regions[obj.id] == args.get("region")


def footprint_overlaps(sample: WorldSample, obj: SceneObject | None, args: dict[str, Any]) -> Tri:
    """台車の外形（円）が args["zone"] の領域に重なっている。台車の位置か領域の形が分からなければ不明。"""
    polygon = sample.zones.get(args.get("zone") or "")
    if sample.base is None or polygon is None:
        return None
    return circle_overlaps((sample.base[0], sample.base[1]), float(args.get("radius") or FOOTPRINT_RADIUS), polygon)


def near_person(sample: WorldSample, obj: SceneObject | None, args: dict[str, Any]) -> Tri:
    """人が台車から args["distance"] m 以内にいる。args["kind"] = child / adult / any（既定 any）。

    人の位置が観測できていなければ不明。近くにいる人の種類が分からないときも不明（該当する人がいれば True）。
    """
    if sample.base is None or sample.people is None:
        return None
    limit = float(args.get("distance") or DEFAULT_PERSON_DISTANCE)
    kind = args.get("kind") or "any"
    near = [p for p in sample.people if math.hypot(p.xy[0] - sample.base[0], p.xy[1] - sample.base[1]) <= limit]
    if kind == "any":
        return bool(near)
    if any(p.kind == kind for p in near):
        return True
    return None if any(p.kind == "unknown" for p in near) else False


def near_child(sample: WorldSample, obj: SceneObject | None, args: dict[str, Any]) -> Tri:
    """子供が台車から args["distance"] m 以内にいる（near_person の kind = child）。"""
    return near_person(sample, obj, {**args, "kind": "child"})


def base_stopped(sample: WorldSample, obj: SceneObject | None, args: dict[str, Any]) -> Tri:
    """台車が止まっている。速さが分からなければ不明。"""
    return None if sample.base_speed is None else sample.base_speed < STOPPED_SPEED


def speed_below(sample: WorldSample, obj: SceneObject | None, args: dict[str, Any]) -> Tri:
    """台車の速さが args["limit"] m/s 以下。速さか上限が分からなければ不明。"""
    limit = args.get("limit")
    if sample.base_speed is None or not isinstance(limit, (int, float)):
        return None
    return sample.base_speed <= float(limit)


def holding(sample: WorldSample, obj: SceneObject | None, args: dict[str, Any]) -> Tri:
    """ロボットがその物体を持っている。"""
    if obj is None or sample.holding is None:
        return None
    return obj.id in sample.holding


def holding_something(sample: WorldSample, obj: SceneObject | None, args: dict[str, Any]) -> Tri:
    """ロボットが何かを持っている。"""
    return None if sample.holding is None else bool(sample.holding)


def region_full(sample: WorldSample, obj: SceneObject | None, args: dict[str, Any]) -> Tri:
    """args["region"] の領域に、その物を置く空きが無い。調べていなければ不明。"""
    return sample.region_full.get(args.get("region") or "")


def known(key: str, sample: WorldSample, obj: SceneObject | None, args: dict[str, Any]) -> bool:
    """項目 key（depends.py のキー）が、この状態から分かるか。"""
    if key == "base_pose":
        return sample.base is not None
    if key == "base_speed":
        return sample.base_speed is not None
    if key == "zone_shape":
        return (args.get("zone") or "") in sample.zones
    if key == "holding":
        return sample.holding is not None
    if key == "region_capacity":
        return (args.get("region") or "") in sample.region_full
    if key == "person_pose":
        return sample.people is not None and not any(p.kind == "unknown" for p in sample.people)
    if key == "object_region":
        return obj is not None and obj.id in sample.object_regions
    return False
