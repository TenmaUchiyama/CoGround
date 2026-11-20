"""同じ物体を見つけ直す（再認識）と、動いた・入れ替わった・無くなったの判定。

方式は次の論文に従う（コードは CoGround で書き起こしたもの。論文の実装は使っていない）:

  Yue Fan, Xiaojian Ma, Rongpeng Su, Jun Guo, Rujie Wu, Xi Chen, Qing Li.
  "Embodied VideoAgent: Persistent Memory from Egocentric Videos and Embodied Sensors Enables
  Dynamic Scene Understanding." ICCV 2025.

論文の方式（1 フレームごと）:
  1. 検出した物体を、マスクと深度とカメラの姿勢から 3D の箱（ワールド座標の AABB）にする          → lift_polygon
  2. 覚えている物体のうち、あるはずの場所が空いているもの（深度が箱の中を素通りする）を「動いた候補」にする → _find_vacated
  3. その場にある物体とは、3D の箱の重なり（IoU / 小さい方に対する重なり）で照合する                    → _match_in_place
  4. 残った検出は、「動いた候補」と見た目（特徴量）と箱の大きさで照合する。合えば、同じ物体が動いた      → _match_moved
  5. どれにも合わない検出は新しい物体
  6. 重なった箱は 1 つにまとめる（同じ物体を 2 つ覚えないように）                                      → _merge_duplicates

CoGround で足したこと:
  - その場の照合でも見た目を確かめる（swap_similarity）。同じ場所でも見た目が大きく違えば「入れ替わった」として、
    古い物体は動いた候補に回し、検出は新しい物体にする。論文の方式は場所とカテゴリだけなので、陶器のマグを
    同じ場所でプラスチックのコップに替えても同じ ID のままになる。CoGround では割れ物かどうかが変わるので区別する
  - 結果を出来事（new / same / moved）として返す。呼ぶ側は new のときだけ VLM に聞けばよい
  - 動いた候補のまま missing_after 秒たった物体は「無くなった」（missing）にする。見えないだけの物体（視界の外、
    手前に何かある）は present のまま

座標系: カメラ座標は x = 右、y = 下、z = 奥（画像と同じ向き。OpenCV と同じ）。Camera.rotation はカメラ座標 →
ワールド座標の回転、Camera.position はワールド座標でのカメラの位置。Unity（y = 上、左手系）の姿勢は、呼ぶ側で直す。

しきい値（AssociationConfig）は最初の値。実際の深度（Quest）で確かめて決め直す。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import Any, Callable, Literal, Sequence

import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import linear_sum_assignment

ObjectState = Literal["present", "displaced", "missing"]
"""present: その場にある（見えていなくてもよい） / displaced: あった場所が空いている（動いた候補） / missing: 無くなった"""

EventKind = Literal["new", "same", "moved"]


@dataclass
class AssociationConfig:
    overlap: float = 0.2  # その場の照合: 箱の重なり（IoU、または同じカテゴリなら小さい方に対する重なり）がこれを超えたら候補
    moved_similarity: float = 0.5  # 動いた物体の照合: 見た目の類似度（コサイン）がこれ以上
    moved_size: float = 0.6  # 動いた物体の照合: 箱の体積の比（小さい方 / 大きい方）がこれ以上
    swap_similarity: float = 0.3  # その場の照合: 見た目の類似度がこれ未満なら、入れ替わったとみなす
    blend: float = 0.2  # 同じ物体を見直したとき、新しい観測を混ぜる割合（箱と特徴量）
    vacated_margin: float = 0.015  # 視線の深度が、箱の中の点よりこれ（m）以上奥まで届いたら、その視線は物体を素通りした
    vacated_fraction: float = 0.6  # 素通りした視線がこの割合以上なら、その場所は空いている
    missing_after: float = 30.0  # 動いた候補のままこの秒数たったら、無くなったとする
    trim: float = 0.1  # 3D の箱を作るとき、手前と奥の点をこの割合ずつ捨てる（マスクのはみ出し）
    min_points: int = 20  # 箱を作るのに要る点の数

    @classmethod
    def from_env(cls) -> AssociationConfig:
        """COGROUND_REID_<名前の大文字>（例 COGROUND_REID_SWAP_SIMILARITY=0.4）で、しきい値を変える。"""
        config = cls()
        for f in fields(cls):
            raw = os.environ.get(f"COGROUND_REID_{f.name.upper()}")
            if raw:
                setattr(config, f.name, type(getattr(config, f.name))(raw))
        return config


@dataclass
class Camera:
    """ピンホールカメラ。fx, fy, cx, cy は深度画像の画素での値。"""

    fx: float
    fy: float
    cx: float
    cy: float
    position: np.ndarray  # (3,) ワールド座標
    rotation: np.ndarray  # (3, 3) カメラ座標 → ワールド座標

    def __post_init__(self) -> None:
        self.position = np.asarray(self.position, dtype=float).reshape(3)
        self.rotation = np.asarray(self.rotation, dtype=float).reshape(3, 3)

    def to_world(self, points: np.ndarray) -> np.ndarray:
        return points @ self.rotation.T + self.position

    def to_camera(self, points: np.ndarray) -> np.ndarray:
        return (points - self.position) @ self.rotation

    def project(self, point: np.ndarray) -> tuple[float, float, float] | None:
        """ワールド座標の点 → (u, v, 奥行き)。カメラの後ろなら None。"""
        x, y, z = self.to_camera(np.asarray(point, dtype=float).reshape(1, 3))[0]
        if z <= 1e-6:
            return None
        return self.fx * x / z + self.cx, self.fy * y / z + self.cy, z

    def unproject(self, u: np.ndarray, v: np.ndarray, depth: np.ndarray) -> np.ndarray:
        """画素 (u, v) と奥行き → ワールド座標の点 (N, 3)。"""
        x = (u - self.cx) / self.fx * depth
        y = (v - self.cy) / self.fy * depth
        return self.to_world(np.stack([x, y, depth], axis=-1))


@dataclass
class Box3D:
    """ワールド座標の、軸に沿った箱。"""

    min: np.ndarray
    max: np.ndarray

    def __post_init__(self) -> None:
        self.min = np.asarray(self.min, dtype=float).reshape(3)
        self.max = np.asarray(self.max, dtype=float).reshape(3)

    @property
    def center(self) -> np.ndarray:
        return (self.min + self.max) / 2

    @property
    def volume(self) -> float:
        return float(np.prod(np.clip(self.max - self.min, 0, None)))

    def intersection(self, other: Box3D) -> float:
        return float(np.prod(np.clip(np.minimum(self.max, other.max) - np.maximum(self.min, other.min), 0, None)))

    def iou(self, other: Box3D) -> float:
        inter = self.intersection(other)
        return inter / (self.volume + other.volume - inter + 1e-12)

    def overlap_of_smaller(self, other: Box3D) -> float:
        """重なり / 小さい方の体積。片方がもう片方の一部（一部しか見えなかった）のときに大きくなる。"""
        return self.intersection(other) / (min(self.volume, other.volume) + 1e-12)

    def size_ratio(self, other: Box3D) -> float:
        return min(self.volume, other.volume) / (max(self.volume, other.volume) + 1e-12)

    def contains(self, point: np.ndarray) -> bool:
        return bool(np.all(point >= self.min) and np.all(point <= self.max))

    def blended(self, other: Box3D, ratio: float) -> Box3D:
        return Box3D((1 - ratio) * self.min + ratio * other.min, (1 - ratio) * self.max + ratio * other.max)

    def union(self, other: Box3D) -> Box3D:
        return Box3D(np.minimum(self.min, other.min), np.maximum(self.max, other.max))


@dataclass
class Observation:
    """1 フレームで検出した物体 1 つ（3D にしたもの）。"""

    detection_id: int
    category: str
    box: Box3D
    embedding: np.ndarray | None = None  # 見た目の特徴量（切り出した画像を DINOv2 などに通したもの）。無ければ None


@dataclass
class TrackedObject:
    """覚えている物体 1 つ。"""

    object_id: str
    category: str
    box: Box3D
    embedding: np.ndarray | None = None
    state: ObjectState = "present"
    first_seen: float = 0.0
    last_seen: float = 0.0
    displaced_at: float | None = None  # 動いた候補になった時刻
    sightings: int = 1


@dataclass
class Event:
    """検出 1 つが、どの物体だったか。"""

    detection_id: int
    object_id: str
    kind: EventKind  # new: 初めて見た（VLM に聞く） / same: その場にあった / moved: 別の場所に動いていた


@dataclass
class FrameResult:
    events: list[Event] = field(default_factory=list)
    displaced: list[str] = field(default_factory=list)  # このフレームで「あった場所が空いている」と分かった物体
    missing: list[str] = field(default_factory=list)  # このフレームで「無くなった」になった物体
    merged: dict[str, str] = field(default_factory=dict)  # まとめて消した object_id -> 残した object_id


def similarity(a: np.ndarray | None, b: np.ndarray | None) -> float | None:
    """特徴量のコサイン類似度。どちらかが無ければ None（判断しない）。"""
    if a is None or b is None:
        return None
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


# ---------------------------------------------------------------- 2D → 3D


def lift_polygon(polygon: Sequence[Sequence[float]], image_size: tuple[int, int], depth: np.ndarray, camera: Camera,
                 config: AssociationConfig | None = None) -> Box3D | None:
    """マスクの輪郭（RGB 画像の画素）と深度から、物体の 3D の箱を作る。点が足りなければ None。

    image_size は RGB 画像の (幅, 高さ)。深度画像は RGB と同じ視野で、大きさだけ違ってよい（輪郭を縮めて当てる）。
    depth は奥行き（m。カメラの z）。0 以下・NaN・無限大の画素は使わない。
    """
    config = config or AssociationConfig()
    h, w = depth.shape
    sx, sy = w / image_size[0], h / image_size[1]
    if len(polygon) < 3:
        return None
    mask_image = Image.new("1", (w, h), 0)
    ImageDraw.Draw(mask_image).polygon([(x * sx, y * sy) for x, y in polygon], fill=1)
    mask = np.asarray(mask_image, dtype=bool) & np.isfinite(depth) & (depth > 0)
    v, u = np.nonzero(mask)
    if len(u) < config.min_points:
        return None
    z = depth[v, u].astype(float)
    # マスクのはみ出し（手前の物、背景）を落とす: 奥行きの手前と奥を trim ずつ捨てる
    low, high = np.quantile(z, [config.trim, 1 - config.trim])
    keep = (z >= low) & (z <= high)
    if keep.sum() < config.min_points:
        return None
    points = camera.unproject(u[keep] + 0.5, v[keep] + 0.5, z[keep])
    return Box3D(points.min(axis=0), points.max(axis=0))


# ---------------------------------------------------------------- 照合


def _assign(weights: np.ndarray) -> list[tuple[int, int]]:
    """重みの合計が最大になる 1 対 1 の組（重み 0 以下は組まない）。"""
    if weights.size == 0:
        return []
    rows, cols = linear_sum_assignment(weights, maximize=True)
    return [(int(r), int(c)) for r, c in zip(rows, cols) if weights[r, c] > 0]


class ObjectTracker:
    """物体の 3D の箱と見た目を覚えて、フレームごとに照合する。

      result = tracker.update(observations, timestamp, depth=depth, camera=camera)
      for event in result.events: ...   # new のときだけ VLM に聞く

    depth と camera を渡さないと、「あった場所が空いている」の判定（2）はしない（動いた物体は新しい物体になる）。
    """

    def __init__(self, config: AssociationConfig | None = None, prefix: str = "obj",
                 reserved: Callable[[str], bool] | None = None) -> None:
        self.config = config or AssociationConfig()
        self.prefix = prefix
        self.objects: dict[str, TrackedObject] = {}
        self._next = 1
        # すでに使われている ID（物体の記憶にある ID など）。新しい物体には付けない
        self.reserved = reserved or (lambda object_id: False)

    def _new_id(self) -> str:
        while True:
            object_id = f"{self.prefix}_{self._next:03d}"
            self._next += 1
            if object_id not in self.objects and not self.reserved(object_id):
                return object_id

    def forget(self, object_id: str) -> bool:
        return self.objects.pop(object_id, None) is not None

    def reset(self) -> None:
        self.objects.clear()

    def to_dict(self) -> dict[str, Any]:
        """ファイルに書ける形（再起動しても、同じ物体に同じ ID を付け直せるように）。"""
        return {"next": self._next, "objects": [{
            "object_id": o.object_id, "category": o.category, "min": o.box.min.tolist(), "max": o.box.max.tolist(),
            "embedding": None if o.embedding is None else o.embedding.tolist(), "state": o.state,
            "first_seen": o.first_seen, "last_seen": o.last_seen, "displaced_at": o.displaced_at, "sightings": o.sightings,
        } for o in self.objects.values()]}

    def load_dict(self, data: dict[str, Any]) -> None:
        self._next = int(data.get("next", 1))
        self.objects = {}
        for raw in data.get("objects", []):
            embedding = raw.get("embedding")
            self.objects[raw["object_id"]] = TrackedObject(
                object_id=raw["object_id"], category=raw["category"], box=Box3D(raw["min"], raw["max"]),
                embedding=None if embedding is None else np.asarray(embedding, dtype=float), state=raw["state"],
                first_seen=raw["first_seen"], last_seen=raw["last_seen"], displaced_at=raw.get("displaced_at"),
                sightings=raw.get("sightings", 1))

    def in_state(self, state: ObjectState) -> list[TrackedObject]:
        return [o for o in self.objects.values() if o.state == state]

    def update(self, observations: Sequence[Observation], timestamp: float, *, depth: np.ndarray | None = None,
               camera: Camera | None = None) -> FrameResult:
        result = FrameResult()
        if depth is not None and camera is not None:
            for obj in self._find_vacated(depth, camera):
                self._displace(obj, timestamp, result)

        remaining = list(observations)
        seen: list[str] = []
        remaining = self._match_in_place(remaining, timestamp, result, seen)
        remaining = self._match_moved(remaining, timestamp, result, seen)
        for obs in remaining:
            obj = TrackedObject(object_id=self._new_id(), category=obs.category, box=obs.box, embedding=obs.embedding,
                                first_seen=timestamp, last_seen=timestamp)
            self.objects[obj.object_id] = obj
            seen.append(obj.object_id)
            result.events.append(Event(obs.detection_id, obj.object_id, "new"))
        self._merge_duplicates(seen, result)

        for obj in self.in_state("displaced"):
            if obj.displaced_at is not None and timestamp - obj.displaced_at >= self.config.missing_after:
                obj.state = "missing"
                result.missing.append(obj.object_id)
        result.events.sort(key=lambda e: e.detection_id)
        return result

    def _displace(self, obj: TrackedObject, timestamp: float, result: FrameResult) -> None:
        obj.state = "displaced"
        obj.displaced_at = timestamp
        result.displaced.append(obj.object_id)

    def _find_vacated(self, depth: np.ndarray, camera: Camera) -> list[TrackedObject]:
        """あるはずの場所が空いている物体。

        箱の中の点（中心と、中心から 8 つの角へ半分のところ）に向かう視線の深度を見る。物体があれば、深度はその点より
        手前（物体の表面）で止まる。点より vacated_margin 以上奥まで届く視線が vacated_fraction 以上なら、空いている。
        視界の外・深度が無い視線は数えない。数えられる視線が半分に満たなければ、判断しない（present のまま）。
        手前に何かある（深度がずっと近い）ときも、空いているとはしない。"""
        h, w = depth.shape
        vacated = []
        for obj in self.in_state("present"):
            center, half = obj.box.center, (obj.box.max - obj.box.min) / 2
            samples = [center] + [center + half * np.array([sx, sy, sz]) / 2
                                  for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
            through = counted = 0
            for point in samples:
                projected = camera.project(point)
                if projected is None:
                    continue
                u, v, expected = projected
                if not (0 <= u < w and 0 <= v < h):
                    continue
                measured = float(depth[int(v), int(u)])
                if not np.isfinite(measured) or measured <= 0:
                    continue
                counted += 1
                through += measured > expected + self.config.vacated_margin
            if counted * 2 >= len(samples) and through >= self.config.vacated_fraction * counted:
                vacated.append(obj)
        return vacated

    def _match_in_place(self, observations: list[Observation], timestamp: float, result: FrameResult,
                        seen: list[str]) -> list[Observation]:
        """その場にある物体との照合（箱の重なり）。合わなかった検出を返す。"""
        present = self.in_state("present")
        weights = np.zeros((len(observations), len(present)))
        for i, obs in enumerate(observations):
            for j, obj in enumerate(present):
                iou = obs.box.iou(obj.box)
                smaller = obs.box.overlap_of_smaller(obj.box) if obs.category == obj.category else 0.0
                if iou > self.config.overlap or smaller > self.config.overlap:
                    weights[i, j] = max(0.0, iou - self.config.overlap) + max(0.0, smaller - self.config.overlap) + 1e-6
        matched: set[int] = set()
        for i, j in _assign(weights):
            obs, obj = observations[i], present[j]
            alike = similarity(obs.embedding, obj.embedding)
            if alike is not None and alike < self.config.swap_similarity:
                # 同じ場所だが別の物（入れ替わった）。古い物体は動いた候補へ。検出は残して、次の照合か新しい物体へ
                self._displace(obj, timestamp, result)
                continue
            self._refresh(obj, obs, timestamp, self.config.blend)
            seen.append(obj.object_id)
            matched.add(i)
            result.events.append(Event(obs.detection_id, obj.object_id, "same"))
        return [obs for i, obs in enumerate(observations) if i not in matched]

    def _match_moved(self, observations: list[Observation], timestamp: float, result: FrameResult,
                     seen: list[str]) -> list[Observation]:
        """動いた候補（と、無くなった物体）との照合（見た目と箱の大きさ）。合わなかった検出を返す。"""
        # 無くなった物体も含める（戻ってきたら同じ ID に戻す。属性を聞き直さずに済む）
        candidates = self.in_state("displaced") + self.in_state("missing")
        weights = np.zeros((len(observations), len(candidates)))
        for i, obs in enumerate(observations):
            for j, obj in enumerate(candidates):
                alike = similarity(obs.embedding, obj.embedding)
                size = obs.box.size_ratio(obj.box)
                if alike is not None and alike >= self.config.moved_similarity and size >= self.config.moved_size:
                    weights[i, j] = alike + size
        matched: set[int] = set()
        for i, j in _assign(weights):
            obs, obj = observations[i], candidates[j]
            self._refresh(obj, obs, timestamp, 1.0)  # 場所は新しい観測で置き換える
            obj.state = "present"
            obj.displaced_at = None
            if obj.object_id in result.displaced:
                result.displaced.remove(obj.object_id)
            seen.append(obj.object_id)
            matched.add(i)
            result.events.append(Event(obs.detection_id, obj.object_id, "moved"))
        return [obs for i, obs in enumerate(observations) if i not in matched]

    def _refresh(self, obj: TrackedObject, obs: Observation, timestamp: float, ratio: float) -> None:
        obj.box = obj.box.blended(obs.box, ratio)
        obj.category = obs.category
        if obs.embedding is not None:
            obj.embedding = obs.embedding if obj.embedding is None else (1 - self.config.blend) * obj.embedding + self.config.blend * obs.embedding
        obj.last_seen = timestamp
        obj.sightings += 1

    def _merge_duplicates(self, seen: list[str], result: FrameResult) -> None:
        """このフレームで見た物体と重なる、その場の物体をまとめる（古い ID を残す）。"""
        for object_id in seen:
            obj = self.objects.get(object_id)
            if obj is None:
                continue
            for other in self.in_state("present"):
                if other.object_id == object_id or other.object_id not in self.objects or object_id not in self.objects:
                    continue
                iou = obj.box.iou(other.box)
                smaller = obj.box.overlap_of_smaller(other.box) if obj.category == other.category else 0.0
                if iou <= self.config.overlap and smaller <= self.config.overlap:
                    continue
                alike = similarity(obj.embedding, other.embedding)
                if alike is not None and alike < self.config.swap_similarity:
                    continue  # 重なっているが別の物
                keep, drop = (obj, other) if obj.first_seen <= other.first_seen else (other, obj)
                keep.box = keep.box.union(drop.box)
                keep.last_seen = max(keep.last_seen, drop.last_seen)
                del self.objects[drop.object_id]
                result.merged[drop.object_id] = keep.object_id
                for event in result.events:
                    if event.object_id == drop.object_id:
                        event.object_id = keep.object_id
                        if drop.object_id == object_id and event.kind == "new":
                            event.kind = "same"
                if drop.object_id == object_id:
                    break
