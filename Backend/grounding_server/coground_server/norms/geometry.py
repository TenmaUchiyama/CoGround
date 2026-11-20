"""床の上の幾何（ROS の world の x, y。メートル）。ゾーンへの進入（R2）と、人との距離（R4）の判定に使う。

  region_polygon(region)            領域（床面のポリゴン、または box の底面）を ROS の x, y の多角形にする
  circle_overlaps(p, radius, poly)  台車の外形（中心 p、半径 radius の円）が多角形に重なるか
  route_around(start, goal, ...)    多角形を避けて進む折れ線（ROS なしの代役のロボットが使う）
  densify(track, step)              台車の予測軌跡 [[t, x, y, yaw], ...] を、細かい間隔に補間する

台車の外形は円（Fetch の台車。半径は move_base の costmap と同じ 0.30 m。COGROUND_ROBOT_RADIUS で変える）。
"""

from __future__ import annotations

import heapq
import math
import os

from ..models import Quat, SceneRegion, Vec3

Point = tuple[float, float]

FOOTPRINT_RADIUS = float(os.environ.get("COGROUND_ROBOT_RADIUS") or 0.30)


def unity_xy(p: Vec3 | list[float]) -> Point:
    """Unity のワールド座標（左手系、Y 上）-> ROS の world の (x, y)。robot.unity_to_ros と同じ"""
    return (p[2], -p[0])


def _rotate(q: Quat, v: Vec3) -> Vec3:
    x, y, z, w = q
    cx, cy, cz = y * v[2] - z * v[1], z * v[0] - x * v[2], x * v[1] - y * v[0]
    ccx, ccy, ccz = y * cz - z * cy, z * cx - x * cz, x * cy - y * cx
    return (v[0] + 2 * (w * cx + ccx), v[1] + 2 * (w * cy + ccy), v[2] + 2 * (w * cz + ccz))


def region_polygon(region: SceneRegion) -> list[Point]:
    """領域を床に落とした多角形（ROS の x, y）。polygon があればそれ、無ければ box の底面の 4 隅。"""
    if region.polygon is not None:
        return [unity_xy(p) for p in region.polygon]
    box = region.box
    assert box is not None
    hx, hz = box.size[0] / 2, box.size[2] / 2
    corners = []
    for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        d = _rotate(box.rotation, (sx * hx, 0.0, sz * hz))
        corners.append(unity_xy((box.center[0] + d[0], box.center[1] + d[1], box.center[2] + d[2])))
    return corners


def point_in_polygon(p: Point, poly: list[Point]) -> bool:
    inside = False
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > p[1]) != (y2 > p[1]) and p[0] < (x2 - x1) * (p[1] - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _point_segment(p: Point, a: Point, b: Point) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    f = 0.0 if length2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2))
    return math.hypot(p[0] - (a[0] + f * dx), p[1] - (a[1] + f * dy))


