"""ロボット単体テストの method（robot.*）を、代役のロボット（FakeRobot）で確かめる。"""

from __future__ import annotations

import json
import math
from pathlib import Path

from fastapi.testclient import TestClient

from coground_server.main import create_app

SCENE = json.loads((Path(__file__).parent / "fixtures" / "tabletop_scene.json").read_text())


def _call(ws, rid: str, method: str, params: dict | None = None) -> tuple[dict, list[dict]]:
    """response と、それまでに届いた stream を返す。"""
    ws.send_json({"type": "request", "id": rid, "method": method, "params": params or {}})
    streams = []
    while True:
        msg = ws.receive_json()
        if msg.get("id") != rid:
            continue
        if msg["type"] == "stream":
            streams.append(msg["data"])
        elif msg["type"] == "response":
            return msg, streams


def _app(monkeypatch):
    monkeypatch.setenv("COGROUND_FAKE_PHASE_DELAY", "0")
    monkeypatch.delenv("COGROUND_ROSBRIDGE_URL", raising=False)
    return create_app()


def test_pick_then_place_back(monkeypatch):
    with TestClient(_app(monkeypatch)) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json(), ws.receive_json()
        assert _call(ws, "1", "scene.update", SCENE)[0]["ok"]

        res, streams = _call(ws, "2", "robot.pick", {"object_id": "mug_1"})
        assert res["ok"], res
        assert res["result"]["state"] == "succeeded" and res["result"]["holding"] == "mug_1"
        assert [s["phase"] for s in streams] == ["opening", "approaching", "descending", "grasping", "lifting"]

        # 持っている間は別の物をつかめない（ロボット側で断る）
        other = _call(ws, "3", "robot.pick", {"object_id": "glass_1"})[0]
        assert other["ok"] and other["result"]["state"] == "failed"

        back, streams = _call(ws, "4", "robot.place_back")
        assert back["ok"] and back["result"]["state"] == "succeeded" and back["result"]["holding"] is None
        assert streams[-1]["phase"] == "retreating"

        none = _call(ws, "5", "robot.place_back")[0]
        assert not none["ok"] and none["error"]["code"] == "invalid_state"


def test_pick_unknown_object(monkeypatch):
    with TestClient(_app(monkeypatch)) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json(), ws.receive_json()
        res = _call(ws, "1", "robot.pick", {"object_id": "nothing"})[0]
        assert not res["ok"] and res["error"]["code"] == "invalid_params"


def test_navigate_converts_unity_to_ros(monkeypatch):
    app = _app(monkeypatch)
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json(), ws.receive_json()
        # Unity (x=1, z=2)、+X を向く (右回り 90°) -> ROS (x=2, y=-1)、yaw=-90°
        res, streams = _call(ws, "1", "robot.navigate", {"x": 1.0, "z": 2.0, "yaw_deg": 90})
        assert res["ok"] and res["result"]["state"] == "succeeded"
        assert streams[0]["phase"] == "navigating"
        x, y, yaw = app.state.services.robot.base
        assert math.isclose(x, 2.0) and math.isclose(y, -1.0) and math.isclose(yaw, -math.pi / 2)


def test_plan_then_pick_replays(monkeypatch):
    with TestClient(_app(monkeypatch)) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json(), ws.receive_json()
        assert _call(ws, "1", "scene.update", SCENE)[0]["ok"]

        planned = _call(ws, "2", "robot.plan", {"skill": "pick", "object_id": "mug_1"})[0]
        assert planned["ok"], planned
        r = planned["result"]
        assert r["status"] == "ok" and r["stop_source"] == {"pick": "stay"}
        phases = [p["phase"] for p in r["timeline"]["phases"]]
        assert phases == ["opening", "approaching", "descending", "grasping", "lifting"]  # 台車は動かない
        assert "joints" not in r["timeline"]
        assert r["timeline"]["attached"][0]["t1"] == r["timeline"]["duration"]  # 持ったまま終わる

        # 別の物体の Pick には使わない
        other = _call(ws, "3", "robot.pick", {"object_id": "glass_1"})[0]["result"]
        assert other["planned"] is False and other["plan_note"] == "the plan is for mug_1"
        assert _call(ws, "4", "robot.place_back")[0]["result"]["state"] == "succeeded"

        picked = _call(ws, "5", "robot.pick", {"object_id": "mug_1"})[0]["result"]
        assert picked["state"] == "succeeded" and picked["planned"] and picked["mode"] == "replay"

        # 使い終わった計画は消える。持っている間は計画できない
        refused = _call(ws, "6", "robot.plan", {"skill": "pick", "object_id": "glass_1"})[0]
        assert not refused["ok"] and refused["error"]["code"] == "invalid_state"


