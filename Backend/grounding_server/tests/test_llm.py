from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from coground_server.llm import FakeLlm, LlmError
from coground_server.llm.compile_rule import build_prompt, compile_rules
from coground_server.main import create_app
from coground_server.models import SceneSnapshot

TABLETOP = json.loads((Path(__file__).parent / "fixtures" / "tabletop_scene.json").read_text())

ANSWER = {
    "rules": [
        {"text": "Dishes go in the sink", "attribute": "group", "equals": "dish", "target_region": "sink_1"},
        {"text": "Throw burnable trash in the burnables bin", "attribute": "waste_type", "equals": "burnable",
         "target_region": "trash_bin_burnable"},
        {"text": "Put forks away in the drawer", "attribute": "category", "equals": "fork", "target_region": "drawer_1"},
    ],
    "unresolved": ["\"Do the rest however\" can't be decided as a tidying instruction"],
}


def tabletop() -> SceneSnapshot:
    return SceneSnapshot.model_validate(TABLETOP)


def test_compile_rules_assigns_ids_and_drops_unknown_regions():
    llm = FakeLlm({"compile_rule": ANSWER})
    rules, unresolved = asyncio.run(compile_rules(llm, "Dishes go in the sink…", tabletop(), existing_ids={"rule_1"}))
    assert [r.id for r in rules] == ["rule_2", "rule_3"]
    assert all(r.source == "speech" for r in rules)
    assert rules[0].condition.attribute == "group" and rules[0].condition.equals == "dish"
    assert len(unresolved) == 2 and "drawer_1" in unresolved[1]


def test_prompt_shows_regions_items_and_vocabulary():
    prompt = build_prompt("Fragile items go to the sink", tabletop())
    assert '"id": "sink_1"' in prompt and '"waste_type": "burnable"' in prompt  # 領域と、持ち主の属性
    assert '"id": "mug_1"' in prompt and '"id": "table_1", "category": "table", "group"' not in prompt  # 物体は item だけ
    assert "fragile" in prompt and prompt.endswith("# Instruction\nFragile items go to the sink")


def test_fake_llm_validates_and_reports_missing():
    from coground_server.llm.compile_rule import CompiledRules

    with pytest.raises(LlmError):
        asyncio.run(FakeLlm().generate(name="compile_rule", system="", prompt="", output=CompiledRules))


def call(ws, rid, method, params=None):
    ws.send_json({"type": "request", "id": rid, "method": method, "params": params or {}})
    msgs = []
    while not msgs or msgs[-1]["type"] != "response":
        msgs.append(ws.receive_json())
    return msgs


@pytest.fixture
def app_ws():
    app = create_app()
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json(), ws.receive_json()  # welcome, state.updated
        yield app, ws


def test_rules_compile_over_websocket(app_ws):
    app, ws = app_ws
    app.state.services.llm = llm = FakeLlm({"compile_rule": ANSWER})
    call(ws, "u-1", "scene.update", TABLETOP)

    msgs = call(ws, "u-2", "rules.compile", {"text": "Dishes in the sink, burnables in the burnables bin"})
    assert msgs[0] == {"type": "stream", "id": "u-2", "data": {"stage": "llm"}}
    result = msgs[-1]["result"]
    assert msgs[-1]["ok"] is True and result["applied"] is True
    assert [r["id"] for r in result["rules"]] == ["rule_1", "rule_2"]
    assert result["version"] == 2 and result["steps"] == 5 and len(result["unresolved"]) == 2
    state = next(m for m in msgs if m["type"] == "event" and m["event"] == "state.updated")["data"]
    assert len(state["rules"]) == 2 and len(state["plan"]["steps"]) == 5
    assert "Dishes in the sink" in llm.calls[0]["prompt"]

    # apply = false なら状態は変えない
    msgs = call(ws, "u-3", "rules.compile", {"text": "Once more", "apply": False})
    assert msgs[-1]["result"]["applied"] is False and [r["id"] for r in msgs[-1]["result"]["rules"]] == ["rule_3", "rule_4"]
    assert not any(m["type"] == "event" for m in msgs)

    # replace なら、いまのルールを捨てて番号も 1 から
    msgs = call(ws, "u-4", "rules.compile", {"text": "Start over", "mode": "replace"})
    assert [r["id"] for r in msgs[-1]["result"]["rules"]] == ["rule_1", "rule_2"]


def test_llm_failure_is_an_error_response(app_ws):
    app, ws = app_ws
    app.state.services.llm = FakeLlm({"ping": LlmError("unreachable")})
    response = call(ws, "u-1", "llm.ping")[-1]
    assert response["ok"] is False and response["error"]["code"] == "llm_failed"

    app.state.services.llm = FakeLlm({"ping": {"reply": "pong"}})
    assert call(ws, "u-2", "llm.ping")[-1]["result"] == {"reply": "pong"}
