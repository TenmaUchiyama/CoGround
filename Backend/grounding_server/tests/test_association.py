"""再認識（perception/association.py）。合成した机のシーン（箱を置いた平面の深度）で確かめる。

確かめること（ロードマップの Phase 5・6）:
- 視点を変えても、視界から外して戻しても、同じ ID のまま（new は最初だけ）
- 物体が動いたら、同じ ID のまま場所だけ変わる
- 物体を足したら、その物体だけ new
- 同じ場所で入れ替えたら、新しい物体だけ new（古い ID と区別する）
- 取り除いたら displaced → missing。見えないだけ（視界の外、手前に何かある）なら present のまま
"""

from __future__ import annotations

import numpy as np
import pytest

from coground_server.perception.association import (
    AssociationConfig, Box3D, Camera, Observation, ObjectTracker, lift_polygon, similarity)

W, H, F = 320, 240, 280.0  # 深度画像の大きさと焦点距離（画素）
TABLE_Y = 0.0  # ワールド座標は y = 下（カメラ座標と同じ向き）。机の面は y = 0、物体はその上（y < 0）


def look_at(position, target) -> Camera:
    """position から target を見るカメラ（x = 右、y = 下、z = 奥）。"""
    position, target = np.asarray(position, float), np.asarray(target, float)
    z = target - position
    z /= np.linalg.norm(z)
    x = np.cross(np.array([0.0, 1.0, 0.0]), z)  # 下 × 奥 = 右
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return Camera(F, F, W / 2, H / 2, position, np.stack([x, y, z], axis=1))


def box_at(x, z, size=(0.08, 0.10, 0.08)) -> Box3D:
    """机の上の (x, z) に置いた箱（幅, 高さ, 奥行き）。"""
    sx, sy, sz = size
    return Box3D([x - sx / 2, TABLE_Y - sy, z - sz / 2], [x + sx / 2, TABLE_Y, z + sz / 2])


def render(camera: Camera, boxes: list[Box3D]) -> tuple[np.ndarray, np.ndarray]:
    """机の平面と箱を見たときの（深度, どの箱が写っているか -1 = 箱なし）。視線ごとに交点を求める。"""
    v, u = np.mgrid[0:H, 0:W]
    rays = np.stack([(u + 0.5 - camera.cx) / camera.fx, (v + 0.5 - camera.cy) / camera.fy, np.ones((H, W))], axis=-1)
    world = rays @ camera.rotation.T  # 奥行き 1 あたりの進み（t がそのまま奥行き）
    origin = camera.position
    with np.errstate(divide="ignore", invalid="ignore"):
        t_table = (TABLE_Y - origin[1]) / world[..., 1]
        depth = np.where(t_table > 0, t_table, np.inf)
        index = np.full((H, W), -1)
        for i, box in enumerate(boxes):
            t0 = (box.min - origin) / world
            t1 = (box.max - origin) / world
            near, far = np.minimum(t0, t1).max(axis=-1), np.maximum(t0, t1).min(axis=-1)
            hit = (near < far) & (near > 0) & (near < depth)
            depth = np.where(hit, near, depth)
            index = np.where(hit, i, index)
    return np.where(np.isfinite(depth), depth, 0.0), index


def outline(index: np.ndarray, i: int) -> list[list[float]] | None:
    """箱 i が写っている画素を囲む多角形（凸包の代わりに、行ごとの左端と右端をつなぐ）。"""
    rows = [(v, np.nonzero(index[v] == i)[0]) for v in range(H)]
    rows = [(v, us) for v, us in rows if len(us)]
    if len(rows) < 3:
        return None
    left = [[float(us[0]), float(v)] for v, us in rows]
    right = [[float(us[-1]) + 1, float(v)] for v, us in reversed(rows)]
    return left + right


def emb(seed: int) -> np.ndarray:
    """見た目の特徴量の代わり。seed が違えば、ほぼ直交する（似ていない）。"""
    vector = np.random.default_rng(seed).normal(size=64)
    return vector / np.linalg.norm(vector)


class Scene:
    """机の上の物体（名前 -> 箱と見た目）と、それを撮ったときの観測を作る。"""

    def __init__(self, **objects: tuple[Box3D, int]):
        self.objects = dict(objects)

    def frame(self, camera: Camera):
        names = list(self.objects)
        depth, index = render(camera, [self.objects[n][0] for n in names])
        observations, shown = [], {}
        for i, name in enumerate(names):
            polygon = outline(index, i)
            box = lift_polygon(polygon, (W, H), depth, camera) if polygon else None
            if box is not None:
                observations.append(Observation(len(observations) + 1, "cup", box, emb(self.objects[name][1])))
                shown[len(observations)] = name
        return observations, depth, shown


