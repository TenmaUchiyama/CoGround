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
