"""Quest のフレーム（RGB + 深度 + カメラ）の受け取り（perception/frame.py と Perception.analyze_frame）。

Quest の代わりに、机の上に箱を置いたシーンを合成し、Unity（CoGroundFrameSender.cs）が送るのと同じ形にする:
  - 深度: 深度カメラ（OpenGL 式の投影 × ビュー = reprojection 行列）から見た各画素の (NDC 深度, u, v)
  - RGB のカメラ: Unity の座標（y = 上）の位置と回転（Quaternion）、送る画像の画素での fx, fy, cx, cy
  - 検出器の代わり: RGB のカメラに箱を投影したマスクと、物体ごとの特徴量
"""

from __future__ import annotations

import asyncio
import io
import json

import numpy as np
import pytest
from PIL import Image

from coground_server.llm import FakeLlm
from coground_server.perception import ObjectMemory, Perception, PerceptionError, Segmentation
from coground_server.perception import frame as framelib
from coground_server.perception.association import Box3D

RGB_W, RGB_H, RGB_F = 640, 480, 500.0
DEPTH_N = 160  # 深度テクスチャの大きさ（正方形）
DEPTH_TAN = 0.9  # 深度カメラの画角（tan、上下左右とも）
NEAR, FAR = 0.1, 20.0


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def box_on_table(x, z, size=(0.08, 0.10, 0.08)) -> Box3D:
    """Unity のワールド座標（y = 上）。机の面は y = 0。"""
    sx, sy, sz = size
    return Box3D([x - sx / 2, 0.0, z - sz / 2], [x + sx / 2, sy, z + sz / 2])


def trace(origins, directions, boxes):
    """光線（ワールド座標）と、机の面 y = 0・箱との最初の交点。(距離 t, 当たった箱の番号 -1 = 机/なし)"""
    with np.errstate(divide="ignore", invalid="ignore"):
        t_table = -origins[..., 1] / directions[..., 1]
        t = np.where(t_table > 0, t_table, np.inf)
        index = np.full(t.shape, -1)
        for i, box in enumerate(boxes):
            t0 = (box.min - origins) / directions
            t1 = (box.max - origins) / directions
            near, far = np.minimum(t0, t1).max(axis=-1), np.maximum(t0, t1).min(axis=-1)
            hit = (near < far) & (near > 0) & (near < t)
            t = np.where(hit, near, t)
            index = np.where(hit, i, index)
    return t, index


class DepthCamera:
    """Meta の深度カメラの代わり（OpenGL 式: ビュー座標は x = 右、y = 上、カメラは -z を向く）。"""

    def __init__(self, eye, target):
        self.eye = np.asarray(eye, float)
        f = unit(np.asarray(target, float) - self.eye)
        r = unit(np.cross(f, [0, 1, 0]))
        u = np.cross(r, f)
        self.rows = np.stack([r, u, -f])  # ワールド → ビュー の回転
        view = np.eye(4)
        view[:3, :3] = self.rows
        view[:3, 3] = -self.rows @ self.eye
        proj = np.zeros((4, 4))
        proj[0, 0] = proj[1, 1] = 1 / DEPTH_TAN
        proj[2, 2] = -(FAR + NEAR) / (FAR - NEAR)
        proj[2, 3] = -2 * FAR * NEAR / (FAR - NEAR)
        proj[3, 2] = -1
        self.matrix = proj @ view

    def texture(self, boxes) -> bytes:
        """(NDC 深度, u, v, 0) を float32 で。行の並びは Unity の readback と同じく下から。"""
        v, u = np.mgrid[0:DEPTH_N, 0:DEPTH_N]
        uu, vv = (u + 0.5) / DEPTH_N, (v + 0.5) / DEPTH_N
        view_dirs = np.stack([(2 * uu - 1) * DEPTH_TAN, (2 * vv - 1) * DEPTH_TAN, -np.ones_like(uu)], axis=-1)
        dirs = view_dirs @ self.rows  # ビュー → ワールド
        t, _ = trace(np.broadcast_to(self.eye, dirs.shape), dirs, boxes)
        with np.errstate(invalid="ignore"):
            points = self.eye + dirs * t[..., None]
        with np.errstate(invalid="ignore"):
            clip = np.concatenate([points, np.ones(t.shape + (1,))], axis=-1) @ self.matrix.T
        d = np.where(np.isfinite(t), (clip[..., 2] / clip[..., 3] + 1) / 2, 1.0)
        return np.stack([d, uu, vv, np.zeros_like(d)], axis=-1).astype("<f4").tobytes(), points, np.isfinite(t)