FRONT = look_at([0.0, -0.45, -0.60], [0.0, -0.05, 0.0])
LEFT = look_at([-0.30, -0.45, -0.55], [0.0, -0.05, 0.0])
RIGHT = look_at([0.30, -0.45, -0.55], [0.0, -0.05, 0.0])
AWAY = look_at([0.0, -0.45, -0.60], [2.0, -0.05, -0.60])  # 右を向いて、机が視界から外れる


def three() -> Scene:
    return Scene(mug=(box_at(-0.20, 0.0), 1), cup=(box_at(0.0, 0.0), 2), glass=(box_at(0.20, 0.0, (0.07, 0.13, 0.07)), 3))


def step(tracker: ObjectTracker, scene: Scene, camera: Camera, t: float):
    observations, depth, shown = scene.frame(camera)
    result = tracker.update(observations, t, depth=depth, camera=camera)
    ids = {shown[e.detection_id]: e.object_id for e in result.events}
    kinds = {shown[e.detection_id]: e.kind for e in result.events}
    return result, ids, kinds


# ---------------------------------------------------------------- 幾何


def test_lift_polygon_recovers_the_visible_box():
    scene = three()
    observations, _, shown = scene.frame(FRONT)
    assert sorted(shown.values()) == ["cup", "glass", "mug"]
    for obs in observations:
        truth = scene.objects[shown[obs.detection_id]][0]
        assert np.linalg.norm(obs.box.center - truth.center) < 0.03  # 見えている面だけなので、少しずれる
        assert obs.box.iou(truth) > 0.3


def test_lift_polygon_needs_enough_valid_depth():
    depth = np.zeros((H, W))
    square = [[10, 10], [60, 10], [60, 60], [10, 60]]
    assert lift_polygon(square, (W, H), depth, FRONT) is None  # 深度が無い
    assert lift_polygon(square[:2], (W, H), depth + 1.0, FRONT) is None  # 多角形になっていない
    half = lift_polygon([[20, 20], [120, 20], [120, 120], [20, 120]], (W * 2, H * 2), depth + 1.0, FRONT)
    full = lift_polygon([[10, 10], [60, 10], [60, 60], [10, 60]], (W, H), depth + 1.0, FRONT)
    assert np.allclose(half.min, full.min) and np.allclose(half.max, full.max)  # RGB が深度の 2 倍の大きさでも同じ


def test_box_measures():
    a, b = Box3D([0, 0, 0], [2, 2, 2]), Box3D([1, 0, 0], [3, 2, 2])
    assert a.iou(b) == pytest.approx(4 / 12) and a.size_ratio(b) == pytest.approx(1.0)
    small = Box3D([0, 0, 0], [1, 1, 1])
    assert a.overlap_of_smaller(small) == pytest.approx(1.0) and a.iou(small) == pytest.approx(1 / 8)
    assert similarity(None, emb(1)) is None and similarity(emb(1), emb(1)) == pytest.approx(1.0)
    assert abs(similarity(emb(1), emb(2))) < 0.3


# ---------------------------------------------------------------- Phase 5: 再認識


def test_ids_survive_viewpoint_changes_and_looking_away():
    """3 つの物体を登録し、視界から外して戻すのを 5 回。ID は入れ替わらず、new は最初だけ。"""
    tracker, scene = ObjectTracker(), three()
    _, first, kinds = step(tracker, scene, FRONT, 0.0)
    assert set(kinds.values()) == {"new"} and len(set(first.values())) == 3
    t = 1.0
    for camera in [LEFT, RIGHT, FRONT] * 5:
        away, _, _ = step(tracker, scene, AWAY, t)
        assert away.events == [] and away.displaced == []  # 見えないだけ。動いたとはしない
        _, ids, kinds = step(tracker, scene, camera, t + 0.5)
        assert ids == first and set(kinds.values()) == {"same"}
        t += 1.0
    assert len(tracker.objects) == 3 and all(o.state == "present" for o in tracker.objects.values())


def test_occluded_object_stays_present():
    """手前に物が置かれて見えなくなっても、無くなったとはしない。"""
    tracker, scene = ObjectTracker(), three()
    _, first, _ = step(tracker, scene, FRONT, 0.0)
    scene.objects["wall"] = (box_at(0.0, -0.15, (0.30, 0.30, 0.02)), 9)  # cup の手前のついたて
    result, ids, _ = step(tracker, scene, FRONT, 1.0)
    assert result.displaced == [] and tracker.objects[first["cup"]].state == "present"
    assert ids["mug"] == first["mug"] and ids["glass"] == first["glass"]


# ---------------------------------------------------------------- Phase 6: 変化


