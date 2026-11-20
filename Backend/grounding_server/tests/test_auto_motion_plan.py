"""依頼（task.request）のあと、自動で動作計画（motion.plan）を始める（Services.start_auto_motion_plan）。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from coground_server.eventlog import EventLog
from coground_server.models import Rule, SceneSnapshot
from coground_server.robot import FakeRobot
from coground_server.services import Services
from coground_server.state import StateStore

SCENARIO = json.loads((Path(__file__).parent / "fixtures" / "shelf_scenario.json").read_text())


def make(auto: bool = True) -> Services:
    state = StateStore()
    state.set_scene(SceneSnapshot.model_validate(SCENARIO["initial_scene"]))
    state.set_rules([Rule.model_validate(r) for r in SCENARIO["rules"]])
    return Services(state=state, robot=FakeRobot(), events=EventLog(), auto_motion_plan=auto)


def test_request_starts_motion_plan():
    async def go():
        s = make()
        s.state.open_task("tidy", [o.id for o in s.state.scene.objects if o.role == "item"])
        assert s.start_auto_motion_plan()
        await asyncio.wait_for(s._auto_task, 5)
        assert s.motion.status == "ready"
        assert s.motion.summary()["steps"]  # step ごとの結果がある
    asyncio.run(go())


def test_disabled_or_nothing_to_plan():
    async def go():
        assert not make(auto=False).start_auto_motion_plan()
        s = make()
        s.state.set_rules([])  # 行き先が無ければ ok の step が無い
        assert not s.start_auto_motion_plan()
    asyncio.run(go())