def quaternion_from_matrix(m):
    w = np.sqrt(max(0.0, 1 + m[0, 0] + m[1, 1] + m[2, 2])) / 2
    x = np.copysign(np.sqrt(max(0.0, 1 + m[0, 0] - m[1, 1] - m[2, 2])) / 2, m[2, 1] - m[1, 2])
    y = np.copysign(np.sqrt(max(0.0, 1 - m[0, 0] + m[1, 1] - m[2, 2])) / 2, m[0, 2] - m[2, 0])
    z = np.copysign(np.sqrt(max(0.0, 1 - m[0, 0] - m[1, 1] + m[2, 2])) / 2, m[1, 0] - m[0, 1])
    return [float(x), float(y), float(z), float(w)]


class Headset:
    """Quest の代わり。RGB のカメラ（Unity の姿勢）と深度カメラ（少し横）を、同じ場所から同じ所へ向ける。"""

    def __init__(self, eye, target):
        eye = np.asarray(eye, float)
        forward = unit(np.asarray(target, float) - eye)
        right = unit(np.cross([0, 1, 0], forward))  # Unity: right = Cross(up, forward)
        up = np.cross(forward, right)
        self.unity_rotation = np.stack([right, up, forward], axis=1)  # カメラ → ワールド
        self.eye = eye
        self.depth = DepthCamera(eye + right * 0.03 + up * 0.02, target)  # 深度カメラは RGB と少しずれている

    def rgb_rays(self):
        v, u = np.mgrid[0:RGB_H, 0:RGB_W]
        # 画像の行は上から。Unity のカメラ座標は y = 上
        local = np.stack([(u + 0.5 - RGB_W / 2) / RGB_F, -(v + 0.5 - RGB_H / 2) / RGB_F, np.ones((RGB_H, RGB_W))], axis=-1)
        return local @ self.unity_rotation.T

    def meta(self, timestamp: float) -> str:
        return json.dumps({"timestamp": timestamp, "device": "test",
                           "rgb": {"width": RGB_W, "height": RGB_H, "fx": RGB_F, "fy": RGB_F, "cx": RGB_W / 2, "cy": RGB_H / 2,
                                   "pose": {"position": self.eye.tolist(),
                                            "rotation": quaternion_from_matrix(self.unity_rotation)}},
                           "depth": {"width": DEPTH_N, "height": DEPTH_N, "format": "rgba32f_uv",
                                     "reprojection": self.depth.matrix.reshape(-1).tolist()}})


def embedding(seed: int) -> list[float]:
    vector = np.random.default_rng(seed).normal(size=32)
    return (vector / np.linalg.norm(vector)).tolist()


class SceneSegmenter:
    """検出器の代わり: いまの頭の位置から見えた箱のマスクと特徴量を返す。"""

    def __init__(self, objects: dict[str, tuple[Box3D, int, str]]):
        self.objects = objects  # 名前 -> (箱, 見た目の番号, クラス)
        self.headset: Headset | None = None
        self.shown: dict[int, str] = {}

    async def segment(self, data: bytes, embed: bool = False) -> Segmentation:
        names = list(self.objects)
        rays = self.headset.rgb_rays()
        _, index = trace(np.broadcast_to(self.headset.eye, rays.shape), rays, [self.objects[n][0] for n in names])
        found = []
        for i, name in enumerate(names):
            vs, us = np.nonzero(index == i)
            if len(us) < 30:
                continue
            rows = [(v, np.nonzero(index[v] == i)[0]) for v in range(RGB_H)]
            rows = [(v, xs) for v, xs in rows if len(xs)]
            polygon = [[float(xs[0]), float(v)] for v, xs in rows] + [[float(xs[-1]) + 1, float(v)] for v, xs in reversed(rows)]
            found.append((name, {"class": self.objects[name][2], "confidence": 0.9, "mask": polygon,
                                 "bbox": [float(us.min()), float(vs.min()), float(us.max()) + 1, float(vs.max()) + 1],
                                 "embedding": embedding(self.objects[name][1]) if embed else None}))
        found.sort(key=lambda item: item[1]["bbox"][0])
        self.shown = {n: name for n, (name, _) in enumerate(found, start=1)}
        return Segmentation.model_validate({"image": {"width": RGB_W, "height": RGB_H},
                                            "detections": [{"detection_id": n, **d} for n, (_, d) in enumerate(found, start=1)]})


ATTRS = {"category": "cup", "material": "ceramic", "fragility": "likely_fragile", "appearance": "a cup"}


def answer(system, prompt):
    marks = json.loads(prompt.split("\n", 1)[1])
    return {"objects": [{"mark_id": m["mark_id"], **ATTRS} for m in marks]}


def jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (RGB_W, RGB_H), (180, 180, 180)).save(buffer, "JPEG")
    return buffer.getvalue()


