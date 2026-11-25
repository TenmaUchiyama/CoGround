"""検出した物体に VLM（代役）が属性を付け、それでルール照合・Plan ができること。"""

from __future__ import annotations

import pytest

from coground_server.models import Attribute, Rule, SceneSnapshot
from coground_server.state import StateStore
from coground_server.perception.object_store import ObjectMemory
from coground_server.vlm import (DEFAULT_MOCK_FILE, MockVlm, NoAttributes, PerceptionVlm, annotate_scene,
                                 make_attribute_provider)


def _item(oid: str, category: str, x: float, source: str = "detection", attributes=None) -> dict:
    return {"id": oid, "category": category, "position": [x, 0.75, 0.6], "size": [0.05, 0.07, 0.05],
            "attributes": attributes or {}, "observation": {"source": source, "detector_label": category, "confidence": 0.9}}


def _place(oid: str, category: str, x: float) -> dict:
    return {"id": oid, "category": category, "position": [x, 0.72, 0.78], "size": [0.16, 0.03, 0.14],
            "place_zone": {"center": [x, 0.80, 0.78], "size": [0.16, 0.14, 0.14]},
            "observation": {"source": "detection", "detector_label": category}}


def tidy_scene() -> SceneSnapshot:
    """片付けデモ（Unity の TidyDemoSetup）を、認識済みで属性なしの形にしたもの。"""
    return SceneSnapshot.model_validate({"objects": [
        _item("pet_bottle", "plastic_bottle", 0.33),
        _item("can", "can", 0.11),
        _item("tissue", "tissue", 0.0),
        _item("mug", "mug", -0.22),
        _item("plate", "plate", -0.34),
        _place("box_1", "storage_box", 0.25),
        _place("trash_bin", "trash_bin", 0.0),
        _place("box_2", "storage_box", -0.25),
    ]})


TIDY_RULES = [
    Rule(id="trash", text="Trash goes in the trash bin", condition={"attribute": "trash", "equals": True}, target_region="trash_bin"),
    Rule(id="fragile", text="Fragile items go in box_2", condition={"attribute": "fragile", "equals": True}, target_region="box_2"),
    Rule(id="store", text="Everything else in box_1", condition=None, target_region="box_1"),
]


def test_mock_by_category_and_id():
    vlm = MockVlm({"default_confidence": 0.8,
                   "by_category": {"mug": {"fragile": True, "material": "ceramic"}},
                   "by_id": {"mug_2": {"fragile": {"value": False, "confidence": 0.4}}, "_note": {}}})
    scene = SceneSnapshot.model_validate({"objects": [_item("mug_1", "mug", 0), _item("mug_2", "mug", 0.1)]})
    out = {o.id: o for o in annotate_scene(scene, vlm).objects}
    assert out["mug_1"].attributes["fragile"] == Attribute(value=True, source="vlm", confidence=0.8)
    assert out["mug_2"].attributes["fragile"] == Attribute(value=False, source="vlm", confidence=0.4)
    assert out["mug_2"].attributes["material"].value == "ceramic"


def test_only_detection_and_missing_keys():
    vlm = MockVlm({"by_category": {"mug": {"fragile": True, "dirty": True}}})
    scene = SceneSnapshot.model_validate({"objects": [
        _item("sim", "mug", 0, source="simulation"),
        _item("det", "mug", 0.1, attributes={"fragile": {"value": False, "source": "detector", "confidence": 0.7}}),
    ]})
    out = {o.id: o for o in annotate_scene(scene, vlm).objects}
    assert out["sim"].attributes == {}  # 真値の物体には付けない
    assert out["det"].attributes["fragile"].source == "detector"  # 届いた値は上書きしない
    assert out["det"].attributes["dirty"].source == "vlm"


def test_no_change_returns_same_scene():
    scene = tidy_scene()
    assert annotate_scene(scene, NoAttributes()) is scene


def test_tidy_demo_plan_from_mock_vlm():
    state = StateStore()
    state.attributes = MockVlm.from_file(DEFAULT_MOCK_FILE)
    state.set_rules(TIDY_RULES)
    state.set_scene(tidy_scene())
    steps = {s.object_id: (s.to.region_id if s.to else None, s.rule_id, s.status) for s in state.plan.steps}
    assert steps == {
        "pet_bottle": ("box_1", "store", "ok"),
        "can": ("trash_bin", "trash", "ok"),
        "tissue": ("trash_bin", "trash", "ok"),
        "mug": ("box_2", "fragile", "ok"),
        "plate": ("box_2", "fragile", "ok"),
    }


