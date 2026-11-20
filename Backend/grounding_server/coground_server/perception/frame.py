"""Quest から届いた 1 フレーム（RGB・深度・カメラ）を、association.py が使う形にする。

Quest（Unity、CoGroundFrameSender.cs）が送るもの（POST /perception/frame、multipart）:
  rgb    パススルーカメラの画像（JPEG）
  depth  環境深度（EnvironmentDepthManager の _EnvironmentDepthTexture、左目）を、画素ごとに float32 × 4 で
         (NDC の深度 0..1, 読んだ位置 u, 読んだ位置 v, 0)。行の順番は問わない（どの uv から読んだかが画素ごとにある）
  meta   JSON（FrameMeta）。RGB カメラの内部パラメータ（送った画像の画素）と撮影時の姿勢、深度の行列

深度の画素をワールド座標の点に戻すには、Meta の occlusion シェーダーと同じ約束を逆にたどる:
  clip = M @ (ワールド座標, 1)、 uv = (clip.xy / clip.w + 1) / 2、 深度テクスチャの値 = (clip.z / clip.w + 1) / 2
  M = _EnvironmentDepthReprojectionMatrices[0]（深度カメラの投影 × ビュー。トラッキング空間の補正込み）
なので ワールド = M⁻¹ @ (2u-1, 2v-1, 2d-1, 1) を w で割ったもの。

その点群を RGB カメラに投影して、RGB と同じ向き・同じ視野の深度画像（m）を作る（align_depth）。
深度カメラと RGB カメラは位置も撮影時刻も違うが、どちらもワールド座標に戻すので、頭が動いていてもずれない
（物体が動いているとずれる）。

座標: ワールドは Unity のワールド座標のまま（y = 上）。association.Camera のカメラ座標は x = 右、y = 下、z = 奥なので、
Unity のカメラの回転（x = 右、y = 上、z = 奥）の y を反転して渡す。
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, Field, field_validator

from .association import Camera

# 位置を合わせた深度画像の横幅（画素）。環境深度は数百画素四方しかないので、RGB と同じ大きさにしても穴が増えるだけ
ALIGNED_WIDTH = 320


class Pose(BaseModel):
    position: list[float] = Field(min_length=3, max_length=3)
    rotation: list[float] = Field(min_length=4, max_length=4, description="Unity の Quaternion (x, y, z, w)")


class RgbMeta(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fx: float = Field(gt=0)
    fy: float = Field(gt=0)
    cx: float
    cy: float
    pose: Pose


class DepthMeta(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    format: str = Field(default="rgba32f_uv", description="いまは rgba32f_uv だけ")
    reprojection: list[float] = Field(min_length=16, max_length=16, description="ワールド → 深度カメラのクリップ座標。行ごと（m00, m01, ...）")

    @field_validator("format")
    @classmethod
    def _known(cls, value: str) -> str:
        if value != "rgba32f_uv":
            raise ValueError("depth.format must be rgba32f_uv")
        return value


class FrameMeta(BaseModel):
    timestamp: float = Field(description="撮影時刻（秒。RGB の Timestamp）")
    rgb: RgbMeta
    depth: DepthMeta
    device: str | None = None


@dataclass
class Frame:
    meta: FrameMeta
    camera: Camera  # RGB カメラ（送られた画像の画素で）
    points: np.ndarray  # 深度から戻したワールド座標の点 (N, 3)


def quaternion_matrix(x: float, y: float, z: float, w: float) -> np.ndarray:
    n = np.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def rgb_camera(meta: RgbMeta) -> Camera:
    """Unity のカメラ姿勢 → association.Camera（カメラ座標の y を下向きに）。"""
    rotation = quaternion_matrix(*meta.pose.rotation) @ np.diag([1.0, -1.0, 1.0])
    return Camera(meta.fx, meta.fy, meta.cx, meta.cy, np.asarray(meta.pose.position), rotation)


def depth_points(data: bytes, meta: DepthMeta) -> np.ndarray:
    """深度の画素 → ワールド座標の点 (N, 3)。深度が無い画素（0、または 1 = 遠すぎる）は捨てる。"""
    expected = meta.width * meta.height * 4 * 4
    if len(data) != expected:
        raise ValueError(f"depth has {len(data)} bytes, expected {expected} ({meta.width}x{meta.height} rgba32f)")
    pixels = np.frombuffer(data, dtype="<f4").reshape(-1, 4)
    d, u, v = pixels[:, 0].astype(float), pixels[:, 1].astype(float), pixels[:, 2].astype(float)
    valid = np.isfinite(d) & (d > 0) & (d < 0.9999) & np.isfinite(u) & np.isfinite(v)
    ndc = np.stack([2 * u[valid] - 1, 2 * v[valid] - 1, 2 * d[valid] - 1, np.ones(valid.sum())], axis=1)
    world = ndc @ np.linalg.inv(np.asarray(meta.reprojection, dtype=float).reshape(4, 4)).T
    world = world[:, :3] / world[:, 3:4]
    return world[np.all(np.isfinite(world), axis=1)]


def decode_frame(depth: bytes, meta_json: str | bytes) -> Frame:
    meta = FrameMeta.model_validate(json.loads(meta_json))
    return Frame(meta=meta, camera=rgb_camera(meta.rgb), points=depth_points(depth, meta.depth))


def align_depth(points: np.ndarray, camera: Camera, image_size: tuple[int, int],
                width: int = ALIGNED_WIDTH) -> tuple[np.ndarray, Camera]:
    """点群を RGB カメラに投影して、RGB と同じ視野の深度画像（m、無い画素は 0）と、その画素でのカメラを返す。

    同じ画素に複数の点が落ちたら近い方。点の間の 1 画素の穴は、まわり 3×3 のいちばん近い値で埋める。"""
    scale = width / image_size[0]
    height = max(1, round(image_size[1] * scale))
    small = Camera(camera.fx * scale, camera.fy * scale, camera.cx * scale, camera.cy * scale,
                   camera.position, camera.rotation)
    local = small.to_camera(points)
    z = local[:, 2]
    front = z > 1e-3
    u = np.floor(small.fx * local[front, 0] / z[front] + small.cx).astype(int)
    v = np.floor(small.fy * local[front, 1] / z[front] + small.cy).astype(int)
    z = z[front]
    inside = (u >= 0) & (u < width) & (v >= 0) & (v < height)
    depth = np.full(height * width, np.inf)
    np.minimum.at(depth, v[inside] * width + u[inside], z[inside])
    depth = depth.reshape(height, width)
    # 穴埋め（1 回だけ）
    padded = np.pad(depth, 1, constant_values=np.inf)
    neighbors = np.min([padded[dy:dy + height, dx:dx + width] for dy in range(3) for dx in range(3)], axis=0)
    depth = np.where(np.isfinite(depth), depth, neighbors)
    return np.where(np.isfinite(depth), depth, 0.0), small


def depth_overlay(image, depth: np.ndarray, near: float = 0.2, far: float = 2.0):
    """確認用: RGB に、位置を合わせた深度を色（近い = 赤、遠い = 青）で重ねる。深度が無い画素はそのまま。"""
    from PIL import Image

    t = np.clip((depth - near) / (far - near), 0, 1)
    color = np.stack([255 * (1 - t), 80 * np.ones_like(t), 255 * t], axis=-1).astype(np.uint8)
    alpha = np.where(depth > 0, 120, 0).astype(np.uint8)
    layer = Image.fromarray(np.dstack([color, alpha]), "RGBA").resize(image.size, Image.NEAREST)
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")