def test_moved_object_keeps_its_id():
    tracker, scene = ObjectTracker(), three()
    _, first, _ = step(tracker, scene, FRONT, 0.0)
    scene.objects["cup"] = (box_at(0.05, 0.22), 2)  # cup を奥へ動かした
    result, ids, kinds = step(tracker, scene, FRONT, 1.0)
    assert ids == first
    assert kinds == {"mug": "same", "cup": "moved", "glass": "same"}
    assert result.displaced == [] and len(tracker.objects) == 3
    assert np.linalg.norm(tracker.objects[first["cup"]].box.center[[0, 2]] - [0.05, 0.22]) < 0.04  # 場所が更新された


def test_added_object_is_the_only_new_one():
    tracker, scene = ObjectTracker(), three()
    _, first, _ = step(tracker, scene, FRONT, 0.0)
    scene.objects["bottle"] = (box_at(0.08, 0.22, (0.06, 0.15, 0.06)), 4)
    _, ids, kinds = step(tracker, scene, FRONT, 1.0)
    assert kinds == {"mug": "same", "cup": "same", "glass": "same", "bottle": "new"}
    assert {k: v for k, v in ids.items() if k != "bottle"} == first and ids["bottle"] not in first.values()


def test_swap_in_place_gives_a_new_id_only_to_the_new_object():
    """3 つ目を、同じ場所で別の物体に入れ替える。新しい物体だけ new（VLM に聞くのはこれだけ）。"""
    tracker, scene = ObjectTracker(), three()
    _, first, _ = step(tracker, scene, FRONT, 0.0)
    scene.objects["glass"] = (box_at(0.20, 0.0, (0.07, 0.13, 0.07)), 30)  # 同じ場所・同じ大きさ・違う見た目
    result, ids, kinds = step(tracker, scene, FRONT, 1.0)
    assert kinds == {"mug": "same", "cup": "same", "glass": "new"}
    assert ids["glass"] != first["glass"] and result.displaced == [first["glass"]]
    assert tracker.objects[first["glass"]].state == "displaced"
    # 元の物体を別の場所に戻したら、元の ID に戻る
    scene.objects["old_glass"] = (box_at(0.0, 0.22, (0.07, 0.13, 0.07)), 3)
    _, ids, kinds = step(tracker, scene, FRONT, 2.0)
    assert ids["old_glass"] == first["glass"] and kinds["old_glass"] == "moved"


def test_without_embeddings_a_swap_is_not_noticed():
    """見た目の特徴量が無いと、同じ場所の入れ替えは区別できない（論文の方式のまま）。"""
    tracker = ObjectTracker()
    box = box_at(0.0, 0.0)
    first = tracker.update([Observation(1, "cup", box)], 0.0).events[0]
    again = tracker.update([Observation(1, "cup", box)], 1.0).events[0]
    assert (first.kind, again.kind) == ("new", "same") and first.object_id == again.object_id


def test_removed_object_becomes_missing_and_returns_with_its_id():
    tracker, scene = ObjectTracker(AssociationConfig(missing_after=10.0)), three()
    _, first, _ = step(tracker, scene, FRONT, 0.0)
    cup = scene.objects.pop("cup")
    result, ids, _ = step(tracker, scene, FRONT, 1.0)
    assert result.displaced == [first["cup"]] and result.missing == []
    assert tracker.objects[first["cup"]].state == "displaced" and "cup" not in ids
    result, _, _ = step(tracker, scene, FRONT, 5.0)
    assert result.missing == [] and result.displaced == []  # 同じことを何度も知らせない
    result, _, _ = step(tracker, scene, FRONT, 11.5)
    assert result.missing == [first["cup"]] and tracker.objects[first["cup"]].state == "missing"
    scene.objects["cup"] = (box_at(-0.05, 0.20), cup[1])  # 戻ってきた（別の場所に）
    _, ids, kinds = step(tracker, scene, FRONT, 20.0)
    assert ids["cup"] == first["cup"] and kinds["cup"] == "moved"
    assert tracker.objects[first["cup"]].state == "present"


def test_duplicate_detections_of_one_object_do_not_create_two_objects():
    tracker = ObjectTracker()
    box = box_at(0.0, 0.0)
    shifted = Box3D(box.min + 0.005, box.max + 0.005)
    result = tracker.update([Observation(1, "cup", box, emb(1)), Observation(2, "mug", shifted, emb(1))], 0.0)
    assert len(tracker.objects) == 1 and len(result.merged) == 1
    assert {e.object_id for e in result.events} == set(tracker.objects)


def test_two_similar_objects_side_by_side_keep_their_own_ids():
    """同じ見た目の物体が隣り合っていても、場所で区別する。"""
    tracker = ObjectTracker()
    scene = Scene(a=(box_at(-0.06, 0.0), 1), b=(box_at(0.06, 0.0), 1))
    _, first, _ = step(tracker, scene, FRONT, 0.0)
    for t, camera in enumerate([LEFT, RIGHT, FRONT], start=1):
        _, ids, kinds = step(tracker, scene, camera, float(t))
        assert ids == first and set(kinds.values()) == {"same"}
