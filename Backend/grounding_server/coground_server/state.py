"""サーバーが持つ全体状態（シーン、ルール、計画）。データの型は models.py。

状態が変わるたびに version を 1 増やし、全体を state.updated で全クライアントに送る。
差分は送らないので、取りこぼしても次の state.updated（または state.get）で最新に戻れる。

座標はすべて Unity のワールド座標（メートル、左手系、Y 上）。物体 ID は Unity が決め、
MoveIt の collision object 名と揃える。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import Plan, Quat, Rule, SceneObject, SceneRegion, SceneSnapshot, Vec3

__all__ = ["Plan", "Quat", "Rule", "SceneObject", "SceneRegion", "SceneSnapshot", "StateStore", "Vec3"]


class StateStore:
    def __init__(self) -> None:
        self._version = 0
        self._updated_at: str | None = None
        self._scene = SceneSnapshot()
        self._rules: list[Rule] = []
        self._plan: Plan | None = None  # まだ計画が無ければ None

    @property
    def version(self) -> int:
        return self._version

    @property
    def scene(self) -> SceneSnapshot:
        return self._scene

    @property
    def rules(self) -> list[Rule]:
        return self._rules

    @property
    def plan(self) -> Plan | None:
        return self._plan

    def snapshot(self) -> dict[str, Any]:
        return {
            "version": self._version,
            "updated_at": self._updated_at,
            "scene": self._scene.model_dump(mode="json"),
            "rules": [r.model_dump(mode="json") for r in self._rules],
            "plan": self._plan.model_dump(mode="json") if self._plan else None,
        }

    def set_scene(self, scene: SceneSnapshot) -> int:
        self._scene = scene
        return self._bump()

    def set_rules(self, rules: list[Rule]) -> int:
        self._rules = list(rules)
        return self._bump()

    def set_plan(self, plan: Plan | None) -> int:
        self._plan = plan
        return self._bump()

    def _bump(self) -> int:
        self._version += 1
        self._updated_at = datetime.now(timezone.utc).isoformat()
        return self._version