FRONT = Headset([0.0, 0.45, -0.60], [0.0, 0.05, 0.0])
LEFT = Headset([-0.30, 0.45, -0.55], [0.0, 0.05, 0.0])
RIGHT = Headset([0.30, 0.45, -0.55], [0.0, 0.05, 0.0])
AWAY = Headset([0.0, 0.45, -0.60], [2.0, 0.05, -0.60])


def three():
    return {"mug": (box_on_table(-0.20, 0.0), 1, "mug"), "cup": (box_on_table(0.0, 0.0), 2, "cup"),
            "glass": (box_on_table(0.20, 0.0, (0.07, 0.13, 0.07)), 3, "cup")}


def make(tmp_path=None, objects=None):
    llm = FakeLlm({"analyze_objects": answer})
    segmenter = SceneSegmenter(objects or three())
    perception = Perception(lambda: llm, segmenter=segmenter, memory=ObjectMemory(),
                            runs_dir=tmp_path / "runs" if tmp_path else None,
                            sequences_dir=tmp_path / "sequences" if tmp_path else None,
                            tracks_path=tmp_path / "tracks.json" if tmp_path else None)
    return perception, segmenter, llm


def look(perception, segmenter, headset: Headset, t: float, shuffle: bool = False):
    segmenter.headset = headset
    depth, _, _ = headset.depth.texture([box for box, _, _ in segmenter.objects.values()])
    if shuffle:  # 行の並びが違っても（Vulkan で上下が逆でも）同じ結果になる
        pixels = np.frombuffer(depth, dtype="<f4").reshape(-1, 4).copy()
        np.random.default_rng(0).shuffle(pixels)
        depth = pixels.tobytes()
    result = asyncio.run(perception.analyze_frame(jpeg(), depth, headset.meta(t)))
    by_name = {segmenter.shown[o.detection_id]: o for o in result.objects}
    return result, by_name


# ---------------------------------------------------------------- 深度 → ワールド座標


def test_depth_pixels_return_to_world_points():
    boxes = [box for box, _, _ in three().values()]
    depth, truth, valid = FRONT.depth.texture(boxes)
    meta = framelib.DepthMeta(width=DEPTH_N, height=DEPTH_N, reprojection=FRONT.depth.matrix.reshape(-1).tolist())
    points = framelib.depth_points(depth, meta)
    near = valid & (np.linalg.norm(truth - FRONT.depth.eye, axis=-1) < 8.0)  # 10 m 先あたりからは「遠すぎる」で捨てる
    close = points[np.linalg.norm(points - FRONT.depth.eye, axis=-1) < 8.0]
    assert len(close) == near.sum()
    assert np.abs(close - truth[near]).max() < 1e-3


def test_unity_pose_becomes_y_down_camera():
    camera = framelib.rgb_camera(framelib.RgbMeta.model_validate(json.loads(FRONT.meta(0))["rgb"]))
    center = box_on_table(0.0, 0.0).center
    u, v, _ = camera.project(center)
    assert abs(u - RGB_W / 2) < 40 and abs(v - RGB_H / 2) < 60  # 見ている先は画像の真ん中あたり
    top = camera.project(center + [0, 0.05, 0])  # ワールドで上の点は、画像では上（v が小さい）
    assert top[1] < v


def test_aligned_depth_matches_the_rgb_view():
    boxes = [box for box, _, _ in three().values()]
    depth, _, _ = FRONT.depth.texture(boxes)
    frame = framelib.decode_frame(depth, FRONT.meta(0))
    aligned, small = framelib.align_depth(frame.points, frame.camera, (RGB_W, RGB_H))
    assert aligned.shape == (240, 320) and (aligned > 0).mean() > 0.8
    rays = FRONT.rgb_rays()[::2, ::2]
    t, _ = trace(np.broadcast_to(FRONT.eye, rays.shape), rays, boxes)  # 光線の長さ = z が 1 の倍数なので t = 奥行き
    both = (aligned > 0) & np.isfinite(t)
    assert np.median(np.abs(aligned[both] - t[both])) < 0.01


def test_frame_validation():
    perception, _, _ = make()
    depth, _, _ = FRONT.depth.texture([])
    with pytest.raises(PerceptionError, match="bytes"):
        asyncio.run(perception.analyze_frame(jpeg(), depth[:-4], FRONT.meta(0)))
    with pytest.raises(PerceptionError, match="Invalid frame"):
        asyncio.run(perception.analyze_frame(jpeg(), depth, "{}"))
    small = io.BytesIO()
    Image.new("RGB", (320, 240)).save(small, "JPEG")
    with pytest.raises(PerceptionError, match="intrinsics"):
        asyncio.run(perception.analyze_frame(small.getvalue(), depth, FRONT.meta(0)))


