"""ロボットを使う窓口。Executor（executor.py）と MotionStore（motion.py）が使う。

    result = await robot.run_skill("navigate", "BoxA", pose=[x, y, yaw])             # 台車を動かす
    result = await robot.run_skill("pick", "BoxA", on_phase=..., plan_ref={...})      # 終わるまで待つ
    result = await robot.run_skill("place", "BoxA", place={...}, plan_ref={...})      # place を省くと、つかんだ元の場所へ戻す
    await robot.cancel()                                                              # 実行中のスキルを止める（canceled で返る）
    result = await robot.plan_motion(request, on_progress)                            # 動かさずに一連の動きを計画する

家庭ルール（領域への進入の禁止、子供が近くにいる間は台車を止める）のために、台車について次のものがある:
    robot.base_pose / robot.base_speed      台車の位置 [x, y, yaw] と速さ（分からなければ None）
    robot.nav_goal                          台車を動かすスキル（navigate）の行き先。動かしていなければ None
    await robot.hold(reason)                台車を止めておく（スキルは取り消さない。腕は止めない）
    await robot.release(keepout_zones)      hold を解く。keepout_zones を渡すと、その範囲を避ける経路に替えてから続ける
    await robot.plan_route(goal, keepout)   いまの位置から goal までの経路だけを計画する（hold のあとの再検証に使う）
    run_skill(..., keepout_zones=[...])     navigate のとき、その範囲を避ける
    plan_motion の request["keepout_zones"] 計画でも同じ範囲を避ける
keepout_zones は [{"id": "zone_play", "polygon": [[x, y], ...]}]（ROS の world）。空のリストは「避ける範囲なし」。

plan_ref = {"plan_id", "plan_version", "step_id"} を付けると、plan_motion で計画した軌道を使う
（台車がぴったり止まり、今のシーンでもぶつからなければ、計画どおりに再生する。だめならその場で計画し直す）。
結果の mode に replay / replanned が入る。

実装は 2 つ:
  RosbridgeRobot  ROS の pick_place_server.py と rosbridge（WebSocket、:9090）で話す。
                  トピックは /coground/skill/*（実行）と /coground/task/*（計画）。中身は std_msgs/String の JSON
  FakeRobot       ROS なしで動く代役。phase を順に進め、計画は直線で動くだけの時間軸を作る。
                  テストと、Unity / ROS を立ち上げない実験に使う。失敗をわざと起こせる（fail_next）

どちらを使うかは環境変数で決める（make_robot）:
  COGROUND_ROSBRIDGE_URL=ws://<ROS のホスト>:9090  があれば RosbridgeRobot、無ければ FakeRobot
  COGROUND_FAKE_PHASE_DELAY=0.4                     FakeRobot が phase 1 つにかける秒

座標: ここでやりとりする位置はすべて ROS の座標（右手系、Z 上、frame world = Unity の World）。
Unity の座標とは unity_pose_to_ros / unity_to_ros で変換する。
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .models import Pose
from .norms.geometry import FOOTPRINT_RADIUS, Point, polygon_distance, route_around

log = logging.getLogger(__name__)

PICK_PHASES = ("opening", "approaching", "descending", "grasping", "lifting")
PLACE_PHASES = ("moving", "lowering", "releasing", "retreating")
TERMINAL = ("succeeded", "failed", "canceled", "rejected")
PLAN_TIMEOUT = 180.0  # 計画を待つ秒

PhaseCallback = Callable[[str, str], None]  # (phase, detail)
ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class SkillResult:
    state: str  # succeeded / failed / canceled / rejected
    detail: str = ""
    mode: str | None = None  # plan_ref を付けたとき: replay / replanned

    @property
    def ok(self) -> bool:
        return self.state == "succeeded"


def unity_to_ros(p: tuple[float, float, float] | list[float]) -> list[float]:
    return [p[2], -p[0], p[1]]


def ros_to_unity(p: list[float]) -> list[float]:
    return [-p[1], p[2], p[0]]


def unity_pose_to_ros(pose: Pose) -> dict[str, list[float]]:
    """Unity（左手系、Y 上）-> ROS（右手系、Z 上）。Unity の To<FLU>() と同じ。"""
    qx, qy, qz, qw = pose.rotation
    return {"position": unity_to_ros(pose.position), "orientation": [qz, -qx, qy, -qw]}


class Robot:
    kind = "none"
    simulated = False  # True なら、置いた結果を Executor がサーバーのシーンに書き込む（Unity がいないので）

    def __init__(self) -> None:
        self.connected = False
        self.holding: str | None = None
        self.busy = False
        self.on_change: Callable[[], None] | None = None  # connected / holding / busy が変わったら呼ばれる
        self._goal_id: str | None = None
        self.held = False            # hold 中（家庭ルールにより台車を止めている）
        self.hold_reason = ""
        self.nav_goal: list[float] | None = None   # 台車を動かすスキルの行き先 [x, y, yaw]
        self.nav_object: str | None = None         # そのスキルが運んでいる（取りに行く）物体
        self.next_point: list[float] | None = None  # 次に進む点（分かるロボットだけ。進む向きを知るのに使う）
        self.keepout: list[dict[str, Any]] = []    # いま避けている範囲

    async def start(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def run_skill(
        self, skill: str, object_id: str, place: dict[str, Any] | None = None, on_phase: PhaseCallback | None = None,
        *, pose: list[float] | None = None, plan_ref: dict[str, Any] | None = None,
        keepout_zones: list[dict[str, Any]] | None = None,
    ) -> SkillResult:
        raise NotImplementedError

    async def cancel(self) -> None:
        raise NotImplementedError

    @property
    def base_pose(self) -> list[float] | None:
        """台車の位置 [x, y, yaw]（ROS の world）。分からなければ None"""
        return None

    @property
    def base_speed(self) -> float | None:
        return None

    async def hold(self, reason: str = "") -> None:
        raise NotImplementedError

    async def release(self, keepout_zones: list[dict[str, Any]] | None = None) -> None:
        raise NotImplementedError

    async def plan_route(self, goal: list[float], keepout_zones: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """いまの位置から goal = [x, y, yaw] までの経路。{"ok", "reason", "base": [[t, x, y, yaw], ...]}（t は今からの秒）"""
        raise NotImplementedError

    async def reset(self) -> tuple[bool, str]:
        """まっさらにする（system.reset）: 動いていれば止め、持っている物・計画を忘れ、腕を初期姿勢へ戻す。(ok, 理由)"""
        raise NotImplementedError

    async def plan_motion(self, request: dict[str, Any], on_progress: ProgressCallback | None = None) -> dict[str, Any]:
        """request（pick_place_server.py の /coground/task/plan_request と同じ形）を計画した結果を返す。"""
        raise NotImplementedError

    def snapshot(self) -> dict[str, Any]:
        return {"kind": self.kind, "connected": self.connected, "holding": self.holding, "busy": self.busy,
                "held": self.held, "hold_reason": self.hold_reason, "base": self.base_pose,
                "keepout": [z.get("id") for z in self.keepout]}

    def _changed(self) -> None:
        if self.on_change is not None:
            self.on_change()


# ---------------------------------------------------------------- ROS なしの代役


class FakeRobot(Robot):
    kind = "fake"
    simulated = True
    STANDOFF = 0.6     # 物体の手前で止まる距離 [m]
    LINEAR = 0.4       # 計画の時間軸での台車の速さ [m/s]
    ANGULAR = 0.8      # [rad/s]
    ARM_PHASE = 1.0    # 腕の phase 1 つの長さ [s]
    NAV_STEP = 0.1     # navigate で 1 回に進む距離 [m]（進むたびに、家庭ルールの監視が入る）
    CLEARANCE = FOOTPRINT_RADIUS + 0.05  # 避ける範囲から台車の中心を離す距離 [m]
    STOP_ANGLES = (0, 45, -45, 90, -90, 135, -135, 180)  # 止まる位置の候補（物体のまわり、手前から）[度]
    GRIPPER_HALF = 0.06  # つかむとき、手の通り道の半分の幅 [m]（手前にある物がこれより近いと、つかめない）

    def __init__(self, phase_delay: float = 0.4) -> None:
        super().__init__()
        self.connected = True
        self.phase_delay = phase_delay
        self.base = [0.0, 0.0, 0.0]  # 台車の位置 [x, y, yaw]（ROS の world）
        self.fail_next: list[dict[str, str]] = []  # {"skill": "pick" | "place" | "", "detail": "..."}。先頭から 1 つずつ使う
        self.infeasible: set[str] = set()           # 計画で infeasible にする物体
        # 床の障害物（ROS の world の多角形 [[x, y], ...]）。台車はこれを避ける。本物では Unity の地図（NavMapPublisher）が担う
        self.obstacles: list[list[list[float]]] = []
        # 置いたあとの「配置先の観測」をどう返すか（Unity がいないので、Executor がこれを見てシーンを書く）。
        #   "auto"  計画した置き先で観測される / "none"  観測が来ない / 領域の ID  その領域で観測される（配置先違い）
        self.placement_observation = "auto"
        self._cancel = asyncio.Event()
        # 台車を 1 歩進める前に呼ぶ（Executor が家庭ルールの監視を入れる。monitor.py の Monitor.gate）
        self.gate: Callable[[], Awaitable[None]] | None = None
        self.speed = 0.0
        self._released = asyncio.Event()
        self._released.set()
        self._reroute = False  # hold の間に避ける範囲が変わった（経路を作り直す）
        self.base_log: list[list[float]] = []  # navigate で通った位置（テストで確かめる）

    @property
    def base_pose(self) -> list[float] | None:
        return list(self.base)

    @property
    def base_speed(self) -> float | None:
        return self.speed

    async def hold(self, reason: str = "") -> None:
        self.held, self.hold_reason, self.speed = True, reason, 0.0
        self._released.clear()
        self._changed()

    async def release(self, keepout_zones: list[dict[str, Any]] | None = None) -> None:
        if keepout_zones is not None and keepout_zones != self.keepout:
            self.keepout, self._reroute = list(keepout_zones), True
        self.held, self.hold_reason = False, ""
        self._released.set()
        self._changed()

    def _polygons(self, zones: list[dict[str, Any]]) -> list[list[Point]]:
        """台車が避ける範囲: 進入禁止の領域と、床の障害物"""
        return ([[(float(p[0]), float(p[1])) for p in z["polygon"]] for z in zones]
                + [[(float(p[0]), float(p[1])) for p in poly] for poly in self.obstacles])

    def _route(self, start: Point, goal: Point, zones: list[dict[str, Any]]) -> list[Point] | None:
        return route_around(start, goal, self._polygons(zones), self.CLEARANCE)

    async def plan_route(self, goal: list[float], keepout_zones: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        zones = self.keepout if keepout_zones is None else keepout_zones
        x, y, yaw = self.base
        points = self._route((x, y), (goal[0], goal[1]), zones)
        if points is None:
            return {"ok": False, "reason": "No path that avoids the no-entry areas", "base": []}
        t, track = 0.0, [[0.0, x, y, yaw]]
        for px, py in points[1:]:
            heading = math.atan2(py - y, px - x)
            t += abs(math.atan2(math.sin(heading - yaw), math.cos(heading - yaw))) / self.ANGULAR
            track.append([round(t, 3), x, y, heading])
            t += math.hypot(px - x, py - y) / self.LINEAR
            x, y, yaw = px, py, heading
            track.append([round(t, 3), x, y, yaw])
        t += abs(math.atan2(math.sin(goal[2] - yaw), math.cos(goal[2] - yaw))) / self.ANGULAR
        track.append([round(t, 3), x, y, goal[2]])
        return {"ok": True, "reason": "", "base": track}

    async def _navigate(self, pose: list[float], object_id: str, on_phase: PhaseCallback | None,
                        keepout_zones: list[dict[str, Any]] | None) -> SkillResult:
        """折れ線の経路を NAV_STEP ずつ進む。進む前に gate（監視）を呼び、hold の間は待つ。"""
        if keepout_zones is not None:
            self.keepout = list(keepout_zones)
        self.busy = True
        self._cancel.clear()
        self.nav_goal, self.nav_object = list(pose), object_id
        self._changed()
        try:
            if on_phase is not None:
                on_phase("navigating", object_id)
            path: list[Point] | None = None
            delay = self.phase_delay
            while True:
                if path is None:
                    points = self._route((self.base[0], self.base[1]), (pose[0], pose[1]), self.keepout)
                    if points is None:
                        return SkillResult("failed", "No path that avoids the no-entry areas")
                    path = []
                    for a, b in zip(points, points[1:]):
                        n = max(1, math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / self.NAV_STEP - 1e-9))
                        path.extend((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(1, n + 1))
                    if math.hypot(pose[0] - self.base[0], pose[1] - self.base[1]) < 1e-6:
                        path = []
                    delay = self.phase_delay / max(1, len(path))  # 全体で phase 1 つ分の時間
                    self._reroute = False
                if not path:
                    break
                self.next_point, self.speed = list(path[0]), self.LINEAR
                if self.gate is not None:
                    await self.gate()
                while self.held and not self._cancel.is_set():
                    waits = [asyncio.ensure_future(self._cancel.wait()), asyncio.ensure_future(self._released.wait())]
                    _, pending = await asyncio.wait(waits, return_when=asyncio.FIRST_COMPLETED)
                    for w in pending:
                        w.cancel()
                if self._cancel.is_set():
                    return SkillResult("canceled", "stopped")
                if self._reroute:
                    path = None
                    continue
                nx, ny = path.pop(0)
                self.base = [nx, ny, math.atan2(ny - self.base[1], nx - self.base[0])]
                self.base_log.append(list(self.base))
                if await self._wait(delay):
                    return SkillResult("canceled", "stopped")
            if not self.base_log or self.base_log[-1][:2] != list(pose[:2]):
                if await self._wait(self.phase_delay):  # もうそこにいる
                    return SkillResult("canceled", "stopped")
            self.base = list(pose)
            return SkillResult("succeeded")
        finally:
            self.nav_goal, self.nav_object, self.next_point, self.speed = None, None, None, 0.0
            self.busy = False
            self._changed()

    def inject_failure(self, skill: str = "", detail: str = "Failed on purpose") -> None:
        """次に実行する skill（"" ならどれでも）を、途中の phase で失敗させる。"""
        self.fail_next.append({"skill": skill, "detail": detail})

    async def _wait(self, seconds: float | None = None) -> bool:
        """phase 1 つ分（または seconds）待つ。止められたら True"""
        try:
            await asyncio.wait_for(self._cancel.wait(), timeout=self.phase_delay if seconds is None else seconds)
            return True
        except asyncio.TimeoutError:
            return False

    async def run_skill(self, skill, object_id, place=None, on_phase=None, *, pose=None, plan_ref=None,
                        keepout_zones=None) -> SkillResult:
        if self.busy:
            return SkillResult("rejected", "busy")
        mode = "replay" if plan_ref is not None else None
        if skill == "navigate":
            if pose is None:
                return SkillResult("failed", "navigate requires pose")
            return await self._navigate(list(pose), object_id, on_phase, keepout_zones)
        if skill == "pick" and self.holding not in (None, object_id):
            return SkillResult("failed", f"Holding {self.holding}, so can't handle {object_id}")
        if skill == "place" and self.holding != object_id:
            return SkillResult("failed", f"Not holding {object_id}, so can't place it")
        if skill == "pick" and self.holding == object_id:
            return SkillResult("succeeded", mode=mode)

        failure = next((f for f in self.fail_next if f["skill"] in ("", skill)), None)
        if failure is not None:
            self.fail_next.remove(failure)
        phases = PICK_PHASES if skill == "pick" else PLACE_PHASES
        self.busy = True
        self._cancel.clear()
        self._changed()
        try:
            for i, phase in enumerate(phases):
                if on_phase is not None:
                    on_phase(phase, object_id)
                if await self._wait():
                    return SkillResult("canceled", "stopped")
                if failure is not None and i == 1:
                    return SkillResult("failed", failure["detail"])
                if phase == "grasping":
                    self.holding = object_id
                elif phase == "releasing":
                    self.holding = None
            return SkillResult("succeeded", mode=mode)
        finally:
            self.busy = False
            self._changed()

    async def cancel(self) -> None:
        self._cancel.set()

    async def reset(self) -> tuple[bool, str]:
        self._cancel.set()
        for _ in range(50):  # 動いているスキルが止まるのを待つ
            if not self.busy:
                break
            await asyncio.sleep(0.02)
        self.holding = None
        self.fail_next.clear()
        self.infeasible.clear()
        self.obstacles = []
        self.held, self.hold_reason, self.keepout, self._reroute = False, "", [], False
        self._released.set()
        self._changed()
        return True, ""

    async def plan_motion(self, request, on_progress=None) -> dict[str, Any]:
        """直線で動き、腕の phase は決まった長さの時間軸を作る（関節角は無い）。

        step は順に、前の step を終えた状態から計画する（計画できた step の物体は置き先へ移り、できなかった物は元の場所に残る）。
        request["world"]（シーンの物体。MotionStore が付ける）があれば、つかむ物の手前に、同じ場所の、背が同じか高い物があるとき
        つかめないことにする（結果の blocked_by に、じゃまな物体）。本物では MoveIt の衝突判定が担う。
        """
        if self.busy:
            return {"plan_id": request["plan_id"], "plan_version": request["plan_version"],
                    "error": "busy (the robot is moving)", "steps": [], "timeline": None}
        t = 0.0
        x, y, yaw = self.base
        base = [[0.0, x, y, yaw]]
        phases: list[dict[str, Any]] = []
        attached: list[dict[str, Any]] = []
        objects: list[dict[str, Any]] = []
        steps_out: list[dict[str, Any]] = []
        zones = request.get("keepout_zones") or []  # 避ける範囲（家庭ルールの進入禁止）
        polygons = self._polygons(zones)
        # 計画の中での物体の位置（step が進むたびに書き換える）
        world: dict[str, dict[str, Any]] = {w["id"]: dict(w) for w in request.get("world") or []}

        class Blocked(Exception):
            def __init__(self, reason: str, blocked_by: list[str] | None = None) -> None:
                super().__init__(reason)
                self.blocked_by = blocked_by or []

        def in_the_way(obj: str, stop: list[float]) -> list[str]:
            """stop から obj をつかむとき、手の通り道にある物体"""
            me = world.get(obj)
            if me is None:
                return []
            ax, ay = stop[0], stop[1]
            bx, by = me["position"][0], me["position"][1]
            length2 = (bx - ax) ** 2 + (by - ay) ** 2
            out = []
            for other in world.values():
                if other["id"] == obj or other.get("role") != "item" or other.get("region") != me.get("region"):
                    continue
                if other.get("height", 0.0) < me.get("height", 0.0) - 1e-6:
                    continue  # 背の低い物は、上から越えられる
                ox, oy = other["position"][0], other["position"][1]
                u = ((ox - ax) * (bx - ax) + (oy - ay) * (by - ay)) / length2 if length2 > 1e-9 else 0.0
                if not 0.0 < u < 1.0:
                    continue
                d = math.hypot(ox - (ax + u * (bx - ax)), oy - (ay + u * (by - ay)))
                if d < other.get("radius", 0.05) + self.GRIPPER_HALF:
                    out.append(other["id"])
            return out

        def drive(tx: float, ty: float, tyaw: float, sid: str) -> None:
            nonlocal t, x, y, yaw
            points = self._route((x, y), (tx, ty), zones)
            if points is None:
                raise Blocked("No path that avoids the no-entry areas")
            t0 = t
            for px, py in points[1:]:
                heading = math.atan2(py - y, px - x)
                t += abs(math.atan2(math.sin(heading - yaw), math.cos(heading - yaw))) / self.ANGULAR
                yaw = heading
                base.append([round(t, 3), x, y, yaw])
                t += math.hypot(px - x, py - y) / self.LINEAR
                x, y = px, py
                base.append([round(t, 3), x, y, yaw])
            t += abs(math.atan2(math.sin(tyaw - yaw), math.cos(tyaw - yaw))) / self.ANGULAR
            yaw = tyaw
            base.append([round(t, 3), x, y, yaw])
            phases.append({"step_id": sid, "phase": "navigating", "t0": round(t0, 3), "t1": round(t, 3)})

        def go_to_stop(target: list[float], fixed: list[list[float]], sid: str, grasp: str | None = None) -> tuple[list[float], str]:
            """止まる位置を選んで、そこまで移動する。(止まった位置, 出どころ approach / auto)。

            家具に決めてある位置（fixed。目標に近い順）を先に試し、だめなら物体の手前 STANDOFF の位置を角度を変えて探す。
            grasp（つかむ物体）があれば、手の通り道がふさがっている位置は使わない。
            """
            th0 = math.atan2(target[1] - y, target[0] - x)
            candidates = [(list(p), "approach") for p in sorted(fixed, key=lambda p: math.hypot(p[0] - target[0], p[1] - target[1]))]
            if not fixed:
                for a in self.STOP_ANGLES:
                    th = th0 + math.radians(a)
                    candidates.append(([target[0] - self.STANDOFF * math.cos(th), target[1] - self.STANDOFF * math.sin(th), th], "auto"))
            reasons: list[str] = []
            blockers: list[str] = []
            for stop, source in candidates:
                if source == "auto" and any(polygon_distance((stop[0], stop[1]), poly) < self.CLEARANCE for poly in polygons):
                    reasons.append("Every stop position falls inside a no-entry area")
                    continue
                hit = in_the_way(grasp, stop) if grasp else []
                if hit:
                    blockers.extend(h for h in hit if h not in blockers)
                    reasons.append(f"{', '.join(hit)} is in the way of grasping {grasp}")
                    continue
                if self._route((x, y), (stop[0], stop[1]), zones) is None:
                    reasons.append("No path that avoids the no-entry areas")
                    if source == "auto":
                        break  # 自動で選んだ位置は、通れなければそこまで（遠回りの位置までは探さない）
                    continue
                drive(*stop, sid)
                return stop, source
            # 手の通り道がふさがっていた候補があれば、それを理由にする（順序を変えれば解けるので）
            grasp_reason = next((r for r in reasons if "in the way" in r), None)
            raise Blocked(grasp_reason or (reasons[-1] if reasons else "No stop position"), blockers if grasp_reason else [])

        for s in request["steps"]:
            sid, obj = s["step_id"], s.get("object") or ""
            kind = s.get("kind") or "pick_place"
            if on_progress is not None:
                await on_progress({"step_id": sid, "detail": "planning"})
            saved = (t, x, y, yaw, len(base), len(phases), len(attached))
            try:
                if kind == "navigate":  # 台車の移動だけ（単体テスト）
                    t_start = t
                    pose = list(s["pose"])
                    drive(*pose, sid)
                    steps_out.append({"step_id": sid, "object": obj, "status": "ok", "reason": "", "t0": round(t_start, 3),
                                      "t1": round(t, 3), "stops": {"navigate": pose}, "stop_source": {"navigate": "goal"}})
                    continue
                if obj in self.infeasible or s.get("start") is None:
                    reason = "Made unplannable on purpose" if obj in self.infeasible else "Object position unknown"
                    steps_out.append({"step_id": sid, "object": obj, "status": "infeasible", "reason": reason,
                                      "t0": round(t, 3), "t1": round(t, 3), "stops": {}})
                    continue
                t_start = t
                approach = s.get("approach") or {}
                if kind == "pick" and s.get("stay"):  # その場でつかむだけ（単体テスト）
                    pick_stop, source = [x, y, yaw], {"pick": "stay"}
                else:
                    source = {}
                    here = world.get(obj, {}).get("position") or s["start"]["position"]
                    pick_stop, source["pick"] = go_to_stop(list(here), approach.get("pick") or [], sid, grasp=obj)
                for phase in PICK_PHASES:
                    phases.append({"step_id": sid, "phase": phase, "t0": round(t, 3), "t1": round(t + self.ARM_PHASE, 3)})
                    t += self.ARM_PHASE
                    if phase == "grasping":
                        attached.append({"object": obj, "t0": round(t, 3), "t1": None, "link": "gripper_link",
                                         "pose": {"position": [0.0, 0.0, 0.0], "orientation": [0.0, 0.0, 0.0, 1.0]}})
                if kind == "pick":
                    attached[-1]["t1"] = None  # 持ったまま終わる（下で duration にする）
                    objects.append({"object": obj, "start": s["start"], "rest": s["start"]})
                    steps_out.append({"step_id": sid, "object": obj, "status": "ok", "reason": "", "t0": round(t_start, 3),
                                      "t1": round(t, 3), "stops": {"pick": pick_stop}, "stop_source": source})
                    continue
                place_stop, source["place"] = go_to_stop(list(s["place"]["position"]), approach.get("place") or [], sid)
                for phase in PLACE_PHASES:
                    phases.append({"step_id": sid, "phase": phase, "t0": round(t, 3), "t1": round(t + self.ARM_PHASE, 3)})
                    t += self.ARM_PHASE
                    if phase == "releasing":
                        attached[-1]["t1"] = round(t, 3)
                objects.append({"object": obj, "start": s["start"], "rest": s.get("rest") or s["place"]})
                if obj in world:  # 次の step は、この物体が置き先にある状態から計画する
                    world[obj]["position"] = list((s.get("rest") or s["place"])["position"])
                    world[obj]["region"] = s.get("to_region")
                steps_out.append({"step_id": sid, "object": obj, "status": "ok", "reason": "", "t0": round(t_start, 3),
                                  "t1": round(t, 3), "stops": {"pick": pick_stop, "place": place_stop}, "stop_source": source})
            except Blocked as e:
                # その step は動かなかったものとして、次の step を続ける
                t, x, y, yaw = saved[:4]
                del base[saved[4]:], phases[saved[5]:], attached[saved[6]:]
                steps_out.append({"step_id": sid, "object": obj, "status": "infeasible", "reason": str(e),
                                  "t0": round(t, 3), "t1": round(t, 3), "stops": {}, "blocked_by": list(e.blocked_by)})
        base.append([round(t, 3), x, y, yaw])
        for a in attached:
            if a["t1"] is None:
                a["t1"] = round(t, 3)
        return {"plan_id": request["plan_id"], "plan_version": request["plan_version"], "error": "",
                "steps": steps_out,
                "timeline": {"duration": round(t, 3), "base": base, "joint_names": [], "joints": [[0.0]],
                             "attached": attached, "phases": phases, "objects": objects}}


# ---------------------------------------------------------------- ROS（rosbridge）


class RosbridgeRobot(Robot):
    kind = "rosbridge"
    ACCEPT_TIMEOUT = 5.0  # goal を送ってから accepted が届くまで待つ秒
    RESET_TIMEOUT = 60.0  # リセット（腕を初期姿勢へ戻すまで）を待つ秒
    ROUTE_TIMEOUT = 15.0  # 経路だけの計画（plan_route）を待つ秒
    BASE_STALE = 2.0      # 台車の位置がこの秒数届かなければ、分からない扱いにする
    TOPICS_OUT = ("/coground/skill/goal", "/coground/skill/cancel", "/coground/task/plan_request", "/coground/system/reset",
                  "/coground/skill/hold", "/coground/nav/route_request")
    TOPICS_IN = ("/coground/skill/feedback", "/coground/skill/state", "/coground/task/plan_feedback",
                 "/coground/task/plan_result", "/coground/system/reset_result", "/coground/nav/route_result")
    BASE_POSE_TOPIC = "/unity/base_pose"  # geometry_msgs/PoseStamped。world から見た base_link（fake_base_driver などが出す）

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url
        self._ws: Any = None
        self._task: asyncio.Task[None] | None = None
        self._result: asyncio.Future[SkillResult] | None = None
        self._accepted = asyncio.Event()
        self._on_phase: PhaseCallback | None = None
        self._plan_key: tuple[str, int] | None = None
        self._plan_result: asyncio.Future[dict[str, Any]] | None = None
        self._plan_progress: ProgressCallback | None = None
        self._background: set[asyncio.Task[Any]] = set()
        self._reset_id: str | None = None
        self._reset_result: asyncio.Future[dict[str, Any]] | None = None
        self._base: list[float] | None = None   # [x, y, yaw]
        self._base_at = 0.0                     # 届いた時刻（time.monotonic）
        self._speed: float | None = None
        self._route_id: str | None = None
        self._route_result: asyncio.Future[dict[str, Any]] | None = None

    @property
    def base_pose(self) -> list[float] | None:
        return list(self._base) if self._base is not None and time.monotonic() - self._base_at <= self.BASE_STALE else None

    @property
    def base_speed(self) -> float | None:
        return self._speed if self.base_pose is not None else None

    def _on_base_pose(self, msg: dict[str, Any]) -> None:
        try:
            p, q = msg["pose"]["position"], msg["pose"]["orientation"]
            yaw = math.atan2(2.0 * (q["w"] * q["z"] + q["x"] * q["y"]), 1.0 - 2.0 * (q["y"] * q["y"] + q["z"] * q["z"]))
            pose = [float(p["x"]), float(p["y"]), yaw]
        except (KeyError, TypeError, ValueError):
            return
        now = time.monotonic()
        if self._base is not None and 0.0 < now - self._base_at < 1.0:
            self._speed = math.hypot(pose[0] - self._base[0], pose[1] - self._base[1]) / (now - self._base_at)
        self._base, self._base_at = pose, now

    async def hold(self, reason: str = "") -> None:
        self.held, self.hold_reason = True, reason
        await self._publish("/coground/skill/hold", {"hold": True, "reason": reason})
        self._changed()

    async def release(self, keepout_zones: list[dict[str, Any]] | None = None) -> None:
        if keepout_zones is not None:
            self.keepout = list(keepout_zones)
        self.held, self.hold_reason = False, ""
        await self._publish("/coground/skill/hold", {"hold": False, "keepout_zones": keepout_zones})
        self._changed()

    async def plan_route(self, goal: list[float], keepout_zones: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if not self.connected:
            return {"ok": False, "reason": self.not_connected_reason(), "base": []}
        if self._route_id is not None:
            return {"ok": False, "reason": "busy (planning a path)", "base": []}
        self._route_id = uuid.uuid4().hex[:12]
        self._route_result = asyncio.get_running_loop().create_future()
        try:
            request = {"route_id": self._route_id, "goal": list(goal), "keepout_zones": keepout_zones}
            if not await self._publish("/coground/nav/route_request", request):
                return {"ok": False, "reason": "Couldn't ask the robot to plan a path", "base": []}
            try:
                return await asyncio.wait_for(self._route_result, timeout=self.ROUTE_TIMEOUT)
            except asyncio.TimeoutError:
                return {"ok": False, "reason": f"No path returned after waiting {self.ROUTE_TIMEOUT:.0f} s", "base": []}
        finally:
            self._route_id, self._route_result = None, None

    async def start(self) -> None:
        log.info("robot: ROS（rosbridge %s）を使う。pick_place_server の返事を待つ", self.url)
        self._task = asyncio.create_task(self._connect_loop(), name="rosbridge")
        asyncio.get_running_loop().call_later(10.0, self._warn_if_silent)

    def not_connected_reason(self) -> str:
        if self._ws is None:
            return f"Not connected to the robot: can't reach rosbridge ({self.url}). Was ROS started with ROSBRIDGE=true, and is the URL right?"
        return "Not connected to the robot: connected to rosbridge, but no reply from pick_place_server (was it started together with MoveIt?)"

    def _warn_if_silent(self) -> None:
        if not self.connected:
            log.warning("rosbridge: 10 秒たっても pick_place_server から返事が無い（%s。ROS は ROSBRIDGE=true で起動したか）",
                        "rosbridge にはつながった" if self._ws is not None else f"{self.url} につながらない")

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    async def _connect_loop(self) -> None:
        import websockets  # uvicorn[standard] と一緒に入る

        while True:
            try:
                async with websockets.connect(self.url, max_size=None) as ws:
                    for topic in self.TOPICS_OUT:
                        await ws.send(json.dumps({"op": "advertise", "topic": topic, "type": "std_msgs/String"}))
                    for topic in self.TOPICS_IN:
                        await ws.send(json.dumps({"op": "subscribe", "topic": topic, "type": "std_msgs/String"}))
                    await ws.send(json.dumps({"op": "subscribe", "topic": self.BASE_POSE_TOPIC,
                                              "type": "geometry_msgs/PoseStamped", "throttle_rate": 100, "queue_length": 1}))
                    self._ws = ws
                    # サーバーを起動し直したとき、ROS 側に前の hold が残らないようにする
                    await self._publish("/coground/skill/hold", {"hold": self.held, "reason": self.hold_reason})
                    log.info("rosbridge: connected to %s", self.url)
                    # connected は、pick_place_server の state が届いてから True にする（_on_message）
                    async for raw in ws:
                        self._on_message(raw)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if self.connected or self._ws is not None:
                    log.warning("rosbridge: %s: %s", self.url, e)
                else:
                    log.debug("rosbridge: %s: %s", self.url, e)
            finally:
                self._ws = None
                if self.connected:
                    log.warning("rosbridge: disconnected from %s", self.url)
                self.connected = False
                self.busy = False
                self._finish(SkillResult("failed", "Connection to the robot was lost"))
                if self._plan_result is not None and not self._plan_result.done():
                    self._plan_result.set_exception(ConnectionError("Connection to the robot was lost"))
                self._changed()
            await asyncio.sleep(2.0)

    def _on_message(self, raw: str | bytes) -> None:
        try:
            msg = json.loads(raw)
            if msg.get("op") != "publish":
                return
            if msg.get("topic") == self.BASE_POSE_TOPIC:
                self._on_base_pose(msg.get("msg") or {})
                return
            data = json.loads(msg["msg"]["data"])
        except (ValueError, KeyError, TypeError):
            return
        topic = msg.get("topic")
        if topic == "/coground/nav/route_result":
            if self._route_result is not None and not self._route_result.done() and data.get("route_id") == self._route_id:
                self._route_result.set_result({"ok": bool(data.get("ok")), "reason": str(data.get("reason") or ""),
                                               "base": data.get("base") or []})
            return
        if topic == "/coground/skill/state":
            if not self.connected:
                log.info("rosbridge: pick_place_server とつながった（holding=%s, busy=%s）", data.get("holding"), data.get("busy"))
            before = (self.connected, self.holding, self.busy)
            self.connected, self.holding, self.busy = True, data.get("holding") or None, bool(data.get("busy"))
            if before != (self.connected, self.holding, self.busy):
                self._changed()
            return
        if topic in ("/coground/task/plan_result", "/coground/task/plan_feedback"):
            self._on_plan_message(topic, data)
            return
        if topic == "/coground/system/reset_result":
            if self._reset_result is not None and not self._reset_result.done() and data.get("reset_id") == self._reset_id:
                self._reset_result.set_result(data)
            return
        if data.get("goal_id") != self._goal_id or self._goal_id is None:
            return  # ほかの人の goal、または古い goal
        if "holding" in data:
            self.holding = data.get("holding") or None
        state = data.get("state")
        if state == "accepted":
            self._accepted.set()
        elif state == "running":
            self._accepted.set()
            if self._on_phase is not None and data.get("phase"):
                self._on_phase(str(data["phase"]), str(data.get("detail") or ""))
        elif state in TERMINAL:
            self._accepted.set()
            self._finish(SkillResult(state, str(data.get("detail") or ""), data.get("mode")))

    def _on_plan_message(self, topic: str, data: dict[str, Any]) -> None:
        key = (str(data.get("plan_id")), int(data.get("plan_version") or 0))
        if self._plan_key is None or key != self._plan_key:
            if topic.endswith("plan_result") and self._plan_key is not None:
                log.info("rosbridge: 待っているのとは別の計画の結果を無視した（%s v%s、error=%s）", key[0], key[1], data.get("error"))
            # 形式が不正で plan_id が分からない結果は、待っている計画の失敗として扱う
            if topic.endswith("plan_result") and data.get("plan_id") == "" and data.get("error"):
                if self._plan_result is not None and not self._plan_result.done():
                    self._plan_result.set_result(dict(data, plan_id=self._plan_key[0], plan_version=self._plan_key[1]))
            return
        if topic.endswith("plan_result"):
            if self._plan_result is not None and not self._plan_result.done():
                self._plan_result.set_result(data)
        elif self._plan_progress is not None:
            task = asyncio.get_running_loop().create_task(self._plan_progress(data))
            self._background.add(task)
            task.add_done_callback(self._background.discard)

    def _finish(self, result: SkillResult) -> None:
        if self._result is not None and not self._result.done():
            self._result.set_result(result)

    async def _publish(self, topic: str, data: dict[str, Any]) -> bool:
        ws = self._ws
        if ws is None:
            return False
        try:
            await ws.send(json.dumps({"op": "publish", "topic": topic, "msg": {"data": json.dumps(data, ensure_ascii=False)}}))
            return True
        except Exception as e:
            log.warning("rosbridge: publish %s failed: %s", topic, e)
            return False

    async def run_skill(self, skill, object_id, place=None, on_phase=None, *, pose=None, plan_ref=None,
                        keepout_zones=None) -> SkillResult:
        if not self.connected:
            return SkillResult("failed", self.not_connected_reason())
        if self._goal_id is not None or self._plan_key is not None:
            return SkillResult("rejected", "busy")
        self._goal_id = uuid.uuid4().hex[:12]
        self._result = asyncio.get_running_loop().create_future()
        self._accepted.clear()
        self._on_phase = on_phase
        try:
            goal: dict[str, Any] = {"goal_id": self._goal_id, "skill": skill, "object": object_id, "frame_id": "world",
                                    "place": place}
            if pose is not None:
                goal["pose"] = pose
            if plan_ref is not None:
                goal["plan_ref"] = plan_ref
            if skill == "navigate":
                self.nav_goal, self.nav_object = list(pose or []) or None, object_id
                if keepout_zones is not None:
                    goal["keepout_zones"] = keepout_zones
                    self.keepout = list(keepout_zones)
            if not await self._publish("/coground/skill/goal", goal):
                return SkillResult("failed", "Couldn't send the goal to the robot")
            try:
                await asyncio.wait_for(self._accepted.wait(), timeout=self.ACCEPT_TIMEOUT)
            except asyncio.TimeoutError:
                return SkillResult("failed", f"No reply from the robot for {self.ACCEPT_TIMEOUT:.0f} s (is pick_place_server running?)")
            return await self._result
        finally:
            self._goal_id = None
            self._result = None
            self._on_phase = None
            self.nav_goal, self.nav_object = None, None

    async def cancel(self) -> None:
        if self._goal_id is not None:
            await self._publish("/coground/skill/cancel", {"goal_id": self._goal_id})

    async def reset(self) -> tuple[bool, str]:
        # 待っているスキル・計画は、ROS の返事を待たずにこちらで終わらせる（Executor などがすぐ次へ進めるように）
        self._finish(SkillResult("canceled", "Reset"))
        if self._plan_result is not None and not self._plan_result.done():
            plan_id, version = self._plan_key or ("", 0)
            self._plan_result.set_result({"plan_id": plan_id, "plan_version": version, "error": "Reset",
                                          "steps": [], "timeline": None})
        if not self.connected:
            return False, self.not_connected_reason()
        self._reset_id = uuid.uuid4().hex[:12]
        self._reset_result = asyncio.get_running_loop().create_future()
        try:
            if not await self._publish("/coground/system/reset", {"reset_id": self._reset_id}):
                return False, "Couldn't send the reset to the robot"
            try:
                data = await asyncio.wait_for(self._reset_result, timeout=self.RESET_TIMEOUT)
            except asyncio.TimeoutError:
                return False, f"Reset didn't finish after waiting {self.RESET_TIMEOUT:.0f} s (is pick_place_server running?)"
            return bool(data.get("ok")), str(data.get("detail") or "")
        finally:
            self._reset_id = None
            self._reset_result = None

    async def plan_motion(self, request, on_progress=None) -> dict[str, Any]:
        def fail(error: str) -> dict[str, Any]:
            return {"plan_id": request["plan_id"], "plan_version": request["plan_version"], "error": error,
                    "steps": [], "timeline": None}

        if not self.connected:
            return fail(self.not_connected_reason())
        if self._goal_id is not None or self._plan_key is not None:
            return fail("busy (the robot is moving / planning)")
        self._plan_key = (str(request["plan_id"]), int(request["plan_version"]))
        self._plan_result = asyncio.get_running_loop().create_future()
        self._plan_progress = on_progress
        try:
            if not await self._publish("/coground/task/plan_request", request):
                return fail("Couldn't ask the robot to plan")
            try:
                return await asyncio.wait_for(self._plan_result, timeout=PLAN_TIMEOUT)
            except asyncio.TimeoutError:
                return fail(f"No plan returned after waiting {PLAN_TIMEOUT:.0f} s")
            except ConnectionError as e:
                return fail(str(e))
        finally:
            self._plan_key = None
            self._plan_result = None
            self._plan_progress = None


def make_robot() -> Robot:
    url = os.environ.get("COGROUND_ROSBRIDGE_URL", "").strip()
    if url:
        return RosbridgeRobot(url)
    log.warning("robot: COGROUND_ROSBRIDGE_URL が無いので、ROS なしの代役（FakeRobot）を使う。ROS にも Unity にも何も届かない")
    return FakeRobot(phase_delay=float(os.environ.get("COGROUND_FAKE_PHASE_DELAY", "0.4")))
