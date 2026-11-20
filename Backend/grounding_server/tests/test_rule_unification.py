"""片付けルール（rules.set）と家庭ルール（norms.set）は 1 つの家庭ルールの並びとして持ち、同じ判定で計画する。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from coground_server.main import create_app
from coground_server.models import Rule
from coground_server.norms import NormRule
from coground_server.state import StateStore
from coground_server.vlm import DEFAULT_MOCK_FILE, MockVlm

from test_norms import R1
from test_vlm import TIDY_RULES, tidy_scene
from test_websocket import connect, is_response, recv_until


def tidy_store() -> StateStore:
    state = StateStore()
    state.attributes = MockVlm.from_file(DEFAULT_MOCK_FILE)
    state.set_scene(tidy_scene())
    state.set_rules(TIDY_RULES)
    return state


def plan_of(state: StateStore) -> dict[str, tuple]:
    return {s.object_id: (s.status, s.to.region_id if s.to else None) for s in state.plan.steps}


def test_tidy_rules_are_stored_as_norms():
    state = tidy_store()
    assert [(n.id, n.origin, n.norm, n.destination) for n in state.norms] == [
        ("trash", "tidy", "obligation", "trash_bin"),
        ("fragile", "tidy", "obligation", "box_2"),
        ("store", "tidy", "obligation", "box_1"),
    ]
    assert state.rules == TIDY_RULES  # 片付けルールの形に戻して見られる
    assert state.snapshot()["rules"] == [r.model_dump(mode="json") for r in TIDY_RULES]


def test_prohibition_applies_to_tidy_plan_without_request():
    state = tidy_store()
    state.set_norms([R1])  # 割れ物に触るな
    assert state.task is None
    plan = plan_of(state)
    # 割れ物は「割れ物は box_2」の行き先が分かったうえで、触れないので保留
    assert plan["mug"] == ("deferred", "box_2") and plan["plate"] == ("deferred", "box_2")
    assert plan["can"] == ("ok", "trash_bin") and plan["pet_bottle"] == ("ok", "box_1")
    assert "R1" in (next(s for s in state.plan.steps if s.object_id == "mug").message or "")


def test_set_rules_and_set_norms_replace_only_their_own():
    state = tidy_store()
    state.set_norms([R1])
    state.set_rules([TIDY_RULES[2]])
    assert [n.id for n in state.norms] == ["store", "R1"]
    state.set_norms([])
    assert [n.id for n in state.norms] == ["store"]


def test_tidy_rule_can_be_corrected_like_a_norm():
    state = tidy_store()
    state.update_norm("store", lambda n: n.model_copy(update={"scope": n.scope.model_copy(update={"from_": "18:00"})}))
    assert next(n for n in state.norms if n.id == "store").scope.from_ == "18:00"
    assert [r.id for r in state.rules] == ["trash", "fragile"]  # もう片付けルールの形では書けない（norms には残る）


def test_to_legacy_round_trip():
    for rule in TIDY_RULES:
        assert NormRule.from_legacy(rule).to_legacy() == rule
    assert NormRule.from_legacy(Rule(id="x", text="x", condition=None, target_region="box_1", source="speech")).to_legacy().source == "speech"
    assert R1.to_legacy() is None


def test_id_clash_between_rules_and_norms_over_websocket():
    with TestClient(create_app()) as client, connect(client) as (ws, _w, _s):
        def call(rid: str, method: str, params: dict) -> dict:
            ws.send_json({"type": "request", "id": rid, "method": method, "params": params})
            return recv_until(ws, is_response(rid))[-1]

        r1 = R1.model_dump(mode="json", by_alias=True)
        assert call("1", "norms.set", {"norms": [r1]})["ok"]
        clash = {"id": "R1", "text": "x", "condition": None, "target_region": "box_1"}
        assert call("2", "rules.set", {"rules": [clash]})["error"]["code"] == "invalid_params"
        assert call("3", "rules.set", {"rules": [{**clash, "id": "store"}]})["ok"]
        state = call("4", "state.get", {})["result"]
        assert [(n["id"], n["origin"]) for n in state["norms"]] == [("store", "tidy"), ("R1", "norm")]
        assert [r["id"] for r in state["rules"]] == ["store"]