def test_correction_beats_vlm():
    state = StateStore()
    state.attributes = MockVlm.from_file(DEFAULT_MOCK_FILE)
    state.set_rules(TIDY_RULES)
    state.set_scene(tidy_scene())
    state.set_attribute("mug", "fragile", False)
    mug = next(s for s in state.plan.steps if s.object_id == "mug")
    assert (mug.to.region_id, mug.rule_id) == ("box_1", "store")
    # Unity が同じシーンを送り直しても、訂正は残り、VLM の値は付け直される
    state.set_scene(tidy_scene())
    mug = next(s for s in state.plan.steps if s.object_id == "mug")
    assert mug.rule_id == "store"
    assert next(o for o in state.scene.objects if o.id == "plate").attributes["fragile"].source == "vlm"


def _memory(**objects: dict) -> ObjectMemory:
    memory = ObjectMemory()
    for object_id, attributes in objects.items():
        memory.claim([object_id])
        memory.complete(object_id, "mug", attributes)
    return memory


def test_perception_vlm_reads_object_memory():
    """フレームで VLM が答えた属性を、物体 ID で引く。分からない答えと perception の中だけの項目は付けない。"""
    vlm = PerceptionVlm(_memory(obj_001={"material": "ceramic", "fragility": "likely_fragile", "appearance": "white mug",
                                         "fragile": "true", "trash": "false", "dirty": "unknown"},
                                obj_002={"material": "unknown", "fragility": "uncertain", "appearance": "bottle"}))
    scene = SceneSnapshot.model_validate({"objects": [
        _item("obj_001", "mug", 0), _item("obj_002", "plastic_bottle", 0.1), _item("obj_003", "plate", 0.2)]})
    out = {o.id: o for o in annotate_scene(scene, vlm).objects}
    assert {k: (a.value, a.source) for k, a in out["obj_001"].attributes.items()} == {
        "material": ("ceramic", "vlm"), "fragile": (True, "vlm"), "trash": (False, "vlm")}
    assert out["obj_002"].attributes == {}  # 全部「分からない」
    assert out["obj_003"].attributes == {}  # 記憶に無い（まだ VLM が見ていない）


def test_perception_vlm_plan_and_unknown_stays_unknown():
    """VLM の答えでルールに合い、Plan ができる。答えが無い物体に、代わりの値は入らない。"""
    state = StateStore()
    state.attributes = PerceptionVlm(_memory(obj_001={"fragile": "true"}, obj_002={"fragile": "unknown"}))
    state.set_rules([TIDY_RULES[1]])
    scene = tidy_scene().model_dump(mode="json")
    scene["objects"] = [o for o in scene["objects"] if o["id"].startswith("box")] + [
        _item("obj_001", "mug", -0.22), _item("obj_002", "plate", -0.34)]
    scene["regions"] = []
    state.set_scene(SceneSnapshot.model_validate(scene))
    assert [(s.object_id, s.to.region_id) for s in state.plan.steps if s.to is not None] == [("obj_001", "box_2")]
    assert "fragile" not in next(o for o in state.scene.objects if o.id == "obj_002").attributes


def test_services_use_perception_vlm(monkeypatch):
    monkeypatch.setenv("COGROUND_VLM", "perception")
    monkeypatch.delenv("COGROUND_RULE_BANK", raising=False)
    monkeypatch.delenv("COGROUND_OBJECT_MEMORY", raising=False)
    from coground_server.services import Services

    services = Services()
    assert isinstance(services.state.attributes, PerceptionVlm)
    assert services.state.attributes.memory is services.perception.memory


def test_make_provider_from_env(monkeypatch):
    monkeypatch.delenv("COGROUND_VLM", raising=False)
    assert isinstance(make_attribute_provider(), NoAttributes)
    monkeypatch.setenv("COGROUND_VLM", "mock")
    assert isinstance(make_attribute_provider(), MockVlm)
    monkeypatch.setenv("COGROUND_VLM", "perception")  # 記憶を持つ Services が差し替える
    assert isinstance(make_attribute_provider(), NoAttributes)
    monkeypatch.setenv("COGROUND_VLM", "gpt")
    with pytest.raises(ValueError):
        make_attribute_provider()
