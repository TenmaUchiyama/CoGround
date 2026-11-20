"""検出した物体に属性（fragile / trash など）を付ける VLM の口。

検出器（YOLO-World、VR シミュレーションでは Unity の MockSimulatedObjects）が出すのは
カテゴリ・位置・大きさまで。ルール照合に使う属性は、サーバーがここで付ける。

  scene.update ──> StateStore.set_scene ──> annotate_scene（ここ）──> 住人の訂正を重ねる ──> planner

約束事:
- 付けるのは observation.source = "detection" の物体だけ（simulation / manual は真値をそのまま使う）
- 届いた物体がすでに持っている属性は上書きしない（検出器が付けた値や、Unity で決めた値を優先する）
- 住人の訂正（objects.set_attribute）は、ここで付けた値よりさらに優先する（state.py の _with_corrections）
- 付けた値は source = "vlm"

どれを使うか（環境変数 COGROUND_VLM）:
  off（既定）  何も付けない
  mock         JSON に書いた答えを返す（COGROUND_VLM_MOCK_FILE、既定は同梱の vlm_mock_attributes.json）
本物の VLM（切り出し画像 observation.image_id から属性を推定する）は、AttributeProvider を実装して足す。
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Protocol

from .models import Attribute, SceneObject, SceneSnapshot

log = logging.getLogger(__name__)

DEFAULT_MOCK_FILE = Path(__file__).with_name("vlm_mock_attributes.json")
DEFAULT_CONFIDENCE = 0.9


class AttributeProvider(Protocol):
    name: str

    def attributes_for(self, obj: SceneObject) -> dict[str, Attribute]:
        """obj に付ける属性。分からなければ空。"""
        ...


class NoAttributes:
    name = "off"

    def attributes_for(self, obj: SceneObject) -> dict[str, Attribute]:
        return {}


class MockVlm:
    """VLM の代役。物体 ID（by_id）か、カテゴリ（by_category）で引いた固定の答えを返す。

    ファイルの形:
      {"default_confidence": 0.9,
       "by_category": {"mug": {"fragile": true, "trash": false}, ...},
       "by_id":       {"pet_bottle": {"trash": {"value": false, "confidence": 0.6}}, ...}}
    値だけ書けば default_confidence。by_id は by_category より優先する（同じキーなら by_id の値）。
    "_" で始まるキーは注釈として読み飛ばす。
    """

    name = "mock"

    def __init__(self, table: dict[str, Any]) -> None:
        self.default_confidence = float(table.get("default_confidence", DEFAULT_CONFIDENCE))
        self.by_category = self._section(table.get("by_category"))
        self.by_id = self._section(table.get("by_id"))

    @classmethod
    def from_file(cls, path: Path) -> MockVlm:
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def _section(self, section: Any) -> dict[str, dict[str, Attribute]]:
        out: dict[str, dict[str, Attribute]] = {}
        for name, attrs in (section or {}).items():
            if name.startswith("_"):
                continue
            out[name] = {key: self._attribute(raw) for key, raw in attrs.items() if not key.startswith("_")}
        return out

    def _attribute(self, raw: Any) -> Attribute:
        if isinstance(raw, dict):
            return Attribute(value=raw["value"], source="vlm",
                             confidence=float(raw.get("confidence", self.default_confidence)))
        return Attribute(value=raw, source="vlm", confidence=self.default_confidence)

    def attributes_for(self, obj: SceneObject) -> dict[str, Attribute]:
        return {**self.by_category.get(obj.category, {}), **self.by_id.get(obj.id, {})}


def make_attribute_provider() -> AttributeProvider:
    """環境変数から選ぶ（上の「どれを使うか」）。"""
    kind = (os.environ.get("COGROUND_VLM") or "off").strip().lower()
    if kind == "off":
        return NoAttributes()
    if kind == "mock":
        path = Path(os.environ.get("COGROUND_VLM_MOCK_FILE") or DEFAULT_MOCK_FILE)
        provider = MockVlm.from_file(path)
        log.info("VLM: mock (%s, %d categories, %d ids)", path, len(provider.by_category), len(provider.by_id))
        return provider
    raise ValueError(f"COGROUND_VLM must be off or mock: {kind!r}")


def annotate_scene(scene: SceneSnapshot, provider: AttributeProvider) -> SceneSnapshot:
    """検出した物体に、まだ無い属性を付けたシーンを返す（scene は変えない）。"""
    objects = []
    changed = False
    for obj in scene.objects:
        if obj.observation.source != "detection":
            objects.append(obj)
            continue
        added = {k: v for k, v in provider.attributes_for(obj).items() if k not in obj.attributes}
        if not added:
            objects.append(obj)
            continue
        objects.append(obj.model_copy(update={"attributes": {**obj.attributes, **added}}))
        changed = True
    return scene.model_copy(update={"objects": objects}) if changed else scene
