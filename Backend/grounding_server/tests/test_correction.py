"""属性の訂正と、訂正の前後の比較、住人への説明（state.set_attribute、norms/report.py）。

最後の test_minimal_demo が、最初のデモ（皿 1 枚、コップ 1 個、属性の訂正 1 回）の通し。
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from coground_server.eventlog import EventLog
from coground_server.executor import Executor
from coground_server.main import create_app
from coground_server.norms.report import build_report
from coground_server.robot import FakeRobot

from test_task import NORMS, TEXT, call, request, scene, scene_json, step, store
from test_websocket import connect


def changes(correction) -> list[tuple[str, str, object, object]]:
    return [(c.object_id, c.what, c.before, c.after) for c in correction.changes]


def test_correction_changes_only_what_depends_on_the_attribute():
    state = store()
    task = request(state)
    state.set_scene(scene(cup_at="shelf_lower"))  # コップは収納済み
    cup_before = task.row("cup_B").model_dump()

    c = state.set_attribute("plate_A", "fragile", False)

    assert (c.id, c.object_id, c.key, c.before, c.after) == ("correction_1", "plate_A", "fragile", True, False)
    assert c.affected_rule_ids == ["R1"]  # fragile を読むルールだけ
    assert changes(c) == [
        ("plate_A", "exec_state", "deferred", "pending"),
        ("plate_A", "verdict:R1", "violated (predicted)", "not_applicable (predicted)"),
        ("plate_A", "verdict:R3a", None, "compliant (predicted)"),  # 運べるようになったので、置き先の予測が付く
    ]
    plate = task.row("plate_A")
    assert (plate.destination, plate.exec_state) == ("shelf_upper", "pending")  # 上段の指定はそのまま
    assert step(state, "plate_A").status == "ok"
    assert task.row("cup_B").model_dump() == cup_before  # コップの完了記録は変わらない
    assert task.corrections == [c]
    fragile = next(o for o in state.scene.objects if o.id == "plate_A").attributes["fragile"]
    assert (fragile.value, fragile.source) == (False, "user")


def test_correction_survives_scene_update_and_can_be_withdrawn():
    state = store()
    task = request(state)
    state.set_attribute("plate_A", "fragile", False)

    state.set_scene(scene())  # Unity は「割れ物」のままのシーンを送り直してくる
    assert task.row("plate_A").exec_state == "pending"
    assert state.snapshot()["corrections"] == [{"object_id": "plate_A", "key": "fragile", "value": False}]

    c = state.set_attribute("plate_A", "fragile", None)  # 訂正を取り消すと、届いた値（割れ物）に戻る
    assert (c.before, c.after) == (False, None)
    assert task.row("plate_A").exec_state == "deferred"
    assert state.snapshot()["corrections"] == []
    assert [v.value for v in task.row("plate_A").history if v.rule_id == "R1"] == ["violated", "not_applicable", "violated"]


def test_correction_resolves_unknown_fragility():
    state = store(plate_fragile=None)
    task = request(state)
    assert task.row("plate_A").verdicts["R1"].value == "undetermined"
    c = state.set_attribute("plate_A", "fragile", True)  # 住人が「割れ物」と答えた
    assert c.before is None
    assert ("plate_A", "verdict:R1", "undetermined (predicted)", "violated (predicted)") in changes(c)
    assert task.row("plate_A").exec_state == "deferred" and task.row("plate_A").missing == []


def test_unrelated_correction_changes_nothing():
    state = store()
    task = request(state)
    before = task.model_dump(exclude={"corrections"})
    c = state.set_attribute("cup_B", "dirty", True)
    assert c.affected_rule_ids == [] and c.changes == []
    assert task.model_dump(exclude={"corrections"}) == before


def test_correction_without_task_and_errors():
    state = store()
    c = state.set_attribute("plate_A", "fragile", False)  # 依頼の前の訂正も効く
    assert c.changes == []
    assert request(state).row("plate_A").exec_state == "pending"
    with pytest.raises(ValueError):
        state.set_attribute("nope", "fragile", False)
    with pytest.raises(ValueError):
        state.set_attribute("plate_A", "category", "cup")


def test_report_explains_each_object():
    state = store()
    task = request(state)
    state.set_scene(scene(cup_at="shelf_lower"))
    report = build_report(task, state.all_norms())

    assert report["counts"] == {"total": 2, "done": 1, "deferred": 1}
    assert report["summary"] == "Stored 1 of 2 items."
    plate, cup = report["rows"]
    assert plate["sentence"] == ("Left plate (plate_A) without moving it, following the agreement \"Don't touch fragile things\"."
                                 " The specified storage location is shelf_upper.")
    assert plate["reasons"] == [{"rule_id": "R1", "original_text": "Don't touch fragile things", "value": "violated",
                                 "basis": "predicted", "label": "violated (predicted)"}]
    assert cup["sentence"] == "Stored cup (cup_B) in shelf_lower."
    assert cup["reasons"][0]["label"] == "compliant (observed)"
    assert report["message"] == " ".join([report["summary"], plate["sentence"], cup["sentence"]])


def test_report_names_missing_facts():
    state = store(plate_fragile=None)
    report = build_report(request(state), state.all_norms())
    assert "information needed to decide (attribute fragile of plate_A) is missing" in report["rows"][0]["sentence"]
    assert report["rows"][0]["missing"] == [{"entity_id": "plate_A", "key": "attr:fragile"}]


# ---------------------------------------------------------------- 最初のデモ（通し）


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


def test_minimal_demo_over_websocket(client):
    """皿 1 枚、コップ 1 個、属性の訂正 1 回。WebSocket から、代役のロボットで通す。"""
    services = client.app.state.services
    services.robot.phase_delay = 0.0

    def wait_idle(ws) -> dict:
        for _ in range(400):
            state = call(ws, "poll", "state.get")["result"]
            if state["execution"]["mode"] != "running":
                return state
        raise AssertionError("Execution doesn't finish")

    with connect(client) as (ws, _w, _s):
        call(ws, "1", "scene.update", scene_json())
        call(ws, "2", "norms.set", {"norms": [n.model_dump(mode="json", by_alias=True) for n in NORMS]})

        # 1. 依頼: 皿は「上段指定・R1 違反の予測・保留」、コップは「下段へ計画」
        counts = call(ws, "3", "task.request", {"text": TEXT})["result"]["counts"]
        assert counts == {"total": 2, "done": 0, "deferred": 1, "pending": 1}

        # 2. 実行: コップだけ運ぶ。下段を観測して「2 点中 1 点」
        assert call(ws, "4", "exec.start", {"allow_unplanned": True})["ok"]
        state = wait_idle(ws)
        assert state["execution"]["reason"] == "finished"
        report = call(ws, "5", "task.report")["result"]
        assert report["summary"] == "Stored 1 of 2 items."
        assert "without moving it" in report["rows"][0]["sentence"]
        assert report["rows"][1]["sentence"] == "Stored cup (cup_B) in shelf_lower."
        cup_row = state["task"]["rows"][1]

        # 3. 訂正:「この皿は割れ物ではない」。変わるのは皿だけ
        res = call(ws, "6", "objects.set_attribute", {"object_id": "plate_A", "key": "fragile", "value": False})["result"]
        assert {c["object_id"] for c in res["correction"]["changes"]} == {"plate_A"}
        assert res["correction"]["affected_rule_ids"] == ["R1"]
        assert res["counts"] == {"total": 2, "done": 1, "pending": 1}
        state = call(ws, "7", "state.get")["result"]
        assert state["task"]["rows"][1] == cup_row  # コップの完了記録は維持
        assert state["task"]["rows"][0]["destination"] == "shelf_upper"  # 上段の指定も維持
        assert [(s["object_id"], s["status"]) for s in state["plan"]["steps"]] == [("plate_A", "ok")]

        # 4. もう一度実行すると、皿も上段へ。「2 点中 2 点」
        assert call(ws, "8", "exec.start", {"allow_unplanned": True})["ok"]
        wait_idle(ws)
        report = call(ws, "9", "task.report")["result"]
        assert report["summary"] == "Stored 2 of 2 items."
        assert len(report["corrections"]) == 1
        assert call(ws, "10", "objects.set_attribute", {"object_id": "x", "key": "fragile", "value": 1})["error"]["code"] == "invalid_params"


def test_executor_uses_corrected_attribute():
    # 訂正のあとに実行すると、皿も運ぶ（サーバーの中だけで確かめる）
    async def main() -> None:
        state = store()
        task = request(state)
        state.set_attribute("plate_A", "fragile", False)

        async def publish() -> None:
            pass

        ex = Executor(state, FakeRobot(phase_delay=0.0), EventLog(), publish)
        await ex.start(allow_unplanned=True)
        for _ in range(3000):
            if ex.mode != "running":
                break
            await asyncio.sleep(0.002)
        assert (ex.mode, task.counts()) == ("idle", {"total": 2, "done": 2})
        await ex.close()

    asyncio.run(main())