def test_plan_is_dropped_when_object_moved(monkeypatch):
    with TestClient(_app(monkeypatch)) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json(), ws.receive_json()
        assert _call(ws, "1", "scene.update", SCENE)[0]["ok"]
        assert _call(ws, "2", "robot.plan", {"skill": "pick", "object_id": "mug_1"})[0]["result"]["status"] == "ok"
        moved = json.loads(json.dumps(SCENE))
        mug = next(o for o in moved["objects"] if o["id"] == "mug_1")
        mug["position"][0] += 0.05
        assert _call(ws, "3", "scene.update", moved)[0]["ok"]
        picked = _call(ws, "4", "robot.pick", {"object_id": "mug_1"})[0]["result"]
        assert picked["planned"] is False and "moved" in picked["plan_note"]


def test_plan_navigate_then_go(monkeypatch):
    app = _app(monkeypatch)
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json(), ws.receive_json()
        goal = {"x": 1.0, "z": 2.0, "yaw_deg": 90}
        r = _call(ws, "1", "robot.plan", {"skill": "navigate", **goal})[0]["result"]
        assert r["status"] == "ok" and r["stops"]["navigate"][:2] == [2.0, -1.0]
        assert {p["phase"] for p in r["timeline"]["phases"]} == {"navigating"}
        assert app.state.services.robot.base == [0.0, 0.0, 0.0]  # 計画だけでは動かない

        elsewhere = _call(ws, "2", "robot.navigate", {"x": 0.5, "z": 0.5})[0]["result"]
        assert elsewhere["planned"] is False and elsewhere["plan_note"] == "different Goal from the plan"
        r = _call(ws, "3", "robot.plan", {"skill": "navigate", **goal})[0]["result"]
        went = _call(ws, "4", "robot.navigate", goal)[0]["result"]
        assert went["state"] == "succeeded" and went["planned"]


def test_plan_infeasible(monkeypatch):
    with TestClient(_app(monkeypatch)) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json(), ws.receive_json()
        assert _call(ws, "1", "scene.update", SCENE)[0]["ok"]
        assert _call(ws, "2", "motion.inject_infeasible", {"object_ids": ["mug_1"]})[0]["ok"]
        r = _call(ws, "3", "robot.plan", {"skill": "pick", "object_id": "mug_1"})[0]["result"]
        assert r["status"] == "infeasible" and r["reason"]
        picked = _call(ws, "4", "robot.pick", {"object_id": "mug_1"})[0]["result"]
        assert picked["planned"] is False and picked["plan_note"] == "couldn't be planned"


def test_system_reset_clears_holding_and_plan(monkeypatch):
    with TestClient(_app(monkeypatch)) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json(), ws.receive_json()
        assert _call(ws, "1", "scene.update", SCENE)[0]["ok"]

        # 単体テストの計画を作ってから、つかんだまま「まっさら」にする
        assert _call(ws, "2", "robot.plan", {"skill": "pick", "object_id": "glass_1"})[0]["ok"]
        res = _call(ws, "3", "robot.pick", {"object_id": "mug_1", "use_plan": False})[0]
        assert res["ok"] and res["result"]["holding"] == "mug_1"

        reset = _call(ws, "4", "system.reset")[0]
        assert reset["ok"], reset
        assert reset["result"]["ok"] and reset["result"]["robot"]["holding"] is None

        state = _call(ws, "5", "state.get")[0]["result"]
        assert state["execution"]["mode"] == "idle"
        assert state["motion"]["status"] == "none"

        # 単体テストの計画も消えている（つかむときに計画を使わない）
        again = _call(ws, "6", "robot.pick", {"object_id": "glass_1"})[0]
        assert again["ok"] and again["result"]["state"] == "succeeded" and again["result"]["planned"] is False
