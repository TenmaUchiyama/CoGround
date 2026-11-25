"""動作計画（MotionStore）と、それを使った実行。ロボットは ROS なしの代役（FakeRobot）。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from coground_server.eventlog import EventLog
from coground_server.executor import ExecError, Executor
from coground_server.models import Rule, SceneObject, SceneSnapshot
from coground_server.motion import MotionStore, approach_stops, place_for
from coground_server.robot import FakeRobot, ros_to_unity, unity_to_ros
from coground_server.state import StateStore

FIXTURES = Path(__file__).parent / "fixtures"
SCENARIO = json.loads((FIXTURES / "shelf_scenario.json").read_text())
TABLETOP = json.loads((FIXTURES / "tabletop_scene.json").read_text())
GLASS, PLASTIC = "glass_cup_1", "plastic_cup_1"


class Rig:
    def __init__(self, scene: dict | None = None, phase_delay: float = 0.0) -> None:
        self.state = StateStore()
        self.state.set_scene(SceneSnapshot.model_validate(scene or SCENARIO["initial_scene"]))
        if scene is None:
            self.state.set_rules([Rule.model_validate(r) for r in SCENARIO["rules"]])
            self.state.set_placement(PLASTIC, "shelf_upper")
        self.robot = FakeRobot(phase_delay=phase_delay)
        self.events = EventLog()
        self.motion = MotionStore(self.state, self.robot, self.events, self._publish)
        self.ex = Executor(self.state, self.robot, self.events, self._publish, self.motion)

    async def _publish(self) -> None:
        pass

    def step(self, object_id: str):
        return next(s for s in self.state.plan.steps if s.object_id == object_id)

    def region(self, object_id: str) -> str | None:
        return next(o.region_id for o in self.state.scene.objects if o.id == object_id)

    async def until(self, cond, timeout: float = 3.0) -> None:
        async def poll() -> None:
            while not cond():
                await asyncio.sleep(0.002)
        await asyncio.wait_for(poll(), timeout)


def run(coro):
    return asyncio.run(coro)


def test_coordinate_round_trip():
    assert ros_to_unity(unity_to_ros([1.0, 2.0, 3.0])) == [1.0, 2.0, 3.0]


def test_plan_shows_each_step_as_soon_as_it_is_done():
    """step は順に計画される。全体の結果を待たずに、終わった step から予測（preview）に結果が出る。"""
    async def main():
        rig = Rig()
        order = [s.id for s in rig.state.plan.steps if s.status == "ok" and s.to is not None]
        assert len(order) >= 2
        rig.robot.infeasible.add(rig.state.plan.steps[0].object_id)
        seen: list[dict[str, str]] = []

        async def publish() -> None:
            p = rig.motion.preview()
            seen.append({x["step_id"]: x["state"] for x in p["steps"]} | {"_": p["status"]})

        rig.motion._publish = publish
        await rig.motion.plan()
        # 1 つ目の結果が出た時点: まだ全体は確認中で、2 つ目は確認中のまま
        first = next(x for x in seen if x[order[0]] != "checking")
        assert first["_"] == "checking" and first[order[0]] == "stay_infeasible" and first[order[1]] == "checking"
        # 一度出た結果は、最後まで変わらない
        for sid in order:
            states = [x[sid] for x in seen if x[sid] != "checking"]
            assert states and len(set(states)) == 1
        assert seen[-1]["_"] == "ready" and seen[-1][order[1]] == "move"
    run(main())


def test_plan_makes_timeline_with_phases_in_order():
    async def main():
        rig = Rig()
        progress = []

        async def on_progress(d):
            progress.append(d)

        summary = await rig.motion.plan(on_progress=on_progress)
        assert summary["status"] == "ready" and summary["timeline_id"]
        assert {v["status"] for v in summary["steps"].values()} == {"ok"}
        assert progress and progress[0]["step_id"] == rig.step(GLASS).id
        tl = rig.motion.timeline()
        phases = [(p["step_id"], p["phase"]) for p in tl["timeline"]["phases"]]
        sid = rig.step(GLASS).id
        assert [ph for s, ph in phases if s == sid] == [
            "navigating", "opening", "approaching", "descending", "grasping", "lifting",
            "navigating", "moving", "lowering", "releasing", "retreating"]
        times = [p["t0"] for p in tl["timeline"]["phases"]]
        assert times == sorted(times) and tl["timeline"]["duration"] > 0
        assert [a["object"] for a in tl["timeline"]["attached"]] == [GLASS, PLASTIC]
        assert tl["step_ids"] == {s.id: s.id for s in rig.state.plan.steps}
    run(main())


def test_start_requires_fresh_plan():
    async def main():
        rig = Rig()
        with pytest.raises(ExecError, match="not planned"):
            await rig.ex.start()
        await rig.motion.plan()
        # 計画した後に物体が動いた -> 古い
        o = next(o for o in rig.state.scene.objects if o.id == GLASS)
        rig.state.move_object(GLASS, (o.position[0] + 0.05, o.position[1], o.position[2]), o.rotation, o.region_id)
        assert rig.motion.summary()["steps"][rig.step(GLASS).id]["status"] == "stale"
        with pytest.raises(ExecError, match="stale"):
            await rig.ex.start()
        await rig.ex.start(allow_unplanned=True)  # 計画なしでも動かせる（移動しない）
        await rig.until(lambda: rig.ex.mode == "idle")
        skills = [(h["skill"], h["mode"]) for h in rig.ex.history]
        # ガラスのコップ: つかむ計画は古い（物体が動いた）ので、移動せずその場でつかむ。
        # 持ってしまえば物体の位置は関係ないので、置くところは計画を使う
        assert skills[:3] == [("pick", None), ("navigate", None), ("place", "replay")]
        assert skills[3:] == [("navigate", None), ("pick", "replay"), ("navigate", None), ("place", "replay")]
    run(main())


def test_execute_with_plan_navigates_and_replays():
    async def main():
        rig = Rig()
        await rig.motion.plan()
        stops = {e["result"]["object"]: e["result"]["stops"] for e in rig.motion.entries.values()}
        await rig.ex.start()
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.ex.reason == "finished"
        assert [(h["skill"], h["mode"]) for h in rig.ex.history[:4]] == [
            ("navigate", None), ("pick", "replay"), ("navigate", None), ("place", "replay")]
        assert rig.robot.base == stops[PLASTIC]["place"]  # 最後に止まったのは、計画した位置
        assert rig.region(GLASS) == "shelf_lower" and rig.region(PLASTIC) == "shelf_upper"
        assert rig.motion.entries == {}  # 運び終わった step の計画は捨てる
    run(main())


def test_pause_between_navigate_and_pick():
    async def main():
        rig = Rig(phase_delay=0.02)
        await rig.motion.plan()
        await rig.ex.start()
        await rig.until(lambda: rig.ex.current is not None and rig.ex.current["skill"] == "navigate")
        await rig.ex.pause()
        await rig.until(lambda: rig.ex.mode == "paused")
        assert [h["skill"] for h in rig.ex.history] == ["navigate"]  # 移動が終わったところで止まる
        assert rig.ex.snapshot()["steps"][rig.step(GLASS).id]["status"] == "moving_to_pick"
        await rig.ex.resume()
        await rig.until(lambda: rig.ex.mode == "idle")
        assert [h["skill"] for h in rig.ex.history][:3] == ["navigate", "pick", "navigate"]  # 着いているので移動し直さない
    run(main())


def test_infeasible_step_is_left_and_the_rest_runs():
    async def main():
        rig = Rig()
        rig.robot.infeasible = {GLASS}
        summary = await rig.motion.plan()
        glass = summary["steps"][rig.step(GLASS).id]
        assert glass["status"] == "infeasible" and glass["reason"]
        assert summary["steps"][rig.step(PLASTIC).id]["status"] == "ok"
        with pytest.raises(ExecError, match="couldn't be planned"):
            await rig.ex.start([rig.step(GLASS).id])  # 成立しない step を名指しで実行はできない
        # 成立しない step があっても、独立して成立する step は実行できる。成立しない物は取りに行かない
        assert rig.ex.snapshot()["steps"][rig.step(GLASS).id]["status"] == "blocked"
        await rig.ex.start()
        await rig.until(lambda: rig.ex.mode == "idle")
        assert rig.region(PLASTIC) == "shelf_upper" and rig.region(GLASS) == "table_top"
        assert all(h["object_id"] != GLASS for h in rig.ex.history)
    run(main())


def test_nothing_verified_refuses_start():
    async def main():
        rig = Rig()
        rig.robot.infeasible = {GLASS, PLASTIC}
        await rig.motion.plan()
        with pytest.raises(ExecError, match="no step passed the check"):
            await rig.ex.start()
    run(main())


def test_robot_busy_or_failure_is_reported():
    async def main():
        rig = Rig()

        async def broken(request, on_progress=None):
            return {"plan_id": request["plan_id"], "plan_version": request["plan_version"], "error": "busy",
                    "steps": [], "timeline": None}

        rig.robot.plan_motion = broken
        summary = await rig.motion.plan()
        assert summary["status"] == "failed" and summary["error"] == "busy" and rig.motion.timeline() is None
    run(main())


def test_drop_into_receptacle():
    state = StateStore()
    state.set_scene(SceneSnapshot.model_validate(TABLETOP))
    state.set_placement("plate_1", "sink_1")
    step = state.plan.steps[0]
    release, rest, mode = place_for(state.scene, step)
    assert mode == "drop" and rest is not None
    sink = next(r for r in state.scene.regions if r.id == "sink_1")
    plate = next(o for o in state.scene.objects if o.id == "plate_1")
    top = sink.box.center[1] + sink.box.size[1] / 2
    assert ros_to_unity(release["position"])[1] == pytest.approx(top + plate.size[1] / 2 + 0.05)
    assert ros_to_unity(rest["position"]) == pytest.approx(list(step.to.pose.position))

    state.set_scene(state.scene.model_copy(update={"objects": [
        o.model_copy(update={"region_id": "sink_1"}) if o.id == "plate_1" else o for o in state.scene.objects]}))
    state.set_placement("plate_1", "table_1")  # 机へは、そっと置く
    step = next(s for s in state.plan.steps if s.object_id == "plate_1")
    assert place_for(state.scene, step)[2] == "place"


def test_approach_poses_are_used_first():
    async def main():
        scene = json.loads(json.dumps(TABLETOP))
        for o in scene["objects"]:
            if o["id"] == "sink_1":
                # シンクの手前 (Unity の -Z 側) に、シンクの方 (+Z) を向いて立つ
                x, _, z = o["position"]
                o["approach_poses"] = [{"position": [x, 0.0, z - 0.6], "rotation": [0, 0, 0, 1]}]
        rig = Rig(scene=scene)
        rig.state.set_placement("plate_1", "sink_1")
        sink = next(o for o in rig.state.scene.objects if o.id == "sink_1")
        assert approach_stops(rig.state.scene, "sink_1") == [
            pytest.approx(unity_to_ros([sink.position[0], 0.0, sink.position[2] - 0.6])[:2] + [0.0], abs=1e-3)]
        summary = await rig.motion.plan()
        step = summary["steps"][rig.step("plate_1").id]
        assert step["stop_source"] == {"pick": "auto", "place": "approach"}
        entry = next(iter(rig.motion.entries.values()))
        assert entry["result"]["stops"]["place"] == approach_stops(rig.state.scene, "sink_1")[0]
    run(main())


def test_approach_yaw_follows_unity_forward():
    scene = json.loads(json.dumps(TABLETOP))
    s = 0.7071068
    for o in scene["objects"]:
        if o["id"] == "sink_1":
            # Unity で Y 軸まわりに +90°（正面 +Z が +X を向く）-> ROS では -Y 方向 = yaw -90°
            o["approach_poses"] = [{"position": [0.0, 0.0, 0.0], "rotation": [0, s, 0, s]}]
    state = StateStore()
    state.set_scene(SceneSnapshot.model_validate(scene))
    assert approach_stops(state.scene, "sink_1")[0][2] == pytest.approx(-1.5708, abs=1e-3)
    assert approach_stops(state.scene, "no_such") == []
