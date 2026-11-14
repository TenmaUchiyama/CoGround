from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient

from coground_server.main import create_app

SCENE = json.loads((Path(__file__).parent / "fixtures" / "tabletop_scene.json").read_text())


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


@contextmanager
def connect(client: TestClient):
    """接続して、最初に届く welcome と state.updated を読む。"""
    with client.websocket_connect("/ws") as ws:
        welcome = ws.receive_json()
        assert welcome["type"] == "event" and welcome["event"] == "session.welcome"
        state = ws.receive_json()
        assert state["type"] == "event" and state["event"] == "state.updated"
        yield ws, welcome, state


def recv_until(ws, pred: Callable[[dict[str, Any]], bool], limit: int = 50) -> list[dict[str, Any]]:
    """pred が真になるメッセージまで読み、途中のものも含めて返す。"""
    got = []
    for _ in range(limit):
        msg = ws.receive_json()
        got.append(msg)
        if pred(msg):
            return got
    raise AssertionError(f"条件に合うメッセージが来ない: {got}")


def is_response(rid: str):
    return lambda m: m["type"] == "response" and m["id"] == rid


def test_welcome_and_initial_state(client):
    with connect(client) as (ws, welcome, state):
        assert welcome["data"]["protocol_version"] == 1
        assert "system.ping" in welcome["data"]["methods"]
        assert state["data"]["version"] == 0
        assert state["data"]["scene"]["objects"] == []


def test_ping(client):
    with connect(client) as (ws, _w, _s):
        ws.send_json({"type": "request", "id": "u-1", "method": "system.ping"})
        msg = ws.receive_json()
        assert msg["type"] == "response" and msg["id"] == "u-1" and msg["ok"] is True
        assert msg["result"]["pong"] is True


def test_unknown_method(client):
    with connect(client) as (ws, _w, _s):
        ws.send_json({"type": "request", "id": "u-1", "method": "nope"})
        msg = ws.receive_json()
        assert msg["ok"] is False and msg["error"]["code"] == "unknown_method"
        assert "system.ping" in msg["error"]["details"]["available"]


def test_invalid_params(client):
    with connect(client) as (ws, _w, _s):
        ws.send_json(
            {"type": "request", "id": "u-1", "method": "scene.update",
             "params": {"objects": [{"id": "a", "label": "cup", "position": [0, 0]}]}}
        )
        msg = ws.receive_json()
        assert msg["ok"] is False and msg["error"]["code"] == "invalid_params"


def test_duplicate_object_ids_rejected(client):
    with connect(client) as (ws, _w, _s):
        obj = {"id": "a", "label": "cup", "position": [0, 0, 0]}
        ws.send_json({"type": "request", "id": "u-1", "method": "scene.update",
                      "params": {"objects": [obj, obj]}})
        msg = ws.receive_json()
        assert msg["error"]["code"] == "invalid_params"


def test_rpc_error_from_handler(client):
    with connect(client) as (ws, _w, _s):
        ws.send_json({"type": "request", "id": "u-1", "method": "debug.fail",
                      "params": {"code": "x", "message": "y"}})
        msg = ws.receive_json()
        assert msg["ok"] is False and msg["error"] == {"code": "x", "message": "y"}


def test_bad_json_and_bad_shape(client):
    with connect(client) as (ws, _w, _s):
        ws.send_text("{not json")
        msg = ws.receive_json()
        assert msg["event"] == "session.error" and msg["data"]["code"] == "bad_message"

        ws.send_json({"type": "request", "id": "u-9"})  # method が無い
        msg = ws.receive_json()
        assert msg["type"] == "response" and msg["id"] == "u-9"
        assert msg["error"]["code"] == "bad_message"

        ws.send_json({"type": "whatever"})
        msg = ws.receive_json()
        assert msg["event"] == "session.error"

        # 失敗した後も接続は使える
        ws.send_json({"type": "request", "id": "u-10", "method": "system.ping"})
        assert ws.receive_json()["ok"] is True


