"""Executor（Plan の実行と、実行中の介入）。ロボットは ROS なしの代役（FakeRobot）。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from coground_server.eventlog import EventLog
from coground_server.executor import ExecError, Executor
from coground_server.main import create_app
from coground_server.models import Rule, SceneSnapshot
from coground_server.robot import FakeRobot, unity_pose_to_ros
from coground_server.state import StateStore

SCENARIO = json.loads((Path(__file__).parent / "fixtures" / "shelf_scenario.json").read_text())
GLASS, PLASTIC = "glass_cup_1", "plastic_cup_1"


class Rig:
    """シーン: 机の上にコップ 2 つ。Plan: ガラスのコップ -> 棚の下段（ルール）、プラスチックのコップ -> 棚の上段（手で指定）。"""

    def __init__(self, phase_delay: float = 0.0) -> None:
        self.state = StateStore()
        self.state.set_scene(SceneSnapshot.model_validate(SCENARIO["initial_scene"]))
        self.state.set_rules([Rule.model_validate(r) for r in SCENARIO["rules"]])
        self.state.set_placement(PLASTIC, "shelf_upper")
        self.robot = FakeRobot(phase_delay=phase_delay)
        self.events = EventLog()
        self.published = 0
        self.ex = Executor(self.state, self.robot, self.events, self._publish)

    async def _publish(self) -> None:
        self.published += 1

    def region(self, object_id: str) -> str | None:
        return next(o.region_id for o in self.state.scene.objects if o.id == object_id)

    def step_id(self, object_id: str) -> str:
        return next(s.id for s in self.state.plan.steps if s.object_id == object_id)

    async def until(self, cond, timeout: float = 3.0) -> None:
        async def poll() -> None:
            while not cond():
                await asyncio.sleep(0.002)
        try:
            await asyncio.wait_for(poll(), timeout)
        except asyncio.TimeoutError:
            raise AssertionError(f"Condition never holds: {self.ex.snapshot()}")

    def skill_is(self, skill: str, object_id: str):
        return lambda: bool(self.ex.current and self.ex.current["skill"] == skill and self.ex.current["object_id"] == object_id)


def run(coro):
    return asyncio.run(coro)


def test_plan_has_two_steps():
    rig = Rig()
    assert [(s.object_id, s.to.region_id) for s in rig.state.plan.steps] == [(GLASS, "shelf_lower"), (PLASTIC, "shelf_upper")]
    assert {v["status"] for v in rig.ex.snapshot()["steps"].values()} == {"pending"}


def test_runs_all_steps():
    async def main():
        rig = Rig()
        await rig.ex.start()
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.ex.reason == "finished"
        assert rig.region(GLASS) == "shelf_lower" and rig.region(PLASTIC) == "shelf_upper"
        assert rig.state.plan is None or rig.state.plan.steps == []  # 運び終わったので、やることが無い
        assert [(h["object_id"], h["skill"], h["state"]) for h in rig.ex.history] == [
            (GLASS, "pick", "succeeded"), (GLASS, "place", "succeeded"),
            (PLASTIC, "pick", "succeeded"), (PLASTIC, "place", "succeeded")]
        assert rig.robot.holding is None
        assert rig.published > 0
    run(main())


def test_start_selected_steps_in_given_order():
    async def main():
        rig = Rig()
        await rig.ex.start([rig.step_id(PLASTIC)])
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.region(PLASTIC) == "shelf_upper" and rig.region(GLASS) == "table_top"
    run(main())


def test_pause_waits_for_skill_then_resume_places():
    async def main():
        rig = Rig(phase_delay=0.01)
        await rig.ex.start()
        await rig.until(rig.skill_is("pick", GLASS))
        await rig.ex.pause()
        await rig.until(lambda: rig.ex.mode == "paused")
        assert rig.ex.reason == "user"
        assert rig.robot.holding == GLASS  # つかむ動きは最後までやって、持ったまま止まる
        assert rig.ex.snapshot()["steps"][rig.step_id(GLASS)]["status"] == "holding"
        await rig.ex.resume()
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.region(GLASS) == "shelf_lower" and rig.region(PLASTIC) == "shelf_upper"
    run(main())


def test_stop_cancels_now_then_resume():
    async def main():
        rig = Rig(phase_delay=0.02)
        await rig.ex.start()
        await rig.until(rig.skill_is("pick", GLASS))
        await rig.ex.stop()
        await rig.until(lambda: rig.ex.mode == "paused")
        assert rig.ex.reason == "stopped"
        assert rig.ex.history[-1]["state"] == "canceled"
        assert rig.ex.snapshot()["steps"][rig.step_id(GLASS)]["status"] == "pending"  # 失敗にはしない
        await rig.ex.resume()
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.region(GLASS) == "shelf_lower"
    run(main())


def test_retarget_while_holding_places_at_new_target():
    async def main():
        rig = Rig(phase_delay=0.01)
        await rig.ex.start([rig.step_id(GLASS)])
        await rig.until(rig.skill_is("pick", GLASS))
        await rig.ex.pause()
        await rig.until(lambda: rig.ex.mode == "paused")
        rig.state.set_placement(GLASS, "shelf_upper")  # 持っている間に、行き先を変える（plan.place と同じ）
        await rig.ex.resume()
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.region(GLASS) == "shelf_upper"
        # 運び終わっても、ルール（割れ物は下段）が運び直さない: 手の指定が残っている
        assert rig.state.placements == {GLASS: "shelf_upper", PLASTIC: "shelf_upper"}
        assert [s.object_id for s in rig.state.plan.steps] == [PLASTIC]
    run(main())


def test_skip_current_step_puts_object_back():
    async def main():
        rig = Rig(phase_delay=0.01)
        await rig.ex.start()
        await rig.until(lambda: rig.robot.holding == GLASS)
        await rig.ex.skip(rig.step_id(GLASS))
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.region(GLASS) == "table_top"      # 元の場所に戻した
        assert rig.region(PLASTIC) == "shelf_upper"  # 次の step は実行した
        assert ("put_back", "succeeded") in [(h["skill"], h["state"]) for h in rig.ex.history]
        assert rig.ex.snapshot()["steps"][rig.step_id(GLASS)]["status"] == "skipped"
    run(main())


def test_skip_pending_step():
    async def main():
        rig = Rig()
        await rig.ex.skip(rig.step_id(GLASS))
        await rig.ex.start()
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.region(GLASS) == "table_top" and rig.region(PLASTIC) == "shelf_upper"
    run(main())


def test_failure_pauses_then_retry():
    async def main():
        rig = Rig()
        rig.robot.inject_failure("pick", "can't grasp")
        await rig.ex.start()
        await rig.until(lambda: rig.ex.mode == "paused")
        assert rig.ex.reason.startswith("failed:") and "can't grasp" in rig.ex.reason
        sid = rig.step_id(GLASS)
        assert rig.ex.snapshot()["steps"][sid] == {"status": "failed", "detail": "can't grasp"}
        await rig.ex.retry(sid)
        await rig.ex.resume()
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.region(GLASS) == "shelf_lower" and rig.region(PLASTIC) == "shelf_upper"
    run(main())


def test_failure_continue_policy_goes_on():
    async def main():
        rig = Rig()
        await rig.ex.set_policy(on_failure="continue")
        rig.robot.inject_failure("pick")
        await rig.ex.start()
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.region(GLASS) == "table_top" and rig.region(PLASTIC) == "shelf_upper"
        assert rig.ex.snapshot()["steps"][rig.step_id(GLASS)]["status"] == "failed"
    run(main())


def test_place_failure_then_resume_puts_back():
    async def main():
        rig = Rig()
        rig.robot.inject_failure("place", "can't reach")
        await rig.ex.start([rig.step_id(GLASS)])
        await rig.until(lambda: rig.ex.mode == "paused")
        assert rig.robot.holding == GLASS
        await rig.ex.resume()  # やり直し（retry）をしなければ、持っている物は元の場所へ戻す
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.robot.holding is None and rig.region(GLASS) == "table_top"
    run(main())


def test_confirm_each_step():
    async def main():
        rig = Rig()
        await rig.ex.set_policy(confirm="each_step")
        await rig.ex.start()
        await rig.until(lambda: rig.ex.waiting_confirm is not None)
        assert rig.ex.history == [] and rig.robot.holding is None  # 確認するまで動かない
        await rig.ex.confirm_step()
        await rig.until(lambda: rig.region(GLASS) == "shelf_lower" and rig.ex.waiting_confirm is not None)
        assert rig.region(PLASTIC) == "table_top"
        await rig.ex.confirm_step()
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.region(PLASTIC) == "shelf_upper"
    run(main())


def test_commands_rejected_in_wrong_state():
    async def main():
        rig = Rig(phase_delay=0.01)
        for bad in (rig.ex.pause(), rig.ex.stop(), rig.ex.resume(), rig.ex.confirm_step(), rig.ex.skip("nope")):
            with pytest.raises(ExecError):
                await bad
        await rig.ex.start()
        with pytest.raises(ExecError):
            await rig.ex.start()
        with pytest.raises(ExecError):
            await rig.ex.reset()
        await rig.ex.stop()
        await rig.until(lambda: rig.ex.mode == "paused")
        await rig.ex.reset()
        assert rig.ex.mode == "idle"
    run(main())


def test_events_are_logged():
    async def main():
        rig = Rig()
        await rig.ex.start(actor="llm")
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.events.tail(1, "exec")[0]["action"] == "finished"
        first = rig.events.tail(500, "exec")[0]
        assert first["action"] == "start" and first["actor"] == "llm"
        results = [e for e in rig.events.tail(500, "skill") if e["action"] == "result"]
        assert len(results) == 4 and all(e["state"] == "succeeded" for e in results)
    run(main())


def test_unity_pose_to_ros():
    from coground_server.models import Pose
    assert unity_pose_to_ros(Pose(position=(1.0, 2.0, 3.0), rotation=(0.1, 0.2, 0.3, 0.9))) == {
        "position": [3.0, -1.0, 2.0], "orientation": [0.3, -0.1, 0.2, -0.9]}


# ---------------------------------------------------------------- WebSocket 経由


def _call(ws, rid: str, method: str, params: dict | None = None) -> dict:
    ws.send_json({"type": "request", "id": rid, "method": method, "params": params or {}})
    while True:
        msg = ws.receive_json()
        if msg["type"] == "response" and msg["id"] == rid:
            return msg


def test_exec_over_websocket(monkeypatch):
    monkeypatch.setenv("COGROUND_FAKE_PHASE_DELAY", "0")
    monkeypatch.delenv("COGROUND_ROSBRIDGE_URL", raising=False)
    with TestClient(create_app()) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json()
        first = ws.receive_json()
        assert first["data"]["execution"]["mode"] == "idle"
        robot = first["data"]["execution"]["robot"]
        assert {k: robot[k] for k in ("kind", "connected", "holding", "busy", "held")} == {
            "kind": "fake", "connected": True, "holding": None, "busy": False, "held": False}

        bad = _call(ws, "1", "exec.pause")
        assert bad["ok"] is False and bad["error"]["code"] == "invalid_state"

        assert _call(ws, "2", "session.identify", {"actor": "script"})["ok"]
        assert _call(ws, "3", "scene.update", SCENARIO["initial_scene"])["ok"]
        assert _call(ws, "4", "rules.set", {"rules": SCENARIO["rules"]})["ok"]
        refused = _call(ws, "5a", "exec.start")
        assert refused["ok"] is False and "motion plan" in refused["error"]["message"]
        planned = _call(ws, "5b", "motion.plan")
        assert planned["ok"] and planned["result"]["status"] == "ready"
        timeline = _call(ws, "5c", "motion.get")["result"]
        phases = [p["phase"] for p in timeline["timeline"]["phases"]]
        assert phases[0] == "navigating" and "grasping" in phases and phases[-1] == "retreating"
        assert _call(ws, "5", "exec.start")["result"]["execution"]["mode"] == "running"

        for _ in range(200):
            msg = ws.receive_json()
            if msg.get("event") == "state.updated" and msg["data"]["execution"]["reason"] == "finished":
                break
        else:
            raise AssertionError("Execution doesn't finish")
        glass = next(o for o in msg["data"]["scene"]["objects"] if o["id"] == GLASS)
        assert glass["region_id"] == "shelf_lower"

        events = _call(ws, "6", "log.tail", {"n": 500})["result"]["events"]
        start = [e for e in events if e["type"] == "rpc" and e["method"] == "exec.start"][-1]
        assert start["actor"] == "script" and start["outcome"] == "ok"
        assert next(e for e in events if e["type"] == "rpc" and e["method"] == "scene.update")["params"] is None
        assert any(e["type"] == "skill" and e["action"] == "result" for e in events)
        skills = [(e["skill"], e.get("mode")) for e in events if e["type"] == "skill" and e["action"] == "result"]
        assert skills == [("navigate", None), ("pick", "replay"), ("navigate", None), ("place", "replay")]
        assert any(e["type"] == "motion" and e["action"] == "result" for e in events)
