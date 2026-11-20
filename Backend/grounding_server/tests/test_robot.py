"""RosbridgeRobot（rosbridge 経由で pick_place_server と話す側）。相手は、ここで立てる偽の rosbridge。"""

from __future__ import annotations

import asyncio
import json

import websockets

from coground_server.robot import RosbridgeRobot


class FakeRosbridge:
    """rosbridge と pick_place_server の代わり。goal が来たら accepted -> running -> 結果 を返す。"""

    def __init__(self, result: str = "succeeded", hold_until_cancel: bool = False) -> None:
        self.result = result
        self.hold_until_cancel = hold_until_cancel
        self.ops: list[dict] = []
        self.goals: list[dict] = []
        self.canceled = asyncio.Event()

    async def handler(self, ws) -> None:
        async def pub(topic: str, data: dict) -> None:
            await ws.send(json.dumps({"op": "publish", "topic": topic, "msg": {"data": json.dumps(data)}}))

        await pub("/coground/skill/state", {"busy": False, "goal_id": None, "holding": None})
        async for raw in ws:
            msg = json.loads(raw)
            self.ops.append(msg)
            if msg["op"] != "publish":
                continue
            data = json.loads(msg["msg"]["data"])
            if msg["topic"] == "/coground/system/reset":
                self.canceled.set()
                await pub("/coground/system/reset_result", {"reset_id": "someone-else", "ok": False})  # 無視される
                await pub("/coground/system/reset_result", {"reset_id": data["reset_id"], "ok": True, "detail": ""})
            elif msg["topic"] == "/coground/skill/cancel":
                self.canceled.set()
                await pub("/coground/skill/feedback", {"goal_id": data["goal_id"], "state": "canceled", "detail": "stopped", "holding": None})
            elif msg["topic"] == "/coground/skill/goal":
                self.goals.append(data)
                gid = data["goal_id"]
                await pub("/coground/skill/feedback", {"goal_id": "someone-else", "state": "failed", "holding": None})  # 無視される
                await pub("/coground/skill/feedback", {"goal_id": gid, "state": "accepted", "holding": None})
                await pub("/coground/skill/feedback", {"goal_id": gid, "state": "running", "phase": "approaching", "detail": "", "holding": None})
                if not self.hold_until_cancel:
                    holding = data["object"] if data["skill"] == "pick" and self.result == "succeeded" else None
                    await pub("/coground/skill/feedback", {"goal_id": gid, "state": self.result, "detail": "d", "holding": holding})


async def _connected(robot: RosbridgeRobot) -> None:
    for _ in range(500):
        if robot.connected:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("Can't connect")


def test_run_skill_over_rosbridge():
    async def main():
        fake = FakeRosbridge()
        async with websockets.serve(fake.handler, "127.0.0.1", 0) as server:
            robot = RosbridgeRobot(f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}")
            await robot.start()
            try:
                await _connected(robot)
                phases = []
                place = {"position": [1.0, 2.0, 3.0], "orientation": [0.0, 0.0, 0.0, 1.0]}
                result = await robot.run_skill("pick", "BoxA", place, lambda phase, detail: phases.append(phase))
                assert (result.state, result.detail) == ("succeeded", "d")
                assert phases == ["approaching"] and robot.holding == "BoxA"
                goal = fake.goals[0]
                assert (goal["skill"], goal["object"], goal["frame_id"], goal["place"]) == ("pick", "BoxA", "world", place)
                ops = [(m["op"], m["topic"]) for m in fake.ops if m["op"] != "publish"]
                assert ("advertise", "/coground/skill/goal") in ops and ("subscribe", "/coground/skill/feedback") in ops
            finally:
                await robot.close()
    asyncio.run(main())


def test_reset_over_rosbridge_ends_running_skill():
    async def main():
        fake = FakeRosbridge(hold_until_cancel=True)
        async with websockets.serve(fake.handler, "127.0.0.1", 0) as server:
            robot = RosbridgeRobot(f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}")
            await robot.start()
            try:
                await _connected(robot)
                skill = asyncio.create_task(robot.run_skill("pick", "BoxA"))
                for _ in range(500):
                    if fake.goals:
                        break
                    await asyncio.sleep(0.01)
                ok, detail = await robot.reset()
                assert (ok, detail) == (True, "")
                # 動いていたスキルは、ROS の返事を待たずに canceled で終わる
                assert (await skill).state == "canceled"
            finally:
                await robot.close()
    asyncio.run(main())


def test_cancel_over_rosbridge():
    async def main():
        fake = FakeRosbridge(hold_until_cancel=True)
        async with websockets.serve(fake.handler, "127.0.0.1", 0) as server:
            robot = RosbridgeRobot(f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}")
            await robot.start()
            try:
                await _connected(robot)
                task = asyncio.create_task(robot.run_skill("pick", "BoxA"))
                await asyncio.sleep(0.05)
                await robot.cancel()
                result = await asyncio.wait_for(task, 2.0)
                assert result.state == "canceled" and fake.canceled.is_set()
            finally:
                await robot.close()
    asyncio.run(main())


def test_not_connected_fails_fast():
    async def main():
        robot = RosbridgeRobot("ws://127.0.0.1:9")  # start していない
        result = await robot.run_skill("pick", "BoxA")
        assert result.state == "failed" and "Not connected" in result.detail
    asyncio.run(main())


class FakePlanner(FakeRosbridge):
    """plan_request が来たら、途中経過を 1 つ出してから結果を返す。"""

    async def handler(self, ws) -> None:
        async def pub(topic: str, data: dict) -> None:
            await ws.send(json.dumps({"op": "publish", "topic": topic, "msg": {"data": json.dumps(data)}}))

        await pub("/coground/skill/state", {"busy": False, "goal_id": None, "holding": None})
        async for raw in ws:
            msg = json.loads(raw)
            self.ops.append(msg)
            if msg["op"] == "publish" and msg["topic"] == "/coground/task/plan_request":
                req = json.loads(msg["msg"]["data"])
                self.goals.append(req)
                key = {"plan_id": req["plan_id"], "plan_version": req["plan_version"]}
                await pub("/coground/task/plan_result", {"plan_id": "old", "plan_version": 1, "error": "", "steps": []})  # 無視される
                await pub("/coground/task/plan_feedback", {**key, "step_id": "s1", "detail": "pick: stop position 1/8"})
                await pub("/coground/task/plan_result", {**key, "error": "", "steps": [{"step_id": "s1", "status": "ok"}],
                                                         "timeline": {"duration": 1.0}})


def test_plan_motion_over_rosbridge():
    async def main():
        fake = FakePlanner()
        async with websockets.serve(fake.handler, "127.0.0.1", 0) as server:
            robot = RosbridgeRobot(f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}")
            await robot.start()
            try:
                await _connected(robot)
                progress = []

                async def on_progress(d):
                    progress.append(d["detail"])

                result = await robot.plan_motion({"plan_id": "plan_1", "plan_version": 3, "steps": []}, on_progress)
                assert result["error"] == "" and result["timeline"] == {"duration": 1.0}
                assert fake.goals[0]["plan_version"] == 3
                await asyncio.sleep(0.05)
                assert progress == ["pick: stop position 1/8"]
            finally:
                await robot.close()
    asyncio.run(main())
