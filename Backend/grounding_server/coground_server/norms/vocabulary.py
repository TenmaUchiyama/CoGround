"""語彙の登録簿: ルールに書ける「内容」と「条件」を、1 件ずつここに登録する（設計ガイド §4）。

ルールの枠は 原文 + 規範・条件・対象・内容。そのうち内容と条件は、ここにある名前からしか選べない。
1 件の登録（Entry）が、その語について必要なことをすべて持つ:

  name         名前（ルールの requirement.predicate / scope.when の predicate に書く）
  reads        判定が読む状態の項目（未確定のとき「何が足りないか」を答えるのにも使う）
  evaluate     ある時点の状態 -> True / False / None（不明）。predicates.py の関数
  window       内容だけ: 計画や実行のどこを調べるか（W。住人は書かない）
  transition   内容だけ: 状態ではなく変化を見るとき（「入る」= 外から内へ）
  checked      内容だけ: どの時点の予測で調べるか（grasp: つかむ時点 / place: 置いた時点 / motion: 台車が動く間）
  response     内容だけ: 実行中に破りそうになったときの応答（replan: 避ける経路を計画し直す / hold: 台車を止めて待つ）
  targets      内容だけ: 対象に取れる種類（object / zone / robot）
  phrase       説明に使う言い方
  description  LLM に見せる説明（ルール登録のプロンプトは、この登録簿から作る）
  args         引数の名前 -> 説明。required は必ず要る引数

内容は、ロボットが変えられる状態（ROBOT_STATES）のそれぞれについて用意する。
「ロボットが変えられる状態のすべてについて、住人が規範を書ける」ことを coverage() で確かめられる。

内容や条件を足すとき: predicates.py に関数を書き、ここに 1 件足す。ほか（登録の検査、LLM のプロンプト、
判定、監視、説明）は登録簿を読むので、手を入れない。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from . import predicates as P

Checked = Literal["grasp", "place", "motion"]
Response = Literal["stop", "hold", "replan"]

# ロボットが自分の動作で変えられる状態（スキル: navigate / pick / place）
ROBOT_STATES: dict[str, str] = {
    "base_pose": "where the base is (navigate)",
    "base_speed": "how fast the base moves (navigate)",
    "contact": "which object the robot touches (pick / place)",
    "holding": "which object the robot holds (pick / place)",
    "object_region": "which zone an object is in (place)",
}


@dataclass(frozen=True)
class Entry:
    name: str
    reads: frozenset[str]
    evaluate: P.Predicate
    phrase: str
    description: str
    args: dict[str, str] = field(default_factory=dict)
    required: tuple[str, ...] = ()
    defaults: dict[str, object] = field(default_factory=dict)  # 引数を省いたときの値（説明に使う）
    # ここから下は内容だけ
    targets: tuple[str, ...] = ()
    window: str = "whole"
    transition: tuple[bool, bool] | None = None
    checked: frozenset[str] = frozenset()
    response: Response | None = None
    legacy: bool = False  # 前の名前。読めるが、LLM には見せない


def _reads(*keys: str) -> frozenset[str]:
    return frozenset(keys)


CONTENTS: dict[str, Entry] = {e.name: e for e in [
    Entry(
        name="contact", reads=_reads("contact"), evaluate=P.contact, targets=("object",),
        window="whole", checked=frozenset({"grasp"}),
        phrase="the robot touches it",
        description='the robot is touching that object. "Don\'t touch ..." is a prohibition',
    ),
    Entry(
        name="holding", reads=_reads("holding"), evaluate=P.holding, targets=("object",),
        window="whole", checked=frozenset({"grasp"}),
        phrase="the robot holds it",
        description='the robot is holding (carrying) that object. "Don\'t carry ..." is a prohibition',
    ),
    Entry(
        name="placed_in", reads=_reads("object_region"), evaluate=P.placed_in, targets=("object",),
        window="at_place_complete", checked=frozenset({"place"}),
        args={"region": 'id of the zone, chosen from the "zones"'}, required=("region",),
        phrase="it is placed in {region}",
        description='that object is in the zone args.region when placing is finished. "Put (store) ... in ..." is an obligation; '
                    '"Don\'t put ... in ..." is a prohibition',
    ),
    Entry(
        name="enter_zone", reads=_reads("base_pose", "zone_shape"), evaluate=P.footprint_overlaps, targets=("zone",),
        window="during_base_motion", transition=(False, True), checked=frozenset({"motion"}), response="replan",
        args={"zone": "filled in from the target zone"},
        phrase="the base enters the zone",
        description='the base goes from outside the target zone to inside it (already being inside is not entering). '
                    '"Don\'t go into ..." is a prohibition, target is a zone',
    ),
    Entry(
        name="in_zone", reads=_reads("base_pose", "zone_shape"), evaluate=P.footprint_overlaps, targets=("zone",),
        window="during_base_motion", checked=frozenset({"motion"}), response="replan",
        args={"zone": "filled in from the target zone"},
        phrase="the base is inside the zone",
        description='the base is inside the target zone (also when it was already there). '
                    '"Don\'t be in ..." / "Stay out of ..." is a prohibition, target is a zone',
    ),
    Entry(
        name="base_stopped", reads=_reads("base_speed"), evaluate=P.base_stopped, targets=("robot",),
        window="whole", checked=frozenset({"motion"}), response="hold",
        phrase="the base is stopped",
        description='the base is stopped. "Stop when ..." is an obligation, target is the robot, with the situation in scope.when',
    ),
    Entry(
        name="speed_below", reads=_reads("base_speed"), evaluate=P.speed_below, targets=("robot",),
        window="whole", checked=frozenset({"motion"}), response="hold",
        args={"limit": "speed limit in m/s"}, required=("limit",),
        phrase="the base moves at {limit} m/s or slower",
        description='the base speed is at most args.limit m/s. "Move slowly (at most ...) when ..." is an obligation, target is the robot',
    ),
    # 前の名前（状態としての重なり。transition を付ければ進入）。保存済みのルールを読むために残す
    Entry(
        name="footprint_overlaps", reads=_reads("base_pose", "zone_shape"), evaluate=P.footprint_overlaps, targets=("zone",),
        window="during_base_motion", checked=frozenset({"motion"}), response="replan", legacy=True,
        phrase="the base overlaps the zone", description="(old name) use enter_zone or in_zone",
    ),
]}

CONDITIONS: dict[str, Entry] = {e.name: e for e in [
    Entry(
        name="near_person", reads=_reads("base_pose", "person_pose"), evaluate=P.near_person,
        args={"kind": "child | adult | any (default any)", "distance": "metres (default 5.0)"},
        defaults={"kind": "any", "distance": 5.0},
        phrase="a person ({kind}) is within {distance} m of the base",
        description="a person of args.kind is within args.distance m of the base",
    ),
    Entry(
        name="holding_something", reads=_reads("holding"), evaluate=P.holding_something,
        phrase="the robot is carrying something",
        description="the robot is holding any object",
    ),
    Entry(
        name="base_in_zone", reads=_reads("base_pose", "zone_shape"), evaluate=P.footprint_overlaps,
        args={"zone": "id of a zone"}, required=("zone",),
        phrase="the base is inside {zone}",
        description="the base is inside the zone args.zone",
    ),
    Entry(
        name="region_full", reads=_reads("region_capacity"), evaluate=P.region_full,
        args={"region": 'id of a zone, chosen from the "zones"'}, required=("region",),
        phrase="{region} has no free space",
        description="there is no free space left to put the object in the zone args.region",
    ),
    Entry(
        name="near_child", reads=_reads("base_pose", "person_pose"), evaluate=P.near_child, legacy=True,
        args={"distance": "metres (default 5.0)"}, defaults={"distance": 5.0},
        phrase="a child is within {distance} m of the base", description="(old name) near_person with kind = child",
    ),
]}

# 内容も条件として使える（「止まっているとき」など）。名前が重なれば条件の登録が先
ALL: dict[str, Entry] = {**CONTENTS, **CONDITIONS}

PREDICATES: dict[str, P.Predicate] = {name: e.evaluate for name, e in ALL.items()}
READS: dict[str, frozenset[str]] = {name: e.reads for name, e in ALL.items()}


def register(kind: Literal["content", "condition"], entry: Entry) -> None:
    """内容か条件を 1 件足す（同じ名前があれば置き換える）。足すのに必要な手続きは、これだけ。"""
    (CONTENTS if kind == "content" else CONDITIONS)[entry.name] = entry
    ALL.clear()
    ALL.update({**CONTENTS, **CONDITIONS})
    PREDICATES.clear()
    PREDICATES.update({name: e.evaluate for name, e in ALL.items()})
    READS.clear()
    READS.update({name: e.reads for name, e in ALL.items()})


def unregister(kind: Literal["content", "condition"], name: str) -> None:
    (CONTENTS if kind == "content" else CONDITIONS).pop(name, None)
    for table in (ALL, PREDICATES, READS):
        table.pop(name, None)
    if name in CONTENTS or name in CONDITIONS:  # もう一方に同じ名前が残っていれば、そちらに戻す
        register("content" if name in CONTENTS else "condition", (CONTENTS.get(name) or CONDITIONS[name]))


def content(name: str | None) -> Entry | None:
    return CONTENTS.get(name or "")


def condition(name: str | None) -> Entry | None:
    return ALL.get(name or "")


def default_window(name: str | None) -> str:
    entry = content(name)
    return entry.window if entry is not None else "whole"


def coverage() -> dict[str, list[str]]:
    """ロボットが変えられる状態 -> その状態について書ける内容の名前。空の項目があれば、書けない状態がある。"""
    return {state: [e.name for e in CONTENTS.values() if state in e.reads and not e.legacy] for state in ROBOT_STATES}


def check(kind: Literal["content", "condition"], name: str, args: dict, target_kind: str | None = None) -> str | None:  # type: ignore[type-arg]
    """その名前・引数・対象の種類で書けるか。書けなければ理由（書ければ None）。登録のときに使う。"""
    table = CONTENTS if kind == "content" else ALL
    entry = table.get(name)
    if entry is None:
        known = ", ".join(n for n, e in table.items() if not e.legacy)
        return f"not supported: no {kind} named {name!r} (supported: {known})"
    lacking = [a for a in entry.required if args.get(a) is None]
    if lacking:
        return f"{name} needs {', '.join(lacking)}"
    if kind == "content" and target_kind is not None and entry.targets and target_kind not in entry.targets:
        return f"{name} is about a {' / '.join(entry.targets)}, not a {target_kind}"
    return None


def describe(kind: Literal["content", "condition"]) -> str:
    """LLM のプロンプトに入れる一覧（登録簿から作る）。"""
    lines = []
    for e in (CONTENTS if kind == "content" else CONDITIONS).values():
        if e.legacy:
            continue
        args = "; ".join(f"args.{k}: {v}" for k, v in e.args.items() if not v.startswith("filled in"))
        lines.append(f"- {e.name:<18} {e.description}" + (f" ({args})" if args else ""))
    return "\n".join(lines)


def phrase(name: str, args: dict | None = None) -> str:  # type: ignore[type-arg]
    """説明に使う言い方（引数を埋める。無い引数は ? にする）。"""
    entry = ALL.get(name)
    if entry is None:
        return name

    class _Fill(dict):  # type: ignore[type-arg]
        def __missing__(self, key: str) -> str:
            return "?"

    return entry.phrase.format_map(_Fill({**entry.defaults, **(args or {})}))


def export() -> dict[str, list[dict[str, object]]]:
    """表示する側（Unity）に渡す語彙。state の vocabulary に入れる。

    表示する側は、内容や条件の名前を自分で持たず、ここから説明の言い方（phrase）や応答を読む
    （内容を足しても、表示する側に手を入れなくてよい）。"""
    def row(e: Entry, is_content: bool) -> dict[str, object]:
        out: dict[str, object] = {"name": e.name, "phrase": e.phrase, "defaults": dict(e.defaults), "legacy": e.legacy,
                                  "reads": sorted(e.reads)}
        if is_content:
            out.update({"targets": list(e.targets), "checked": sorted(e.checked), "response": e.response,
                        "event": e.transition is not None})
        return out

    return {"contents": [row(e, True) for e in CONTENTS.values()],
            "conditions": [row(e, False) for e in CONDITIONS.values()]}
