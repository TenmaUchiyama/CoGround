"""ルールとシーンから Plan の step を作る（M0）。LLM は使わない。

やること:
  1. ルール照合   運ぶ物（role = item）ごとに、条件が合うルールを探す
  2. 目標         合ったルールの target_region を行き先にする。すでにそこにあれば何もしない
  3. 置き位置     行き先の領域の中で、ほかの物と重ならない場所を選ぶ（中央に近い順）
  4. 順序         シーンの物体の並び順のまま

まだやらないこと: 動作計画（MoveIt に聞いて infeasible を付ける）、順序の工夫、修正（locked）の引き継ぎ。

step になるのは「ルールに合い、行き先がいまの場所と違う物」だけ。ルールに合わない物は step にしない。
  ok         行き先が 1 つに決まった
  ambiguous  合うルールが複数あり、行き先が違う（to は null、候補は candidate_rule_ids）
  unmatched  合ったルールの行き先の領域がシーンに無い（to は null、message に理由）
"""

from __future__ import annotations

from .models import Placement, Pose, Quat, Rule, SceneObject, SceneRegion, SceneSnapshot, Step, Vec3

DEFAULT_SIZE = 0.1  # size が無い物体の大きさ [m]
MARGIN = 0.02  # 物どうしの間に空けるすき間 [m]
GRID = 0.05  # 置き位置の候補の間隔 [m]

Disc = tuple[float, float, float]  # 床面（XZ）での中心 x, z と半径


def plan_steps(scene: SceneSnapshot, rules: list[Rule]) -> list[Step]:
    regions = {r.id: r for r in scene.regions}

    # 1・2. 物体ごとに、合うルールと行き先を決める
    decided: list[tuple[SceneObject, list[Rule]]] = []
    for obj in scene.objects:
        if obj.role != "item":
            continue
        matched = [r for r in rules if r.condition.matches(obj)]
        if not matched:
            continue
        targets = {r.target_region for r in matched}
        if len(targets) == 1 and matched[0].target_region == obj.region_id:
            continue  # もう行き先にある
        decided.append((obj, matched))

    # 行き先が決まって動かす物は、いまの場所からいなくなるので障害物に数えない
    moving = {obj.id for obj, matched in decided if _single_target(matched) in regions}
    occupied: dict[str, list[Disc]] = {}
    for o in scene.objects:
        if o.region_id is not None and o.id not in moving:
            occupied.setdefault(o.region_id, []).append(_disc(o, o.position))

    # 3・4. 置き位置を決めて step にする
    steps: list[Step] = []
    for obj, matched in decided:
        index = len(steps)
        common = {
            "id": f"s{index + 1}",
            "index": index,
            "object_id": obj.id,
            "from": Placement(region_id=obj.region_id, pose=obj.pose),
        }
        target = _single_target(matched)
        if target is None:
            steps.append(Step(**common, status="ambiguous", candidate_rule_ids=[r.id for r in matched],
                              message="合うルールが複数あり、行き先が違う"))
            continue
        rule = matched[0]
        region = regions.get(target)
        if region is None:
            steps.append(Step(**common, status="unmatched", rule_id=rule.id,
                              message=f"行き先の領域 {target!r} がシーンに無い"))
            continue

        taken = occupied.setdefault(target, [])
        position, free = _choose_position(obj, region, taken)
        taken.append(_disc(obj, position))
        owner_is_receptacle = any(o.id == region.object_id and o.role == "receptacle" for o in scene.objects)
        steps.append(Step(
            **common,
            to=Placement(region_id=target, pose=Pose(position=position, rotation=obj.rotation)),
            rule_id=rule.id,
            status="ok",
            # シンクやごみ箱は重なってもよいので、何も言わない
            message=None if free or owner_is_receptacle else "空いている場所が無いので、中央に重ねて置く",
        ))
    return steps


def _single_target(matched: list[Rule]) -> str | None:
    targets = {r.target_region for r in matched}
    return matched[0].target_region if len(targets) == 1 else None


def _extent(obj: SceneObject) -> Vec3:
    return obj.size if obj.size is not None else (DEFAULT_SIZE, DEFAULT_SIZE, DEFAULT_SIZE)


def _disc(obj: SceneObject, position: Vec3) -> Disc:
    size = _extent(obj)
    return (position[0], position[2], max(size[0], size[2]) / 2)


def _choose_position(obj: SceneObject, region: SceneRegion, taken: list[Disc]) -> tuple[Vec3, bool]:
    """領域の中で obj を置く位置（bbox 中心）と、重ならずに置けたかを返す。"""
    size = _extent(obj)
    radius = max(size[0], size[2]) / 2

    def is_free(p: Vec3) -> bool:
        return all((p[0] - x) ** 2 + (p[2] - z) ** 2 >= (radius + r + MARGIN) ** 2 for x, z, r in taken)

    if region.box is None:
        # 床面のポリゴンだけの領域: 重心に置く
        poly = region.polygon or []
        n = len(poly)
        p = _round((sum(v[0] for v in poly) / n, sum(v[1] for v in poly) / n + size[1] / 2, sum(v[2] for v in poly) / n))
        return p, is_free(p)

    box = region.box
    y = -box.size[1] / 2 + size[1] / 2  # 領域の底に置く（ローカル座標）
    center = _round(_add(box.center, _rotate(box.rotation, (0.0, y, 0.0))))
    for lx, lz in _grid(box.size[0] / 2 - radius, box.size[2] / 2 - radius):
        p = _round(_add(box.center, _rotate(box.rotation, (lx, y, lz))))
        if is_free(p):
            return p, True
    return center, False


def _grid(half_x: float, half_z: float) -> list[tuple[float, float]]:
    """領域のローカル XZ 面の候補点。中央に近い順（同じ距離なら x、z の小さい順）。"""
    nx = int(max(half_x, 0.0) / GRID + 1e-9)
    nz = int(max(half_z, 0.0) / GRID + 1e-9)
    points = [(i * GRID, j * GRID) for i in range(-nx, nx + 1) for j in range(-nz, nz + 1)]
    return sorted(points, key=lambda p: (round(p[0] ** 2 + p[1] ** 2, 9), p[0], p[1]))


def _add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _round(v: Vec3) -> Vec3:
    return (round(v[0], 4), round(v[1], 4), round(v[2], 4))


def _rotate(q: Quat, v: Vec3) -> Vec3:
    """v を q で回す（ローカル -> ワールド）。q は単位四元数とみなす。"""
    x, y, z, w = q
    cx, cy, cz = y * v[2] - z * v[1], z * v[0] - x * v[2], x * v[1] - y * v[0]
    ccx, ccy, ccz = y * cz - z * cy, z * cx - x * cz, x * cy - y * cx
    return (v[0] + 2 * (w * cx + ccx), v[1] + 2 * (w * cy + ccy), v[2] + 2 * (w * cz + ccz))
