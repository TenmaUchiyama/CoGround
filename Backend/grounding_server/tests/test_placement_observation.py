"""置く動作の成功と「収納済み」を分ける（executor.py の _verify_placement）。

収納済みと記録するのは、物体が指定の領域にあるのを観測したときだけ。
代役のロボットでは、robot.placement_observation で観測を差し替える（auto / none / 領域の ID）。
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from coground_server.eventlog import EventLog
from coground_server.executor import Executor
from coground_server.main import create_app
from coground_server.robot import FakeRobot

from test_task import call, request, scene, scene_json, step, store
from test_websocket import connect


class Rig:
    def __init__(self, observation: str = "auto", simulated: bool = True) -> None:
        self.state = store()
        self.task = request(self.state)
        self.robot = FakeRobot(phase_delay=0.0)
        self.robot.placement_observation = observation
        self.robot.simulated = simulated
        self.ex = Executor(self.state, self.robot, EventLog(), self._publish)

    async def _publish(self) -> None:
        pass

    @property
    def cup(self):
        return self.task.row("cup_B")

    def record(self) -> dict[str, str]:
        s = step(self.state, "cup_B")
        return self.ex.snapshot()["steps"][s.id] if s is not None else {}

    async def until(self, cond, timeout: float = 3.0) -> None:
        async def poll() -> None:
            while not cond():
                await asyncio.sleep(0.002)
        try:
            await asyncio.wait_for(poll(), timeout)
        except asyncio.TimeoutError:
            raise AssertionError(f"Condition never holds: {self.ex.snapshot()} / {self.task.model_dump()}")

    async def run_to_stop(self) -> None:
        await self.ex.start(allow_unplanned=True)
        await self.until(lambda: self.ex.mode != "running")


def run(coro) -> None:
    asyncio.run(coro)


def test_observed_in_lower_shelf_is_done():
    async def main() -> None:
        rig = Rig("auto")
        await rig.run_to_stop()
        assert (rig.ex.mode, rig.ex.reason) == ("idle", "finished")
        assert rig.cup.exec_state == "done"
        assert (rig.cup.verdicts["R3b"].value, rig.cup.verdicts["R3b"].basis) == ("compliant", "observed")
        assert rig.task.counts() == {"total": 2, "done": 1, "deferred": 1}
        await rig.ex.close()

    run(main())


def test_observed_in_upper_shelf_is_misplaced():
    async def main() -> None:
        rig = Rig("shelf_upper")
        await rig.run_to_stop()
        assert rig.ex.mode == "paused" and "Wrong placement" in rig.ex.reason
        assert rig.cup.exec_state == "misplaced" and "shelf_upper" in rig.cup.reason
        assert (rig.cup.verdicts["R3b"].value, rig.cup.verdicts["R3b"].basis) == ("violated", "observed")
        assert rig.task.counts() == {"total": 2, "done": 0, "deferred": 1, "misplaced": 1}
        assert rig.record()["status"] == "misplaced"

        # 同じシーンがもう一度届いても、配置先違いの記録は消えない。勝手にやり直しもしない
        rig.state.set_scene(rig.state.scene.model_copy())
        assert rig.cup.exec_state == "misplaced"
        await rig.ex.resume()
        await rig.until(lambda: rig.ex.mode != "running")
        assert (rig.ex.mode, rig.cup.exec_state) == ("idle", "misplaced")

        # やり直す（retry）と、今度は下段で観測されて収納済みになる
        rig.robot.placement_observation = "auto"
        await rig.ex.retry(step(rig.state, "cup_B").id)
        assert rig.cup.exec_state == "pending"
        await rig.run_to_stop()
        assert rig.cup.exec_state == "done" and rig.task.counts()["done"] == 1
        # 履歴には、予測と観測が別々に残る
        assert [(v.value, v.basis) for v in rig.cup.history if v.rule_id == "R3b"] == [
            ("compliant", "predicted"), ("violated", "observed"), ("compliant", "predicted"), ("compliant", "observed")]
        await rig.ex.close()

    run(main())


def test_no_observation_is_unverified_until_seen():
    async def main() -> None:
        rig = Rig("none")
        await rig.run_to_stop()
        assert rig.ex.mode == "paused" and "Couldn't observe" in rig.ex.reason
        assert rig.cup.exec_state == "unverified"
        v = rig.cup.verdicts["R3b"]
        assert (v.value, v.basis, [(m.entity_id, m.key) for m in v.missing]) == (
            "undetermined", "observed", [("cup_B", "object_region")])
        assert rig.task.counts() == {"total": 2, "done": 0, "deferred": 1, "unverified": 1}

        # あとから下段にあるのを観測したら、収納済みになる
        rig.state.set_scene(scene(cup_at="shelf_lower"))
        assert rig.cup.exec_state == "done" and rig.task.counts()["done"] == 1
        await rig.ex.close()

    run(main())


def test_place_success_waits_for_observation_from_unity():
    # 本物のロボットのとき: 置く動作が成功しても、Unity の scene.update が届くまでは観測待ち
    async def main() -> None:
        rig = Rig(simulated=False)
        rig.ex.observe_timeout = 2.0
        await rig.ex.start(allow_unplanned=True)
        await rig.until(lambda: rig.cup.exec_state == "placed_unverified")
        assert rig.record()["status"] == "placed_unverified" and rig.task.counts()["done"] == 0
        assert rig.ex.mode == "running"

        rig.state.set_scene(scene(cup_at="shelf_lower"))
        await rig.until(lambda: rig.ex.mode != "running")
        assert (rig.ex.mode, rig.cup.exec_state) == ("idle", "done")
        await rig.ex.close()

    run(main())


def test_unity_never_reports_is_unverified_after_timeout():
    async def main() -> None:
        rig = Rig(simulated=False)
        rig.ex.observe_timeout = 0.1
        await rig.run_to_stop()
        assert rig.cup.exec_state == "unverified" and rig.ex.mode == "paused"
        await rig.ex.close()

    run(main())


def test_failed_place_marks_row_failed():
    async def main() -> None:
        rig = Rig()
        rig.robot.inject_failure("place", "dropped it")
        await rig.run_to_stop()
        assert (rig.cup.exec_state, rig.cup.reason) == ("failed", "dropped it")
        assert rig.task.counts()["done"] == 0
        await rig.ex.close()

    run(main())


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


def test_debug_observe_placement_over_websocket(client):
    with connect(client) as (ws, _w, _s):
        call(ws, "1", "scene.update", scene_json())
        assert call(ws, "2", "debug.observe_placement", {"mode": "shelf_upper"})["result"] == {"mode": "shelf_upper"}
        assert call(ws, "3", "debug.observe_placement", {"mode": "nope"})["error"]["code"] == "invalid_params"
        assert call(ws, "4", "debug.observe_placement", {"mode": "none"})["ok"]
