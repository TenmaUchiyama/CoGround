"""家庭ルールの R2（領域への進入の禁止）と R4（子供が近くにいる間は台車を止める）: 計画側と実行側。

場面: 机（ROS の x = 2）のコップを、棚（x = 8）へ運ぶ。途中（x = 4.5〜5.5、y = ±1）に zone_play がある。
台車は原点から出て、まっすぐ進むと zone_play を横切る。ロボットは ROS なしの代役（FakeRobot）。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from coground_server.eventlog import EventLog
from coground_server.executor import Executor
from coground_server.models import Person, SceneRegion, SceneSnapshot
from coground_server.motion import MotionStore
from coground_server.norms import NormRule, WorldSample, evaluate
from coground_server.norms.geometry import FOOTPRINT_RADIUS, polygon_distance, route_around
from coground_server.norms.monitors import build_monitors, route_verdicts
from coground_server.norms.predicates import PersonAt
from coground_server.norms.report import build_report
from coground_server.robot import FakeRobot
from coground_server.state import StateStore

R3 = NormRule.model_validate({
    "id": "R3b", "original_text": "Cups go on the shelf", "norm": "obligation",
    "target": {"kind": "object", "where": {"attribute": "category", "equals": "cup"}},
    "requirement": {"window": "at_place_complete", "predicate": "placed_in", "args": {"region": "shelf_lower"}},
})
R2 = NormRule.model_validate({
    "id": "R2", "original_text": "After 6 pm the kids play around here, so don't go into this area of the living room",
    "norm": "prohibition", "scope": {"from": "18:00", "until": None},
    "target": {"kind": "zone", "id": "zone_play"},
    "requirement": {"window": "during_base_motion", "predicate": "footprint_overlaps",
                    "transition": {"from": False, "to": True}},
})
R4 = NormRule.model_validate({
    "id": "R4", "original_text": "Stop the base when a child is within 5 m", "norm": "obligation",
    "scope": {"when": {"predicate": "near_child", "args": {"distance": 5.0}}},
    "target": {"kind": "robot"},
    "requirement": {"window": "whole", "predicate": "base_stopped"},
})
ZONE = [(4.5, -1.0), (5.5, -1.0), (5.5, 1.0), (4.5, 1.0)]  # ROS の x, y


def unity(points: list[tuple[float, float]]) -> list[list[float]]:
    """ROS の (x, y) -> Unity の [x, y, z]"""
    return [[-y, 0.0, x] for x, y in points]


def zone(points: list[tuple[float, float]] = ZONE, zone_id: str = "zone_play") -> SceneRegion:
    return SceneRegion(id=zone_id, label="play area", polygon=unity(points))


def scene(*, cup_fragile: bool = False) -> SceneSnapshot:
    def furniture(oid: str, category: str, z: float) -> dict:
        return {"id": oid, "category": category, "position": [0, 0.7, z], "size": [1, 0.1, 1],
                "place_zone": {"center": [0, 0.9, z], "size": [1, 0.3, 1]}}

    return SceneSnapshot.model_validate({"objects": [
        furniture("table_01", "table", 2.0), furniture("shelf_lower", "shelf", 8.0),
        {"id": "cup_B", "category": "cup", "position": [0, 0.9, 2.0], "size": [0.08, 0.1, 0.08],
         "attributes": {"fragile": cup_fragile}},
    ]})


def child(x: float, y: float, kind: str = "child") -> Person:
    return Person(id="kid_1", kind=kind, position=(-y, 0.0, x))  # type: ignore[arg-type]


class Rig:
    def __init__(self, norms: list[NormRule], time: str, *, zones: list[SceneRegion] | None = None, **scene_kw) -> None:
        self.state = StateStore()
        self.state.clock.freeze(self.state.clock.at(time))
        self.state.set_scene(scene(**scene_kw))
        for z in [zone()] if zones is None else zones:
            self.state.define_zone(z)
        self.state.set_norms(norms)
        self.task = self.state.open_task("Clear everything off the desk", ["cup_B"], source_region="table_01")
        self.robot = FakeRobot(phase_delay=0.0)
        self.events = EventLog()
        self.motion = MotionStore(self.state, self.robot, self.events, self._publish)
        self.ex = Executor(self.state, self.robot, self.events, self._publish, self.motion)
        self.ex.monitor.period = 0.005

    async def _publish(self) -> None:
        pass

    @property
    def cup(self):
        return self.task.row("cup_B")

    @property
    def step(self):
        return next(s for s in self.state.plan.steps if s.object_id == "cup_B")

    def at(self, hhmm: str, seconds: int = 0) -> None:
        self.state.clock.freeze(self.state.clock.at(hhmm) + timedelta(seconds=seconds))

    def hook(self, cond, action) -> None:
        """台車が 1 歩進む前に cond() が初めて成り立ったら action() を呼ぶ。"""
        gate, fired = self.robot.gate, []

        async def wrapped() -> None:
            if not fired and cond():
                fired.append(True)
                action()
            await gate()

        self.robot.gate = wrapped

    async def until(self, cond, timeout: float = 3.0) -> None:
        async def poll() -> None:
            while not cond():
                await asyncio.sleep(0.002)
        try:
            await asyncio.wait_for(poll(), timeout)
        except asyncio.TimeoutError:
            raise AssertionError(f"Condition never holds: {self.ex.snapshot()} / {self.task.model_dump()}")

    async def run_to_stop(self) -> None:
        await self.ex.start()
        await self.until(lambda: self.ex.mode != "running")

    def clear_of_zone(self, points: list[tuple[float, float]] = ZONE) -> bool:
        """通った位置が、どれも領域に重なっていない。"""
        return all(polygon_distance((b[0], b[1]), points) >= FOOTPRINT_RADIUS - 1e-6 for b in self.robot.base_log)


def run(coro) -> None:
    asyncio.run(coro)


def at(hhmm: str, seconds: int = 0) -> datetime:
    h, m = hhmm.split(":")
    return datetime(2026, 11, 18, int(h), int(m), seconds, tzinfo=timezone(timedelta(hours=9)))


# ---------------------------------------------------------------- 述語と経路の判定


def test_footprint_overlaps_and_near_child_are_three_valued():
    def sample(**kw) -> list[WorldSample]:
        return [WorldSample(phase="base_motion", t=at("18:05"), **kw)]

    inside = evaluate(R2.model_copy(update={"requirement": R2.requirement.model_copy(update={"transition": None})}),
                      sample(base=(5.0, 0.0, 0.0), zones={"zone_play": ZONE}), None, basis="observed")
    assert inside.value == "violated"
    # 領域の形が分からなければ未確定で、足りないのは領域の形
    unknown = evaluate(R2, [*sample(base=(0.0, 0.0, 0.0)), *sample(base=(5.0, 0.0, 0.0))], None, basis="predicted")
    assert unknown.value == "undetermined" and [(m.entity_id, m.key) for m in unknown.missing] == [("zone_play", "zone_shape")]

    def r4(people, speed):
        return evaluate(R4, sample(base=(0.0, 0.0, 0.0), base_speed=speed, people=people), None, basis="observed")

    near = [PersonAt(id="k", kind="child", xy=(3.0, 0.0))]
    assert r4(near, 0.4).value == "violated" and r4(near, 0.0).value == "compliant"
    assert r4([PersonAt(id="k", kind="child", xy=(9.0, 0.0))], 0.4).value == "not_applicable"
    assert r4([PersonAt(id="a", kind="adult", xy=(1.0, 0.0))], 0.4).value == "not_applicable"
    lost = r4(None, 0.4)  # 人の位置が観測できていない
    assert lost.value == "undetermined" and [(m.entity_id, m.key) for m in lost.missing] == [(None, "person_pose")]
    assert r4([PersonAt(id="x", kind="unknown", xy=(1.0, 0.0))], 0.4).value == "undetermined"  # 子供かどうか分からない


def test_route_is_judged_at_the_time_it_passes():
    track = [[0.0, 0.0, 0.0, 0.0], [100.0, 8.0, 0.0, 0.0]]  # 0.08 m/s。x = 4.2 で領域に重なる（52.5 秒後）
    zones = {"zone_play": ZONE}

    def judge(start: datetime):
        return route_verdicts([R2], track, start, zones)[0]

    late = judge(at("18:01"))
    assert late.value == "violated" and late.t.strftime("%H:%M") == "18:01"  # 始点も終点も外で、途中だけ横切る
    assert judge(at("17:57")).value == "not_applicable"      # 17:58 に入る: 禁止が効く前
    # 17:59 に入って、18:00 には中にいるだけ: 入ること（変化）は起きていないので、反しない
    assert judge(at("17:59")).value == "compliant"
    assert route_verdicts([R2], track, at("18:01"), {})[0].value == "undetermined"  # 領域の形が無い
    assert route_verdicts([R3], track, at("18:01"), zones) == []  # 進入の禁止が無ければ、何も調べない


def test_route_around_keeps_clear_and_fails_when_goal_is_inside():
    path = route_around((1.4, 0.0), (7.4, 0.0), [ZONE], 0.35)
    assert path[0] == (1.4, 0.0) and path[-1] == (7.4, 0.0) and len(path) > 2
    assert route_around((1.4, 0.0), (5.0, 0.0), [ZONE], 0.35) is None
    assert route_around((0.0, 0.0), (1.0, 0.0), [ZONE], 0.35) == [(0.0, 0.0), (1.0, 0.0)]


def test_monitors_are_derived_from_rules():
    specs = {m.rule_id: m for m in build_monitors([R3, R2, R4])}
    assert set(specs) == {"R2", "R4"}
    assert (specs["R2"].response, specs["R2"].entities, specs["R2"].predicate) == ("replan", ["zone_play"], "footprint_overlaps")
    assert (specs["R4"].response, specs["R4"].entities, specs["R4"].predicate) == ("hold", ["child"], "near_child")


# ---------------------------------------------------------------- E1: 計画側


def test_plan_does_not_detour_before_the_rule_is_active():
    async def main() -> None:
        rig = Rig([R3, R2], "17:50")
        summary = await rig.motion.plan()
        assert summary["status"] == "ready" and summary["keepout"] == []
        assert len(summary["attempts"]) == 1 and summary["attempts"][0]["steps"]["s1"]["verdicts"] == {"R2": "not_applicable"}
        assert (rig.cup.verdicts["R2"].value, rig.cup.verdicts["R2"].basis) == ("not_applicable", "predicted")
        assert summary["monitors"] == [{"rule_id": "R2", "predicate": "footprint_overlaps", "entities": ["zone_play"],
                                        "response": "replan"}]
        await rig.ex.close()

    run(main())


def test_plan_detours_only_after_a_violation_is_predicted():
    async def main() -> None:
        rig = Rig([R3, R2], "18:05")
        summary = await rig.motion.plan()
        assert summary["status"] == "ready" and summary["keepout"] == ["zone_play"]
        first, second = summary["attempts"]
        # 1 回目は領域を避けずに計画して、違反の予測が出る（入る時刻も残る）。2 回目は領域を避けて適合
        assert first["keepout"] == [] and first["steps"]["s1"]["verdicts"] == {"R2": "violated"}
        assert first["steps"]["s1"]["enters_at"]["R2"].startswith("2") and "T18:05" in first["steps"]["s1"]["enters_at"]["R2"]
        assert second["keepout"] == ["zone_play"] and second["steps"]["s1"]["verdicts"] == {"R2": "compliant"}
        track = rig.motion.timeline()["timeline"]["base"]
        assert all(polygon_distance((p[1], p[2]), ZONE) >= FOOTPRINT_RADIUS for p in track)
        assert rig.step.status == "ok" and rig.cup.exec_state == "pending"
        assert (rig.cup.verdicts["R2"].value, rig.cup.verdicts["R2"].basis) == ("compliant", "predicted")
        assert rig.cup.route["keepout"] == ["zone_play"] and len(rig.cup.route["attempts"]) == 2

        await rig.run_to_stop()  # 実行でも同じ領域を避ける
        assert (rig.ex.mode, rig.ex.reason) == ("idle", "finished") and rig.cup.exec_state == "done"
        assert rig.clear_of_zone() and rig.ex.monitor.holds == []
        assert (rig.cup.verdicts["R2"].value, rig.cup.verdicts["R2"].basis) == ("compliant", "observed")
        await rig.ex.close()

    run(main())


WALL = [(6.0, -3.0), (10.0, -3.0), (10.0, 3.0), (6.0, 3.0)]  # 棚ごと囲む領域（棚の前に止まれない）


def test_no_compliant_route_defers_the_row_and_records_what_was_searched():
    async def main() -> None:
        rig = Rig([R3, R2], "18:05", zones=[zone(WALL)])
        summary = await rig.motion.plan()
        assert summary["status"] == "ready" and summary["steps"]["s1"]["status"] == "infeasible"
        assert "R2" in summary["steps"]["s1"]["reason"] and "No path that doesn't violate" in summary["steps"]["s1"]["reason"]
        assert (rig.step.status, rig.cup.exec_state) == ("deferred", "deferred")
        assert (rig.cup.verdicts["R2"].value, rig.cup.verdicts["R2"].basis) == ("violated", "predicted")
        tried = rig.cup.route["attempts"]  # 探した条件: 避けずに計画 -> 違反、避けて計画 -> 計画できない
        assert [a["keepout"] for a in tried] == [[], ["zone_play"]]
        assert tried[0]["steps"]["s1"]["verdicts"] == {"R2": "violated"} and tried[1]["steps"]["s1"]["status"] == "infeasible"
        report = build_report(rig.task, rig.state.all_norms())
        assert "no path that doesn't violate" in report["rows"][0]["sentence"] and report["counts"]["deferred"] == 1
        await rig.run_to_stop()  # 保留は実行しない
        assert rig.ex.reason == "finished" and rig.robot.base_log == [] and rig.robot.holding is None

        # 時計を戻す（禁止が効く前）と保留が解け、計画し直せば運べる
        rig.at("17:00")
        rig.state.replan()
        assert rig.cup.exec_state == "pending" and rig.cup.verdicts["R2"].value == "undetermined"
        summary = await rig.motion.plan()
        assert summary["steps"]["s1"]["status"] == "ok" and rig.cup.verdicts["R2"].value == "not_applicable"
        await rig.ex.close()

    run(main())


def test_undefined_zone_is_undetermined_and_names_the_missing_shape():
    async def main() -> None:
        rig = Rig([R3, R2], "18:05", zones=[])
        await rig.motion.plan()
        assert rig.cup.exec_state == "deferred" and rig.cup.verdicts["R2"].value == "undetermined"
        assert [(m.entity_id, m.key) for m in rig.cup.missing] == [("zone_play", "zone_shape")]
        rig.state.define_zone(zone())  # 範囲が決まれば、計画し直して運べる
        assert rig.cup.exec_state == "pending"
        assert (await rig.motion.plan())["keepout"] == ["zone_play"] and rig.step.status == "ok"
        await rig.ex.close()

    run(main())


# ---------------------------------------------------------------- E2: 実行側


def test_departure_delay_makes_the_robot_wait_before_the_boundary_and_replan():
    async def main() -> None:
        rig = Rig([R3, R2], "17:57")
        summary = await rig.motion.plan()
        assert summary["keepout"] == []  # 予測では 17:57 台に通るので、避けない
        # コップを持って出発するころには 18:02 になっていた
        rig.hook(lambda: rig.robot.holding == "cup_B", lambda: rig.at("18:02"))
        await rig.run_to_stop()

        assert (rig.ex.mode, rig.ex.reason) == ("idle", "finished") and rig.cup.exec_state == "done"
        (hold,) = rig.ex.monitor.holds
        assert hold["rule_ids"] == ["R2"] and hold["outcome"] == "released" and hold["object_id"] == "cup_B"
        # 境界の手前で止まり、止まっている間は動かず、領域を避ける経路に替えてから再開した
        stopped_at = hold["requested"]["base"]
        assert polygon_distance((stopped_at[0], stopped_at[1]), ZONE) >= FOOTPRINT_RADIUS
        assert hold["requested"]["distance"]["R2"] <= 0.5 and hold["released"]["base"] == stopped_at
        assert [(r["keepout"], r["ok"], r.get("verdicts")) for r in hold["replans"]] == [
            (["zone_play"], True, {"R2": "compliant"})]
        assert hold["keepout_after"] == ["zone_play"] and rig.clear_of_zone()
        assert rig.robot.holding is None  # 持ったまま再開して、置いた
        assert (rig.cup.verdicts["R2"].value, rig.cup.verdicts["R2"].basis) == ("compliant", "observed")
        await rig.ex.close()

    run(main())


def test_already_inside_when_the_rule_becomes_active_is_not_asked_to_leave():
    async def main() -> None:
        rig = Rig([R3, R2], "17:58")
        await rig.motion.plan()
        # 17:59 に領域へ入り、中にいる間に 18:00 になる
        rig.hook(lambda: rig.robot.holding == "cup_B", lambda: rig.at("17:59"))
        rig.hook(lambda: 4.6 < rig.robot.base[0] < 5.4, lambda: rig.at("18:00", 30))
        await rig.run_to_stop()
        assert (rig.ex.mode, rig.ex.reason) == ("idle", "finished") and rig.cup.exec_state == "done"
        assert rig.ex.monitor.holds == [] and not rig.clear_of_zone()  # 止められず、領域を通り抜けた
        assert rig.cup.verdicts["R2"].value == "compliant"  # 中にいただけで、入ってはいない
        await rig.ex.close()

    run(main())


def test_no_route_during_execution_stops_holding_the_object_and_defers():
    async def main() -> None:
        rig = Rig([R3, R2], "17:57", zones=[zone(WALL)])
        await rig.motion.plan()
        rig.hook(lambda: rig.robot.holding == "cup_B", lambda: rig.at("18:02"))
        await rig.run_to_stop()
        assert rig.ex.mode == "paused" and "No path that doesn't violate" in rig.ex.reason and "while holding" in rig.ex.reason
        assert rig.robot.holding == "cup_B" and not rig.robot.held
        (hold,) = rig.ex.monitor.holds
        assert hold["outcome"] == "blocked" and rig.clear_of_zone(WALL)
        block = rig.state.route_blocks["cup_B"]
        assert block.searched["during"] == "execution" and [v.value for v in block.verdicts] == ["violated"]
        assert rig.step.status == "deferred"
        await rig.ex.close()

    run(main())


# ---------------------------------------------------------------- F: R4（hold と再計画）


def test_hold_near_child_keeps_the_cup_and_resumes_only_after_the_route_is_reverified():
    async def main() -> None:
        rig = Rig([R3, R2, R4], "17:55")
        rig.state.set_people([child(30.0, 30.0)], valid_for=0)
        await rig.motion.plan()
        # コップを持って棚へ向かう途中、子供が 3 m まで近づく
        rig.hook(lambda: rig.robot.holding == "cup_B" and rig.robot.base[0] >= 3.0,
                 lambda: rig.state.set_people([child(6.0, 0.0)], valid_for=0))
        await rig.ex.start()
        await rig.until(lambda: rig.ex.monitor.active is not None and rig.ex.monitor.active["waiting_for"] == ["R4"])
        active = rig.ex.monitor.active
        assert rig.robot.held and rig.robot.holding == "cup_B" and rig.ex.mode == "running"  # スキルは取り消さない
        held_at = list(rig.robot.base)

        # 止まっている間に 18 時を過ぎる（元の経路は、もう zone_play を通れない）
        rig.at("18:02")
        await asyncio.sleep(0.05)
        assert rig.robot.held and rig.robot.base == held_at
        # 子供が離れても、残りの経路の再検証が済むまで動かない。再検証で zone_play を避ける経路に替わる
        rig.state.set_people([child(30.0, 30.0)], valid_for=0)
        await rig.until(lambda: rig.ex.mode != "running")

        assert (rig.ex.mode, rig.ex.reason) == ("idle", "finished")
        assert rig.cup.exec_state == "done" and rig.robot.holding is None  # 持ったまま再開し、配置の観測まで届いた
        (hold,) = rig.ex.monitor.holds
        assert hold is active and hold["outcome"] == "released" and hold["rule_ids"] == ["R4"]
        # 止めるよう求めた時刻・距離と、実際に止まった時刻・距離が別々に残る
        assert hold["requested"]["t"].endswith("17:55:00+09:00") and hold["requested"]["distance"]["R4"] <= 5.0
        assert hold["stopped"]["base"] == held_at and hold["stopped"]["distance"]["R4"] <= 5.0 and hold["stopped"]["confirmed"]
        assert "t" in hold["stopped"] and hold["stopped"] is not hold["requested"]
        assert hold["released"]["base"] == held_at  # 再計画が終わるまで、台車の位置は変わらない
        assert [(r["keepout"], r.get("verdicts")) for r in hold["replans"]] == [
            ([], {"R2": "violated"}), (["zone_play"], {"R2": "compliant"})]
        assert rig.clear_of_zone()
        assert rig.cup.verdicts["R4"].value in ("compliant", "not_applicable") and rig.cup.verdicts["R4"].basis == "observed"
        report = build_report(rig.task, rig.state.all_norms(), holds=rig.ex.monitor.snapshot()["holds"])
        assert [h["id"] for h in report["rows"][0]["holds"]] == [hold["id"]]
        await rig.ex.close()

    run(main())


def test_hold_when_people_cannot_be_observed():
    async def main() -> None:
        rig = Rig([R3, R4], "12:00")  # 人の位置が一度も届いていない
        await rig.motion.plan()
        await rig.ex.start()
        await rig.until(lambda: rig.ex.monitor.active is not None and rig.ex.monitor.active["stopped"] is not None)
        active = rig.ex.monitor.active
        assert rig.robot.held and active["verdicts"] == {"R4": "undetermined"}
        assert active["missing"] == [{"entity_id": None, "key": "person_pose"}] and rig.robot.base == [0.0, 0.0, 0.0]
        rig.state.set_people([], valid_for=0)  # 「誰もいない」と観測できた
        await rig.until(lambda: rig.ex.mode != "running")
        assert (rig.ex.reason, rig.cup.exec_state) == ("finished", "done")
        await rig.ex.close()

    run(main())


def test_stale_people_observation_counts_as_unobserved():
    state = StateStore()
    state.set_people([child(1.0, 0.0)], valid_for=0.01)
    assert state.people_observed and state.people_samples()[0].xy == (1.0, 0.0)
    import time
    time.sleep(0.03)
    assert not state.people_observed and state.people_samples() is None
    assert state.snapshot()["people"]["observed"] is False


def test_grasp_is_rechecked_right_before_pick():
    evening = NormRule.model_validate({
        "id": "R1e", "original_text": "Don't touch fragile things after 6 pm", "norm": "prohibition", "scope": {"from": "18:00"},
        "target": {"kind": "object", "where": {"attribute": "fragile", "equals": True}},
        "requirement": {"window": "whole", "predicate": "contact"},
    })

    async def main() -> None:
        rig = Rig([R3, evening], "17:59", cup_fragile=True)
        await rig.motion.plan()
        assert rig.step.status == "ok"  # 17:59 にはつかんでよい
        rig.hook(lambda: True, lambda: rig.at("18:01"))  # 机へ向かう間に 18 時を過ぎる（Plan は作り直されていない）
        await rig.run_to_stop()
        assert rig.robot.holding is None and rig.cup.exec_state == "deferred"
        assert (rig.cup.verdicts["R1e"].value, rig.cup.verdicts["R1e"].basis) == ("violated", "predicted")
        assert any(e.get("action") == "pick_withheld" for e in rig.events.tail(50, "exec"))
        await rig.ex.close()

    run(main())
