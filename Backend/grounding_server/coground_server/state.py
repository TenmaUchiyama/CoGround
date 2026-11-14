"""サーバーが持つ全体状態（シーンと判定結果）。

状態が変わるたびに version を 1 増やし、全体を state.updated で全クライアントに送る。
差分は送らないので、取りこぼしても次の state.updated（または state.get）で最新に戻れる。

座標はすべて Unity のワールド座標（メートル、左手系、Y 上）。物体 ID は Unity が決め、
MoveIt の collision object 名と揃える。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

Vec3 = tuple[float, float, float]
Quat = tuple[float, float, float, float]  # x, y, z, w


class SceneObject(BaseModel):
    id: str = Field(min_length=1, description="Unity が決める物体 ID")
    label: str = Field(description="検出クラス名（cup, mug, table など）")
    position: Vec3 = Field(description="bbox 中心（Unity ワールド座標）")
    rotation: Quat = (0.0, 0.0, 0.0, 1.0)
    size: Vec3 | None = Field(default=None, description="bbox の大きさ（ローカル軸）")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="検出の確信度")
    image_id: str | None = Field(default=None, description="切り出し画像の ID（後で REST で受け取る予定）")
    extra: dict[str, Any] = Field(default_factory=dict, description="試験的な追加情報")


class SceneRegion(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(description="living_center, sink, shelf など")
    polygon: list[Vec3] = Field(min_length=3, description="床面のポリゴン（Unity ワールド座標）")


class SceneSnapshot(BaseModel):
    frame: Literal["unity_world"] = "unity_world"
    objects: list[SceneObject] = Field(default_factory=list)
    regions: list[SceneRegion] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_ids(self) -> SceneSnapshot:
        ids = [o.id for o in self.objects] + [r.id for r in self.regions]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            raise ValueError(f"ID が重複している: {dup}")
        return self


class StateStore:
    def __init__(self) -> None:
        self._version = 0
        self._updated_at: str | None = None
        self._scene = SceneSnapshot()
        # M4（適用判定）の結果 (object, rule, constraint, justification) を入れる予定。今は空。
        self._constraints: list[dict[str, Any]] = []

    @property
    def version(self) -> int:
        return self._version

    @property
    def scene(self) -> SceneSnapshot:
        return self._scene

    def snapshot(self) -> dict[str, Any]:
        return {
            "version": self._version,
            "updated_at": self._updated_at,
            "scene": self._scene.model_dump(mode="json"),
            "constraints": list(self._constraints),
        }

    def set_scene(self, scene: SceneSnapshot) -> int:
        self._scene = scene
        return self._bump()

    def _bump(self) -> int:
        self._version += 1
        self._updated_at = datetime.now(timezone.utc).isoformat()
        return self._version