# ---------------------------------------------------------------- フレームの流れ（Phase 5・6）


def test_viewpoint_changes_keep_ids_and_skip_the_vlm():
    perception, segmenter, llm = make()
    first, objects = look(perception, segmenter, FRONT, 0.0)
    assert {o.track for o in objects.values()} == {"new"} and first.vlm.calls == 1 and first.frame.located == 3
    ids = {name: o.object_id for name, o in objects.items()}
    assert objects["mug"].position is not None and abs(objects["mug"].position[0] + 0.20) < 0.03
    for t, headset in enumerate([AWAY, LEFT, AWAY, RIGHT, FRONT], start=1):
        result, objects = look(perception, segmenter, headset, float(t), shuffle=t % 2 == 0)
        if headset is AWAY:
            assert result.objects == [] and result.frame.displaced == []
            continue
        assert {name: o.object_id for name, o in objects.items()} == ids
        assert {o.track for o in objects.values()} == {"same"} and result.vlm.calls == 0
    assert len(llm.calls) == 1


def test_move_swap_and_remove(tmp_path):
    perception, segmenter, llm = make(tmp_path)
    _, objects = look(perception, segmenter, FRONT, 0.0)
    ids = {name: o.object_id for name, o in objects.items()}

    segmenter.objects["cup"] = (box_on_table(0.05, 0.22), 2, "cup")  # 動かした
    result, objects = look(perception, segmenter, FRONT, 1.0)
    assert objects["cup"].object_id == ids["cup"] and objects["cup"].track == "moved" and result.vlm.calls == 0

    segmenter.objects["glass"] = (box_on_table(0.20, 0.0, (0.07, 0.13, 0.07)), 30, "cup")  # 同じ場所で入れ替えた
    result, objects = look(perception, segmenter, FRONT, 2.0)
    assert objects["glass"].track == "new" and objects["glass"].object_id not in ids.values()
    assert result.vlm.analyzed == [objects["glass"].object_id] and result.frame.displaced == [ids["glass"]]
    assert perception.memory.get(ids["glass"]).presence == "displaced"

    del segmenter.objects["mug"]  # 取り除いた
    result, _ = look(perception, segmenter, FRONT, 3.0)
    assert result.frame.displaced == [ids["mug"]]
    assert len(llm.calls) == 2  # 最初の 3 つと、入れ替えた 1 つ

    # 再起動しても、同じ物体に同じ ID（記憶と追跡の両方をファイルから読む）
    memory_path = tmp_path / "memory.json"
    perception.memory.path = memory_path
    perception.memory.save()
    again, segmenter2, llm2 = make(tmp_path, dict(segmenter.objects))
    again.memory = ObjectMemory(memory_path)
    _, objects = look(again, segmenter2, LEFT, 4.0)
    assert objects["cup"].object_id == ids["cup"] and objects["cup"].track == "same" and llm2.calls == []


def test_record_and_run_files(tmp_path):
    perception, segmenter, _ = make(tmp_path)
    segmenter.headset = FRONT
    depth, _, _ = FRONT.depth.texture([b for b, _, _ in segmenter.objects.values()])
    assert perception.record_frame("table_a", jpeg(), depth, FRONT.meta(0)) == "table_a/0001"
    assert perception.record_frame("table_a", jpeg(), depth, FRONT.meta(1)) == "table_a/0002"
    assert {p.name for p in (tmp_path / "sequences" / "table_a" / "0002").iterdir()} == {"rgb.jpg", "depth.bin", "meta.json"}
    with pytest.raises(PerceptionError):
        perception.record_frame("../x", jpeg(), depth, FRONT.meta(0))
    result, _ = look(perception, segmenter, FRONT, 0.0)
    assert {"depth_overlay.jpg", "meta.json", "som.jpg"} <= set(result.artifacts)
    detections = json.loads((tmp_path / "runs" / result.run_id / "detections.json").read_text(encoding="utf-8"))
    assert "embedding" not in detections["detections"][0]


def test_unlocated_detection_is_reported_but_not_remembered():
    """深度が足りず 3D にできない検出は、ID を付けず、VLM にも回さない。"""
    perception, segmenter, llm = make()
    segmenter.headset = FRONT
    depth, _, _ = FRONT.depth.texture([])  # 机だけの深度（物体の点が無い）
    pixels = np.frombuffer(depth, dtype="<f4").reshape(-1, 4).copy()
    pixels[:, 0] = 0.0  # 深度がまったく無い
    result = asyncio.run(perception.analyze_frame(jpeg(), pixels.tobytes(), FRONT.meta(0)))
    assert {o.source for o in result.objects} == {"unlocated"} and result.frame.located == 0
    assert llm.calls == [] and perception.memory.objects == {}
