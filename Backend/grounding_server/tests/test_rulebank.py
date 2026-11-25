"""ルールバンクをファイルに残す（rulebank.py）。"""

import json

from coground_server.models import Rule, SceneRegion
from coground_server.norms.model import NormRule
from coground_server.rulebank import RuleBank
from coground_server.state import StateStore

FRAGILE = {"id": "N1", "original_text": "Don't touch fragile objects", "norm": "prohibition",
           "target": {"kind": "object", "where": {"attribute": "fragile", "equals": True}},
           "requirement": {"window": "whole", "predicate": "contact"}}


def make(path):
    state = StateStore()
    bank = RuleBank(path)
    bank.load(state)
    state.rule_bank = bank
    return state


def test_saves_and_restores(tmp_path):
    path = tmp_path / "rule_bank.json"
    state = make(path)
    assert not path.exists()
    state.set_norms([NormRule.model_validate(FRAGILE)])
    state.set_rules([Rule.model_validate({"id": "trash", "text": "Trash goes in the bin",
                                          "condition": {"attribute": "trash", "equals": True},
                                          "target_region": "trash_bin"})])
    state.define_zone(SceneRegion.model_validate({"id": "zone_play", "label": "play area",
                                                  "polygon": [[0, 0, 0], [1, 0, 0], [1, 0, 1]]}))
    assert path.exists()

    again = make(path)
    assert [n.id for n in again.norms] == [n.id for n in state.norms]
    assert again.norms[0].origin == "tidy"
    assert "zone_play" in again.zones
    assert again.norms == state.norms


def test_scene_changes_do_not_rewrite(tmp_path):
    path = tmp_path / "rule_bank.json"
    state = make(path)
    state.set_norms([NormRule.model_validate(FRAGILE)])
    mtime = path.stat().st_mtime_ns
    state.touch()
    assert path.stat().st_mtime_ns == mtime


def test_broken_file_is_moved_aside(tmp_path):
    path = tmp_path / "rule_bank.json"
    path.write_text("{not json")
    state = make(path)
    assert state.norms == []
    assert (tmp_path / "rule_bank.json.broken").exists()
    state.set_norms([NormRule.model_validate(FRAGILE)])
    assert json.loads(path.read_text())["norms"][0]["id"] == "N1"


OWNER = {"id": "N2", "original_text": "Don't touch papa's things", "norm": "prohibition",
         "target": {"kind": "object", "where": {"attribute": "owner", "equals": "papa"}},
         "requirement": {"window": "whole", "predicate": "contact"},
         "attributes": [{"name": "owner", "how_to_tell": "Who it belongs to", "values": ["papa"], "visual": False}]}


def test_registered_attributes_survive_restart_but_visible_ones_do_not(tmp_path):
    """画像から判断できない属性（持ち主）の訂正は残す。画像から判断できる属性（割れ物）の訂正は残さない。"""
    from test_task import scene

    path = tmp_path / "rule_bank.json"
    state = make(path)
    state.set_norms([NormRule.model_validate(FRAGILE), NormRule.model_validate(OWNER)])
    state.set_scene(scene())
    state.set_attribute("cup_B", "owner", "papa")
    state.set_attribute("cup_B", "fragile", False)
    category = next(o for o in state.scene.objects if o.id == "cup_B").category
    assert json.loads(path.read_text(encoding="utf-8"))["attributes"] == [
        {"object_id": "cup_B", "key": "owner", "value": "papa", "category": category}]

    again = make(path)
    again.set_scene(scene())
    cup = next(o for o in again.scene.objects if o.id == "cup_B")
    assert cup.value("owner") == "papa" and cup.attributes["owner"].source == "user"
    assert "fragile" not in again.corrections.get("cup_B", {})

    again.set_attribute("cup_B", "owner", None)  # 取り消したら、ファイルからも消える
    assert json.loads(path.read_text(encoding="utf-8"))["attributes"] == []


def test_restored_attribute_is_not_applied_to_a_different_kind_of_object(tmp_path):
    """再起動のあと、同じ ID が別の種類の物体に付いていたら、残した属性は重ねない。"""
    from test_task import scene

    path = tmp_path / "rule_bank.json"
    state = make(path)
    state.set_norms([NormRule.model_validate(OWNER)])
    state.set_scene(scene())
    state.set_attribute("cup_B", "owner", "papa")

    again = make(path)
    moved = scene()
    moved = moved.model_copy(update={"objects": [
        o.model_copy(update={"category": "book"}) if o.id == "cup_B" else o for o in moved.objects]})
    again.set_scene(moved)
    assert next(o for o in again.scene.objects if o.id == "cup_B").value("owner") is None