def test_scene_update_broadcasts_to_all_clients(client):
    with connect(client) as (a, _w, _s), connect(client) as (b, _w2, _s2):
        a.send_json({"type": "request", "id": "u-1", "method": "scene.update", "params": SCENE})
        msgs = recv_until(a, is_response("u-1"))
        response = msgs[-1]
        assert response["ok"] is True
        assert response["result"] == {"version": 1, "objects": 11, "regions": 4}
        # 送った本人にも state.updated が response より前に届く
        assert any(m["type"] == "event" and m["event"] == "state.updated" for m in msgs[:-1])

        other = b.receive_json()
        assert other["event"] == "state.updated"
        assert other["data"]["version"] == 1
        ids = [o["id"] for o in other["data"]["scene"]["objects"]]
        assert "mug_1" in ids



def test_reconnect_gets_latest_state(client):
    with connect(client) as (a, _w, _s):
        a.send_json({"type": "request", "id": "u-1", "method": "scene.update", "params": SCENE})
        recv_until(a, is_response("u-1"))

    with connect(client) as (b, _, state):
        assert state["data"]["version"] == 1
        assert len(state["data"]["scene"]["objects"]) == 11


def test_stream_then_response(client):
    with connect(client) as (ws, _w, _s):
        ws.send_json({"type": "request", "id": "u-1", "method": "debug.count",
                      "params": {"count": 3, "interval": 0}})
        msgs = recv_until(ws, is_response("u-1"))
        streams = [m for m in msgs if m["type"] == "stream"]
        assert [s["data"]["i"] for s in streams] == [0, 1, 2]
        assert all(s["id"] == "u-1" for s in streams)
        assert msgs[-1]["result"] == {"done": 3}


def test_cancel(client):
    with connect(client) as (ws, _w, _s):
        ws.send_json({"type": "request", "id": "u-1", "method": "debug.count",
                      "params": {"count": 1000, "interval": 0.05}})
        first = ws.receive_json()
        assert first["type"] == "stream"
        ws.send_json({"type": "cancel", "id": "u-1"})
        msgs = recv_until(ws, is_response("u-1"))
        assert msgs[-1]["ok"] is False and msgs[-1]["error"]["code"] == "cancelled"

        # 終わった request への cancel は無視される
        ws.send_json({"type": "cancel", "id": "u-1"})
        ws.send_json({"type": "request", "id": "u-2", "method": "system.ping"})
        assert ws.receive_json()["id"] == "u-2"


def test_requests_run_concurrently(client):
    with connect(client) as (ws, _w, _s):
        ws.send_json({"type": "request", "id": "slow", "method": "debug.count",
                      "params": {"count": 1000, "interval": 0.05}})
        ws.send_json({"type": "request", "id": "fast", "method": "system.ping"})
        msgs = recv_until(ws, is_response("fast"))
        assert not any(m["type"] == "response" and m["id"] == "slow" for m in msgs)

        ws.send_json({"type": "request", "id": "slow", "method": "system.ping"})
        msgs = recv_until(ws, lambda m: m["type"] == "response" and m["id"] == "slow")
        assert msgs[-1]["error"]["code"] == "duplicate_id"
        ws.send_json({"type": "cancel", "id": "slow"})
        msgs = recv_until(ws, lambda m: m["type"] == "response" and m["id"] == "slow")
        assert msgs[-1]["error"]["code"] == "cancelled"


def test_client_event_has_no_reply(client):
    with connect(client) as (ws, _w, _s):
        ws.send_json({"type": "event", "event": "client.log", "data": {"message": "hello"}})
        ws.send_json({"type": "event", "event": "unknown.event", "data": {}})
        ws.send_json({"type": "request", "id": "u-1", "method": "system.ping"})
        assert ws.receive_json()["id"] == "u-1"  # event には何も返ってこない


def test_rest_endpoints(client):
    assert client.get("/health").json()["ok"] is True

    with connect(client) as (ws, _w, _s):
        ws.send_json({"type": "request", "id": "u-1", "method": "scene.update", "params": SCENE})
        recv_until(ws, is_response("u-1"))

        state = client.get("/api/state").json()
        assert state["version"] == 1 and len(state["scene"]["objects"]) == 11
        assert client.get("/health").json()["clients"] == 1

        proto = client.get("/api/protocol").json()
        names = [m["name"] for m in proto["methods"]]
        assert "scene.update" in names and "debug.count" in names
