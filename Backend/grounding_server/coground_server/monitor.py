"""実行中の監視: 台車が動いている間、家庭ルールを見張り、違反しそうなら台車を止めて（hold）、経路を確かめ直してから再開する。

見張るのは、台車が動くと判定が変わりうるルール（norms/monitors.py の build_monitors）:
  replan  領域への進入の禁止（R2）。禁止が効いている時刻に境界を越えそうなら、手前で止めて、領域を避ける経路を計画し直す
          （予測では 17:58 に入れるはずだった経路も、出発が遅れると 18:02 になる）。
          もう中にいるだけなら何もしない（17:59 に入って 18:00 に中にいても、出ることは求めない）
  hold    子供が近くにいる間は台車を止める（R4）。人の位置が観測できなくなったときも止める

hold は、スキルを取り消さない一時停止（robot.hold）。止めるのは台車だけで、腕は止めない。
hold を解くのは、条件が解けたときではなく、残りの経路の再検証が済んだとき:
  1. 止める理由が無くなる（子供が離れた。進入の禁止は、止めた時点でここへ進む）
  2. 台車が止まったのを確かめる
  3. いまの位置から行き先までの経路を計画し（robot.plan_route）、いまの時刻で判定する。
     反するなら、その領域を避ける範囲に足して計画し直す
  4. 合う経路があれば、その範囲を渡して再開する（robot.release）。無ければ、スキルを止めて block を残す
     （Executor が受け取り、依頼の行を保留にする）
この間、台車は動かない。

記録（holds）には、止めるよう求めた時刻・位置・相手との距離（requested）と、実際に止まった時刻・位置・距離（stopped）を
別々に残す。動いている間に観測した状態も貯めておき、移動が終わったら観測に対する判定として依頼の行に記録する。

動かし方:
  Monitor.start()   0.1 秒ごとに tick する（実機・ROS。Executor が実行を始めるときに呼ぶ）
  Monitor.gate()    代役のロボット（FakeRobot）が 1 歩進む前に呼ぶ（テストでも、動きと監視の順番が決まる）
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import time
from typing import Any, Callable

from .eventlog import EventLog
from .models import Verdict
from .norms.evaluate import evaluate
from .norms.monitors import MonitorSpec, build_monitors, entity_distance, monitored, motion_verdicts, route_verdicts
from .norms.predicates import WorldSample
from .norms.task import RouteBlock
from .robot import Robot
from .state import StateStore

log = logging.getLogger(__name__)

PERIOD = 0.1          # 監視の間隔 [s]
LOOKAHEAD = 0.4       # この先まで進んだら違反するか、を調べる距離 [m]。COGROUND_MONITOR_LOOKAHEAD で変える
STOP_SPEED = 0.01     # これより遅ければ止まったとみなす [m/s]
STOP_WAIT = 3.0       # 止まったのを確かめられないとき、これだけ待ったら先へ進む [s]
MAX_REPLAN = 4
HISTORY = 20
TRACE = 3000


class Monitor:
    def __init__(self, state: StateStore, robot: Robot, events: EventLog,
                 notify: Callable[[], None] | None = None) -> None:
        self.state = state
        self.robot = robot
        self.events = events
        self._notify = notify or (lambda: None)
        self.period = PERIOD
        self.lookahead = float(os.environ.get("COGROUND_MONITOR_LOOKAHEAD") or LOOKAHEAD)
        self.active: dict[str, Any] | None = None     # いまの hold の記録
        self.holds: list[dict[str, Any]] = []         # 終わった hold（新しいものが後ろ）
        self.keepout: list[str] = []                  # いまの移動で避けている領域
        self.block: dict[str, Any] | None = None      # 合う経路が無くてスキルを止めた（Executor が take_block で受け取る）
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._prev: tuple[list[float], float] | None = None  # 前に見た台車の位置と時刻（速さを出す）
        self._moving_dir: tuple[float, float] | None = None  # 位置の差から出した、いま進んでいる向き
        self._trace: list[WorldSample] = []           # 動いている間に観測した状態
        self._trace_object: str | None = None
        self._count = 0

    # ------------------------------------------------------------------ 見せる

    def snapshot(self) -> dict[str, Any]:
        return {
            "held": self.robot.held,
            "active": {k: v for k, v in self.active.items() if not k.startswith("_")} if self.active else None,
            "holds": list(self.holds), "keepout": list(self.keepout),
            "monitors": [m.model_dump(mode="json") for m in build_monitors(self.state.all_norms())],
        }

    # ------------------------------------------------------------------ 動かす

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop(), name="monitor")

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.period)
            if self._lock.locked():
                continue
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("monitor: 想定外のエラー")

    async def gate(self) -> None:
        """代役のロボットが 1 歩進む前に呼ぶ。"""
        await self.tick()

    def begin_navigation(self, keepout: list[str]) -> None:
        """台車を動かすスキルを始める前に呼ぶ（その移動で避ける領域）。"""
        self.keepout = list(keepout)
        self.block = None

    def take_block(self) -> dict[str, Any] | None:
        block, self.block = self.block, None
        return block

    async def tick(self) -> None:
        async with self._lock:
            await self._tick()

    async def reset(self) -> None:
        """まっさらにする（system.reset）: hold の記録を消す。ロボットの hold は robot.reset が解く。"""
        async with self._lock:
            self.active, self.block, self.keepout = None, None, []
            self.holds.clear()
            self._trace.clear()

    # ------------------------------------------------------------------ 監視

    def _speed(self, base: list[float] | None) -> float | None:
        """台車の速さ。ロボットが言えばそれ、無ければ位置の差から出す。"""
        direct = self.robot.base_speed
        now = time.monotonic()
        speed = direct
        if base is None:
            self._prev, self._moving_dir = None, None
            return direct
        if self._prev is not None and now - self._prev[1] > 1e-3:
            dx, dy = base[0] - self._prev[0][0], base[1] - self._prev[0][1]
            if direct is None:
                speed = math.hypot(dx, dy) / (now - self._prev[1])
            if math.hypot(dx, dy) >= 0.01:
                self._moving_dir = (dx, dy)
            elif now - self._prev[1] >= 0.3:
                self._moving_dir = None  # 止まっている
        if self._prev is None or now - self._prev[1] >= 0.05:
            self._prev = (list(base), now)
        return speed

    def _heading(self, base: list[float] | None) -> tuple[tuple[float, float] | None, float]:
        """進む向きと、その向きに調べる距離。次に進む点 > いま進んでいる向き > 行き先 の順に使う。"""
        goal = self.robot.nav_goal
        if base is None or goal is None:
            return None, 0.0
        remaining = math.hypot(goal[0] - base[0], goal[1] - base[1])
        nxt = self.robot.next_point
        if nxt is not None and math.hypot(nxt[0] - base[0], nxt[1] - base[1]) > 1e-6:
            return (nxt[0] - base[0], nxt[1] - base[1]), min(self.lookahead, max(remaining, 0.1))
        if self._moving_dir is not None:
            return self._moving_dir, min(self.lookahead, max(remaining, 0.1))
        if remaining > 1e-6:
            return (goal[0] - base[0], goal[1] - base[1]), min(self.lookahead, remaining)
        return None, 0.0

    def _holding(self) -> set[str]:
        """いま持っている物体（条件「何かを持っているとき」が読む）。"""
        held = getattr(self.robot, "holding", None)
        return {held} if held else set()

    def _requester(self) -> str | None:
        task = self.state.active_task
        return task.requester if task is not None else None

    async def _tick(self) -> None:
        robot, state = self.robot, self.state
        moving = robot.nav_goal is not None
        if not moving and self.active is None:
            if self._trace:
                self._finish_trace()
            self._prev = None
            return
        norms = state.all_norms()
        if not monitored(norms) and self.active is None:
            return
        base = robot.base_pose
        speed = self._speed(base)
        now = state.clock.now()
        zones, people = state.zone_polygons(), state.people_samples()
        heading, reach = self._heading(base)
        pose = (base[0], base[1], base[2]) if base is not None else None
        judged = motion_verdicts(norms, pose, heading, reach, now, zones, people, speed=speed,
                                 requester=self._requester(), skip_zones=set(self.keepout), holding=self._holding())
        blocking = [(spec, v) for spec, v in judged if v.value in ("violated", "undetermined")]

        if self.active is None:
            if not (blocking and moving):
                # 止める必要が無い: 観測として貯める（止めるよう求めた瞬間と減速の間は、hold の記録に残す）
                self._observe(pose, speed, now, zones, people)
                return
            await self._hold(blocking, base, now, zones, people)
            if self.robot.base_speed is not None:
                speed = self.robot.base_speed  # 代役のロボットは、その場で止まる
        rec = self.active
        assert rec is not None
        self._check_stopped(rec, base, speed, now, zones, people)
        if not moving:  # 止めている間に、スキルが終わった（取り消された）
            await self._close(rec, "skill_ended", now)
            await robot.release(None)
            return
        waiting = [(spec, v) for spec, v in blocking if spec.response != "replan"]
        if waiting:
            rec["waiting_for"] = [spec.rule_id for spec, _ in waiting]
            return
        if rec["stopped"] is None:
            return  # まだ止まりきっていない
        rec["waiting_for"] = []
        await self._reverify(rec, norms)

    def _observe(self, pose: tuple[float, float, float] | None, speed: float | None, now: Any,
                 zones: dict[str, Any], people: Any) -> None:
        """動いている間の観測を貯める（移動が終わったら、観測に対する判定にする）。"""
        if self.robot.nav_goal is None:
            return
        self._trace_object = self.robot.nav_object
        self._trace.append(WorldSample(t=now, phase="base_motion", base=pose, base_speed=speed, zones=zones, people=people))
        del self._trace[:-TRACE]

    def _finish_trace(self) -> None:
        trace, self._trace = self._trace, []
        norms = self.state.all_norms()
        permissions = [n for n in norms if n.norm == "permission"]
        now = self.state.clock.now()
        verdicts = [evaluate(r, trace, None, basis="observed", requester=self._requester(), exceptions=permissions, now=now)
                    for r in monitored(norms)]
        self.state.record_observed(self._trace_object, verdicts)
        bad = [v for v in verdicts if v.value == "violated"]
        if bad:
            self.events.add("monitor", "system", action="observed_violation", object_id=self._trace_object,
                            rules=[v.rule_id for v in bad])

    async def finish_navigation(self) -> None:
        """台車を動かすスキルが終わったら呼ぶ（観測に対する判定を記録する）。"""
        async with self._lock:
            if self.active is not None and self.robot.nav_goal is None:
                await self._close(self.active, "skill_ended", self.state.clock.now())
                await self.robot.release(None)
            if self._trace and self.robot.nav_goal is None:
                self._finish_trace()

    # ------------------------------------------------------------------ hold

    def _distances(self, rule_ids: list[str], base: list[float] | None, zones: dict[str, Any], people: Any) -> dict[str, Any]:
        rules = {r.id: r for r in self.state.all_norms()}
        pose = (base[0], base[1], base[2]) if base is not None else None
        return {i: entity_distance(rules[i], pose, zones, people) for i in rule_ids if i in rules}

    async def _hold(self, blocking: list[tuple[MonitorSpec, Verdict]], base: list[float] | None, now: Any,
                    zones: dict[str, Any], people: Any) -> None:
        rules = {r.id: r for r in self.state.all_norms()}
        ids = [spec.rule_id for spec, _ in blocking]
        reason = " / ".join(
            ("\"%s\" (%s) %s" % (rules[spec.rule_id].original_text, spec.rule_id,
                               "is about to be violated" if v.value == "violated" else "lacks information to evaluate"))
            for spec, v in blocking)
        self._count += 1
        self.active = {
            "id": f"hold_{self._count}", "rule_ids": ids, "reason": reason,
            "responses": {spec.rule_id: spec.response for spec, _ in blocking},
            "verdicts": {spec.rule_id: v.value for spec, v in blocking},
            "missing": [m.model_dump(mode="json") for _, v in blocking for m in v.missing],
            "object_id": self.robot.nav_object, "goal": list(self.robot.nav_goal or []),
            # 止めるよう求めた時刻・位置・相手との距離
            "requested": {"t": now.isoformat(), "base": list(base) if base is not None else None,
                          "distance": self._distances(ids, base, zones, people)},
            "stopped": None,     # 実際に止まった時刻・位置・距離（_check_stopped が入れる）
            "waiting_for": [], "replans": [], "keepout_before": list(self.keepout),
            "released": None, "outcome": None, "_mono": time.monotonic(),
        }
        await self.robot.hold(reason)
        log.info("monitor: hold %s: %s", self.active["id"], reason)
        self.events.add("monitor", "system", action="hold", hold_id=self.active["id"], rules=ids, reason=reason,
                        requested=self.active["requested"])
        self._notify()

    def _check_stopped(self, rec: dict[str, Any], base: list[float] | None, speed: float | None, now: Any,
                       zones: dict[str, Any], people: Any) -> None:
        if rec["stopped"] is not None:
            return
        waited = time.monotonic() - rec["_mono"]
        stopped = speed is not None and speed < STOP_SPEED
        if not stopped and waited < STOP_WAIT:
            return
        rec["stopped"] = {"t": now.isoformat(), "base": list(base) if base is not None else None,
                          "distance": self._distances(rec["rule_ids"], base, zones, people),
                          "confirmed": stopped, "after": round(waited, 3)}
        self.events.add("monitor", "system", action="stopped", hold_id=rec["id"], stopped=rec["stopped"])

    async def _reverify(self, rec: dict[str, Any], norms: list[Any]) -> None:
        """残りの経路を計画して判定する。合う経路があれば再開、無ければスキルを止める。"""
        robot, state = self.robot, self.state
        goal = robot.nav_goal
        if goal is None:
            return
        zone_rules = {r.id: r for r in monitored(norms) if r.target.kind == "zone"}
        # 入りそうになって止めた領域は、はじめから避ける（経路がたまたま通らなくても、近くでまた止まらないように）
        known = state.zone_polygons()
        triggered = [zone_rules[i].target.id for i in rec["rule_ids"]
                     if rec["responses"].get(i) == "replan" and rec["verdicts"].get(i) == "violated" and i in zone_rules]
        keepout = [*self.keepout, *(z for z in triggered if z is not None and z in known and z not in self.keepout)]
        failure = ""
        verdicts: list[Verdict] = []   # 最後に判定できた経路の判定
        rules = {r.id: r for r in norms}

        def names(vs: list[Verdict]) -> str:
            return ", ".join(f"\"{rules[v.rule_id].original_text}\" ({v.rule_id})" for v in vs if v.rule_id in rules) or "household rules"

        for _ in range(MAX_REPLAN):
            route = await robot.plan_route(list(goal), state.keepout_payload(keepout))
            started = state.clock.now()
            attempt: dict[str, Any] = {"t": started.isoformat(), "keepout": list(keepout), "ok": bool(route.get("ok")),
                                       "reason": route.get("reason") or ""}
            rec["replans"].append(attempt)
            if not route.get("ok"):
                # 領域を避けると行けない: その領域の禁止に反しない経路が無い
                added = [z for z in keepout if z not in self.keepout]  # この再検証で避けることにした領域
                verdicts = [Verdict(rule_id=r.id, value="violated", basis="predicted", entity_id=r.target.id,
                                    detail="No path that avoids the zone", evaluated_at=started)
                            for r in zone_rules.values() if r.target.id in added]
                failure = (f"No path that doesn't violate {names(verdicts)}" if verdicts else "No path to the destination") \
                    + f" ({route.get('reason') or ''})"
                break
            verdicts = route_verdicts(norms, route.get("base") or [], started, state.zone_polygons(),
                                      requester=self._requester(), now=started, holding=self._holding())
            attempt["verdicts"] = {v.rule_id: v.value for v in verdicts}
            bad = [v for v in verdicts if v.value in ("violated", "undetermined")]
            if not bad:
                # 計画している間に、止める理由が戻っていないか（子供がまた近づいた、など）
                base = robot.base_pose
                pose = (base[0], base[1], base[2]) if base is not None else None
                again = motion_verdicts(norms, pose, None, 0.0, started, state.zone_polygons(), state.people_samples(),
                                        speed=0.0, requester=self._requester(), skip_zones=set(keepout),
                                        holding=self._holding())
                waiting = [spec.rule_id for spec, v in again
                           if spec.response != "replan" and v.value in ("violated", "undetermined")]
                if waiting:
                    rec["waiting_for"] = waiting
                    return
                self.keepout = keepout
                state.record_route(rec["object_id"], verdicts)
                await self._close(rec, "released", started)
                await robot.release(state.keepout_payload(keepout))
                return
            known = state.zone_polygons()
            more = [zone_rules[v.rule_id].target.id for v in bad
                    if v.value == "violated" and v.rule_id in zone_rules
                    and zone_rules[v.rule_id].target.id not in keepout and zone_rules[v.rule_id].target.id in known]
            if not more:
                failure = f"No path that doesn't violate {names(bad)}" if any(v.value == "violated" for v in bad) \
                    else f"Not enough information to evaluate {names(bad)}"
                break
            keepout.extend(z for z in more if z is not None)
        else:
            failure = "Couldn't find a path that complies with household rules (too many replans)"
        # 合う経路が無い: スキルを止めて、Executor に理由を渡す
        bad = [v for v in verdicts if v.value in ("violated", "undetermined")]
        missing = [m for v in bad for m in v.missing]
        self.block = {
            "object_id": rec["object_id"],
            "block": RouteBlock(reason=failure, verdicts=bad, missing=[] if any(v.value == "violated" for v in bad) else missing,
                                searched={"planned_at": state.clock.now().isoformat(), "during": "execution",
                                          "hold_id": rec["id"], "attempts": list(rec["replans"])}),
        }
        await self._close(rec, "blocked", state.clock.now(), failure)
        await robot.cancel()
        await robot.release(None)

    async def _close(self, rec: dict[str, Any], outcome: str, now: Any, detail: str = "") -> None:
        rec["released"] = {"t": now.isoformat(), "base": self.robot.base_pose}
        rec["outcome"], rec["detail"] = outcome, detail
        rec["keepout_after"] = list(self.keepout)
        rec.pop("_mono", None)
        self.holds.append(rec)
        del self.holds[:-HISTORY]
        self.active = None
        log.info("monitor: %s -> %s %s", rec["id"], outcome, detail)
        self.events.add("monitor", "system", action=outcome, hold_id=rec["id"], detail=detail,
                        keepout=rec["keepout_after"], replans=len(rec["replans"]))
        self._notify()


__all__ = ["Monitor"]
