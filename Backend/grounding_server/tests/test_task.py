"""依頼から Plan を作る（norms/planner.py、handlers/task.py）。

場面は設計ガイドの最小デモ: 机に割れ物の皿 A と樹脂のコップ B。取り決めは R1（割れ物に触るな）と R3a・R3b（皿は上段、コップは下段）。
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from coground_server.eventlog import EventLog
from coground_server.executor import Executor
from coground_server.main import create_app
from coground_server.models import Rule, SceneSnapshot
from coground_server.norms import NormRule
from coground_server.robot import FakeRobot
from coground_server.state import StateStore

from test_norms import R1, R3A, R3B, exception_for
from test_websocket import connect, is_response, recv_until

NORMS = [R1, R3A, R3B]
TEXT = "Clear everything off the desk"


def scene_json(*, plate_fragile: bool | None = True, cup_at: str = "table_01", extra: list[dict] | None = None) -> dict:
    def furniture(oid: str, category: str, y: float) -> dict:
        return {"id": oid, "category": category, "position": [0, y, 0], "size": [1, 0.1, 1],
                "place_zone": {"center": [0, y + 0.2, 0], "size": [1, 0.3, 1]}}

    height = {"table_01": 0.9, "shelf_lower": 1.9, "shelf_upper": 2.9}
    plate = {"id": "plate_A", "category": "plate", "position": [-0.2, 0.9, 0], "size": [0.2, 0.02, 0.2],
             "attributes": {} if plate_fragile is None else {"fragile": plate_fragile}}
    cup = {"id": "cup_B", "category": "cup", "position": [0.2, height[cup_at], 0], "size": [0.08, 0.1, 0.08],
           "attributes": {"fragile": False, "material": "plastic"}}
    return {"objects": [furniture("table_01", "table", 0.7), furniture("shelf_lower", "shelf", 1.7),
                        furniture("shelf_upper", "shelf", 2.7), plate, cup, *(extra or [])]}


def scene(**kw) -> SceneSnapshot:
    return SceneSnapshot.model_validate(scene_json(**kw))


def store(norms: list[NormRule] | None = None, **kw) -> StateStore:
    state = StateStore()
    state.set_scene(scene(**kw))
    state.set_norms(NORMS if norms is None else norms)
    return state


def request(state: StateStore, requester: str | None = None):
    return state.open_task(TEXT, ["plate_A", "cup_B"], requester=requester, source_region="table_01")


def step(state: StateStore, object_id: str):
    return next((s for s in state.plan.steps if s.object_id == object_id), None)


# ---------------------------------------------------------------- 計画


def test_norms_apply_without_a_request():
    # 依頼が無くても、運ぶ物すべてを暗黙の依頼にして同じ判定をする（行の記録は残さない）
    state = store()
    assert state.task is None
    assert [(s.object_id, s.status, s.to.region_id) for s in state.plan.steps] == [
        ("plate_A", "deferred", "shelf_upper"), ("cup_B", "ok", "shelf_lower")]
    assert next(v for v in step(state, "plate_A").verdicts if v.rule_id == "R1").value == "violated"


def test_only_prohibitions_make_no_plan():
    assert store(norms=[R1]).plan is None  # 収納先を決める取り決めが無ければ、運ぶ物が決まらない


def test_plate_is_deferred_with_destination_and_cup_is_planned():
    state = store()
    task = request(state)

    plate, cup = task.row("plate_A"), task.row("cup_B")
    # 皿: 指定先は上段と分かっているが、つかむと R1 に反する（予測）ので保留
    assert (plate.destination, plate.destination_rule_ids, plate.exec_state) == ("shelf_upper", ["R3a"], "deferred")
    assert (plate.verdicts["R1"].value, plate.verdicts["R1"].basis) == ("violated", "predicted")
    assert "Don't touch fragile things" in plate.reason
    # コップ: 下段へ
    assert (cup.destination, cup.exec_state) == ("shelf_lower", "pending")
    assert cup.verdicts["R1"].value == "not_applicable"
    assert (cup.verdicts["R3b"].value, cup.verdicts["R3b"].basis) == ("compliant", "predicted")

    s_plate, s_cup = step(state, "plate_A"), step(state, "cup_B")
    assert (s_plate.status, s_plate.to.region_id, s_plate.rule_id) == ("deferred", "shelf_upper", "R3a")
    assert [(v.rule_id, v.value) for v in s_plate.verdicts] == [("R1", "violated")]
    assert (s_cup.status, s_cup.to.region_id, s_cup.rule_id) == ("ok", "shelf_lower", "R3b")
    assert [s.index for s in state.plan.steps] == [0, 1]
    assert task.counts() == {"total": 2, "done": 0, "deferred": 1, "pending": 1}


def test_unknown_fragility_is_deferred_with_missing_fact():
    state = store(plate_fragile=None)
    plate = request(state).row("plate_A")
    assert (plate.destination, plate.exec_state, plate.verdicts["R1"].value) == ("shelf_upper", "deferred", "undetermined")
    assert [(m.entity_id, m.key) for m in plate.missing] == [("plate_A", "attr:fragile")]
    assert step(state, "plate_A").status == "deferred"


def test_denominator_stays_when_cup_leaves_the_table():
    state = store()
    task = request(state)
    state.set_scene(scene(cup_at="shelf_lower"))  # 下段にあるのを観測した

    cup = task.row("cup_B")
    assert (cup.exec_state, cup.verdicts["R3b"].value, cup.verdicts["R3b"].basis) == ("done", "compliant", "observed")
    assert task.counts() == {"total": 2, "done": 1, "deferred": 1}
    assert [s.object_id for s in state.plan.steps] == ["plate_A"]  # コップの step は無くなるが、行は残る
    assert [v.basis for v in cup.history if v.rule_id == "R3b"] == ["predicted", "observed"]


def test_correcting_fragile_changes_only_the_plate_grasp_verdict():
    state = store()
    task = request(state)
    state.set_scene(scene(cup_at="shelf_lower"))
    cup_before = task.row("cup_B").model_dump()

    state.set_scene(scene(cup_at="shelf_lower", plate_fragile=False))  # 「この皿は割れ物ではない」

    plate = task.row("plate_A")
    assert (plate.exec_state, plate.destination) == ("pending", "shelf_upper")  # 上段の指定はそのまま
    assert [v.value for v in plate.history if v.rule_id == "R1"] == ["violated", "not_applicable"]
    assert step(state, "plate_A").status == "ok"
    assert task.row("cup_B").model_dump() == cup_before  # コップの完了記録は変わらない
    assert task.counts() == {"total": 2, "done": 1, "pending": 1}


def test_same_scene_again_keeps_plan_and_history():
    state = store()
    task = request(state)
    plan_id, lengths = state.plan.id, [len(r.history) for r in task.rows]
    state.clock.advance(120)
    state.set_scene(scene())
    assert state.plan.id == plan_id and [len(r.history) for r in task.rows] == lengths


def test_only_requested_objects_are_planned():
    # 依頼のあとで机に置かれた物は、対象にならない
    state = store()
    request(state)
    late = {"id": "cup_C", "category": "cup", "position": [0.4, 0.9, 0.3], "size": [0.08, 0.1, 0.08]}
    state.set_scene(scene(extra=[late]))
    assert [s.object_id for s in state.plan.steps] == ["plate_A", "cup_B"]


def test_no_destination_rule_defers_but_other_objects_still_planned():
    state = store(norms=[R3B])
    task = request(state)
    plate = task.row("plate_A")
    assert (plate.destination, plate.exec_state, plate.reason) == (None, "deferred", "No agreement decides the storage location")
    assert (step(state, "plate_A").status, step(state, "plate_A").to) == ("deferred", None)
    assert step(state, "cup_B").status == "ok"


def test_legacy_rules_give_destinations_and_manual_placement_wins():
    state = StateStore()
    state.set_scene(scene())
    state.set_rules([Rule(id="r_dish", text="Dishes on the lower shelf", condition={"attribute": "group", "equals": "dish"},
                          target_region="shelf_lower")])
    state.set_norms([R1])
    task = request(state)
    assert (task.row("cup_B").destination, step(state, "cup_B").rule_id) == ("shelf_lower", "r_dish")
    assert task.row("plate_A").exec_state == "deferred"  # 旧ルールで収納先が決まっても、R1 は効く

    state.set_placement("cup_B", "shelf_upper")
    assert (step(state, "cup_B").to.region_id, step(state, "cup_B").locked, step(state, "cup_B").rule_id) == (
        "shelf_upper", True, None)


def test_exception_lets_the_requester_move_the_plate():
    norms = [*NORMS, exception_for("user_01")]
    by_owner = store(norms=norms)
    assert request(by_owner, requester="user_01").row("plate_A").exec_state == "pending"
    by_other = store(norms=norms)
    assert request(by_other, requester="user_02").row("plate_A").exec_state == "deferred"
    anonymous = store(norms=norms)
    row = request(anonymous).row("plate_A")  # 依頼者が分からない: 例外の成立は未確定
    assert (row.exec_state, row.verdicts["R1"].value) == ("deferred", "undetermined")
    assert [(m.entity_id, m.key) for m in row.missing] == [(None, "requester")]


def test_close_task_returns_to_implicit_planning_and_new_request_closes_old():
    state = store()
    first = request(state)
    second = request(state)
    assert first.closed_at is not None and state.active_task is second and second.id == "task_2"
    state.close_task()
    assert state.active_task is None and state.task is second  # 記録は残る
    # 依頼なしの作り方（運ぶ物すべてを暗黙の依頼）に戻る。判定は同じ
    assert [s.status for s in state.plan.steps] == ["deferred", "ok"]


# ---------------------------------------------------------------- 実行（FakeRobot）


def test_executor_carries_the_cup_and_leaves_the_plate():
    async def main() -> None:
        state = store()
        task = request(state)

        async def publish() -> None:
            pass

        ex = Executor(state, FakeRobot(phase_delay=0.0), EventLog(), publish)
        assert ex.snapshot()["steps"][step(state, "plate_A").id]["status"] == "blocked"
        await ex.start(allow_unplanned=True)
        for _ in range(2000):
            if ex.mode == "idle":
                break
            await asyncio.sleep(0.002)
        assert (ex.mode, ex.reason) == ("idle", "finished")
        region = {o.id: o.region_id for o in state.scene.objects}
        assert (region["cup_B"], region["plate_A"]) == ("shelf_lower", "table_01")
        assert task.counts() == {"total": 2, "done": 1, "deferred": 1}
        await ex.close()

    asyncio.run(main())


# ---------------------------------------------------------------- WebSocket


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


def call(ws, rid: str, method: str, params: dict | None = None) -> dict:
    ws.send_json({"type": "request", "id": rid, "method": method, **({"params": params} if params is not None else {})})
    return recv_until(ws, is_response(rid))[-1]


def test_request_over_websocket(client):
    with connect(client) as (ws, _w, _s):
        assert call(ws, "1", "scene.update", scene_json())["ok"]
        norms = [n.model_dump(mode="json", by_alias=True) for n in NORMS]
        assert call(ws, "2", "norms.set", {"norms": norms})["result"] == {"version": 2, "norms": 3, "steps": 2}

        res = call(ws, "3", "task.request", {"text": TEXT, "requester": "user_01"})
        assert res["ok"], res
        result = res["result"]
        assert result["task"]["source_region"] == "table_01"  # 机が 1 つなら、そこを対象にする
        assert [r["object_id"] for r in result["task"]["rows"]] == ["plate_A", "cup_B"]
        assert result["counts"] == {"total": 2, "done": 0, "deferred": 1, "pending": 1}

        state = call(ws, "4", "state.get")["result"]
        assert [s["status"] for s in state["plan"]["steps"]] == ["deferred", "ok"]
        assert state["task"]["rows"][0]["verdicts"]["R1"]["value"] == "violated"
        assert len(state["norms"]) == 3 and state["clock"]["overridden"] is False

        assert call(ws, "5", "task.get")["result"]["counts"]["total"] == 2
        assert call(ws, "6", "task.close")["ok"]
        assert call(ws, "7", "task.close")["error"]["code"] == "invalid_state"


def test_request_errors_over_websocket(client):
    with connect(client) as (ws, _w, _s):
        assert call(ws, "1", "task.request", {"text": TEXT})["error"]["code"] == "invalid_params"  # 机が無い
        call(ws, "2", "scene.update", scene_json())
        assert call(ws, "3", "task.request", {"text": TEXT, "source_region": "nope"})["error"]["code"] == "invalid_params"
        assert call(ws, "4", "task.request", {"text": TEXT, "source_region": "shelf_upper"})["error"]["code"] == "invalid_state"
        bad = [{**exception_for("user_01").model_dump(mode="json", by_alias=True)}]  # 元の禁止 R1 が無い
        assert call(ws, "5", "norms.set", {"norms": bad})["error"]["code"] == "invalid_params"


def test_clock_over_websocket(client):
    with connect(client) as (ws, _w, _s):
        frozen = call(ws, "1", "clock.set", {"time": "17:55", "freeze": True})["result"]
        assert frozen["overridden"] and frozen["frozen"] and "T17:55:00" in frozen["now"]
        assert "T18:02:00" in call(ws, "2", "clock.advance", {"seconds": 420})["result"]["now"]
        assert "T18:02:00" in call(ws, "3", "clock.get")["result"]["now"]
        assert call(ws, "4", "clock.set", {"time": "25:99"})["error"]["code"] == "invalid_params"
        assert call(ws, "5", "clock.reset")["result"]["overridden"] is False