def polygon_distance(p: Point, poly: list[Point]) -> float:
    """点から多角形までの距離（中にあれば 0）。"""
    if point_in_polygon(p, poly):
        return 0.0
    return min(_point_segment(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def circle_overlaps(p: Point, radius: float, poly: list[Point]) -> bool:
    return polygon_distance(p, poly) < radius


def _cross(o: Point, a: Point, b: Point) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _segments_cross(a: Point, b: Point, c: Point, d: Point) -> bool:
    d1, d2, d3, d4 = _cross(c, d, a), _cross(c, d, b), _cross(a, b, c), _cross(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def segment_polygon_distance(a: Point, b: Point, poly: list[Point]) -> float:
    """線分 a-b と多角形の距離（交わる・中を通るなら 0）。"""
    if point_in_polygon(a, poly) or point_in_polygon(b, poly):
        return 0.0
    best = math.inf
    for i in range(len(poly)):
        c, d = poly[i], poly[(i + 1) % len(poly)]
        if _segments_cross(a, b, c, d):
            return 0.0
        best = min(best, _point_segment(a, c, d), _point_segment(b, c, d), _point_segment(c, a, b), _point_segment(d, a, b))
    return best


def _hull(points: list[Point]) -> list[Point]:
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts
    lower: list[Point] = []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[Point] = []
    for p in reversed(pts):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def route_around(start: Point, goal: Point, polygons: list[list[Point]], clearance: float) -> list[Point] | None:
    """polygons から clearance 以上離れて start から goal へ行く折れ線（start と goal を含む）。行けなければ None。

    多角形ごとに、凸包の頂点を外へ広げた点を経由点の候補にして、最短の道を探す（可視グラフ）。
    start がすでに多角形に近い（中にいる）ときは、その多角形から出る最初の 1 本だけは通してよい。
    """
    if any(polygon_distance(goal, poly) < clearance for poly in polygons):
        return None
    start_in = [polygon_distance(start, poly) < clearance for poly in polygons]

    def clear(a: Point, b: Point, from_start: bool) -> bool:
        return all((from_start and start_in[i]) or segment_polygon_distance(a, b, poly) >= clearance - 1e-6
                   for i, poly in enumerate(polygons))

    if clear(start, goal, True):
        return [start, goal]
    nodes: list[Point] = [start, goal]
    for poly in polygons:
        hull = _hull(poly)
        cx, cy = sum(p[0] for p in hull) / len(hull), sum(p[1] for p in hull) / len(hull)
        for v in hull:
            d = math.hypot(v[0] - cx, v[1] - cy) or 1.0
            out = clearance * math.sqrt(2) + 0.05
            p = (v[0] + (v[0] - cx) / d * out, v[1] + (v[1] - cy) / d * out)
            if all(polygon_distance(p, other) >= clearance for other in polygons):
                nodes.append(p)
    # Dijkstra（頂点が少ないので、辺はその場で調べる）
    best = {0: 0.0}
    prev: dict[int, int] = {}
    heap = [(0.0, 0)]
    while heap:
        cost, i = heapq.heappop(heap)
        if cost > best.get(i, math.inf):
            continue
        if i == 1:
            path = [1]
            while path[-1] != 0:
                path.append(prev[path[-1]])
            return [nodes[k] for k in reversed(path)]
        for j in range(1, len(nodes)):
            if j == i or not clear(nodes[i], nodes[j], i == 0):
                continue
            c = cost + math.hypot(nodes[j][0] - nodes[i][0], nodes[j][1] - nodes[i][1])
            if c < best.get(j, math.inf):
                best[j], prev[j] = c, i
                heapq.heappush(heap, (c, j))
    return None


def densify(track: list[list[float]], step: float = 0.05, t0: float | None = None, t1: float | None = None) -> list[list[float]]:
    """台車の軌跡 [[t, x, y, yaw], ...] を、位置が step [m] 以上あかないように補間する（時刻は線形）。

    t0 / t1 を渡すと、その間だけを返す（両端の時刻の位置も入れる）。
    """
    if not track:
        return []

    def at(t: float) -> list[float]:
        for a, b in zip(track, track[1:]):
            if a[0] <= t <= b[0]:
                f = 0.0 if b[0] == a[0] else (t - a[0]) / (b[0] - a[0])
                return [t, a[1] + f * (b[1] - a[1]), a[2] + f * (b[2] - a[2]), a[3] if f < 1.0 else b[3]]
        return [t, *(track[0][1:] if t < track[0][0] else track[-1][1:])]

    lo = track[0][0] if t0 is None else t0
    hi = track[-1][0] if t1 is None else t1
    keys = [at(lo), *[list(k) for k in track if lo < k[0] < hi], at(hi)]
    out = [keys[0]]
    for a, b in zip(keys, keys[1:]):
        n = max(1, math.ceil(math.hypot(b[1] - a[1], b[2] - a[2]) / step))
        for k in range(1, n + 1):
            f = k / n
            out.append([a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]), a[2] + f * (b[2] - a[2]), b[3] if k == n else a[3]])
    return out
