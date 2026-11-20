"""Plan の step を 1 つずつロボットに実行させる。実行中も、止める・待つ・飛ばす・行き先を変えることができる。

考え方:
  - step 1 つ = 移動 → pick（つかんで持ち上げる）→ 移動 → place（運んで置く / 落とす）のスキル（robot.py）
  - 実行の前に、動作計画（motion.py の MotionStore。Plan ボタン）が要る。計画した止まる位置へ移動し、
    計画した軌道で動かす（台車がぴったり止まり、今のシーンでもぶつからなければ、そのまま再生する。だめならその場で計画し直す）。
    start(allow_unplanned=True) なら計画なしでも動かす（移動はせず、その場で計画する）
  - スキルが 1 つ終わるたびに、いまの Plan を読み直して次を決める。
    だから、実行中に Plan が変わっても（plan.place で行き先を変える、ルールを変えるなど）、そのまま次の動きに効く。
    持っている物の行き先が変われば、新しい行き先に置く。持っている物の step が無くなれば、つかんだ元の場所へ戻す
  - 置く動作が成功しても、まだ done にしない。配置先の観測（Unity の scene.update。代役のロボットでは
    robot.placement_observation）を待ち、行き先の領域にあれば done、別の場所なら misplaced、観測が来なければ unverified
  - 台車が動いている間は、家庭ルールを見張る（monitor.py）。領域への進入の禁止に反しそうなら手前で止めて経路を計画し直し、
    子供が近くにいる間は止めておく（hold。スキルは取り消さない）。合う経路が無ければ、その物は保留にして次へ進む
    （持っているときは、持ったまま止まる）。移動には、動作計画で避けた領域（motion.py の keepout）も渡す
  - つかむ直前に、いまの時刻と属性で判定をやり直す（訂正で「割れ物」になった、時刻で効き始めた禁止、に対応する）
  - 実行の記録（done / failed / skipped / misplaced / unverified）は「物体 -> 行き先の領域」ごとに持つ。
    Plan は シーンが変わるたびに作り直され step の id が変わるので、id では覚えない

状態（mode）:
  idle     何もしていない（まだ始めていない、または全部終わった）
  running  実行中
  paused   止まっている（reason に理由: user / stopped / failed: ... / ロボットにつながっていない）。resume で続きから

命令（handlers/execution.py の exec.*）:
  start(step_ids)  始める。step_ids を渡すと、その step だけをその順に実行する。動作計画が無い / 古い step があれば断る
  pause            いまのスキル（pick か place）が終わったら止まる。物を持ったまま止まることもある
  stop             いますぐ止める（スキルを取り消す）。物を持っていれば持ったまま
  resume           続きから。持っている物があれば、置くところから
  skip(step_id)    その step を飛ばす。いま実行中の step なら取り消し、持っていれば元の場所へ戻す
  retry(step_id)   failed / skipped / done の記録を消して、もう一度実行できるようにする
  confirm          確認待ち（confirm = each_step のとき、つかむ前に毎回待つ）を進める
  set_policy       confirm（auto / each_step）と on_failure（pause / continue）を変える
  reset            記録を全部消す（実行中は不可）
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Awaitable, Callable, Literal

from .eventlog import EventLog
from .models import Step
from .monitor import Monitor
from .motion import MotionStore, place_for, step_key
from .robot import Robot, SkillResult
from .state import StateStore

log = logging.getLogger(__name__)

Mode = Literal["idle", "running", "paused"]
ConfirmPolicy = Literal["auto", "each_step"]
FailurePolicy = Literal["pause", "continue"]

# この記録がある step は、retry するまで実行しない
#   misplaced   配置動作は成功したが、別の場所にあるのを観測した
#   unverified  配置動作は成功したが、配置先の観測が来なかった
FINISHED = ("done", "failed", "skipped", "misplaced", "unverified")
OBSERVE_TIMEOUT = 5.0  # 置いたあと、配置先の観測（scene.update）を待つ時間 [s]。COGROUND_OBSERVE_TIMEOUT で変える
OBSERVE_POLL = 0.05
HISTORY = 50


class ExecError(Exception):
    """命令を受けられない（ハンドラが invalid_state の error response にする）。"""


class Executor:
    def __init__(
        self, state: StateStore, robot: Robot, events: EventLog, publish: Callable[[], Awaitable[None]],
        motion: MotionStore | None = None,
    ) -> None:
        self.state = state
        self.motion = motion
        self.robot = robot
        self.events = events
        self._publish_state = publish

        self.mode: Mode = "idle"
        self.reason = ""
        self.confirm: ConfirmPolicy = "auto"
        self.on_failure: FailurePolicy = "pause"
        self.pausing = False                       # pause を受けて、いまのスキルが終わるのを待っている
        self.waiting_confirm: str | None = None    # 確認を待っている step の id
        self.current: dict[str, Any] | None = None  # 実行中のスキル: step_id, object_id, skill, phase, detail
        self.only: list[str] | None = None         # start(step_ids) で絞ったときの物体 ID（この順に実行する）
        self.records: dict[str, dict[str, str]] = {}  # step_key -> {"status", "detail"}
        self.history: list[dict[str, Any]] = []    # 終わったスキル（新しいものが後ろ）
        self.allow_unplanned = False               # 動作計画なしでも動かす（その場で計画する）
        self._arrived: tuple[str, str] | None = None  # (step_key, "pick" | "place")。計画した止まる位置に着いた
        # 代役のロボットは観測をすぐ返すので待たない（robot.placement_observation）
        self.observe_timeout = 0.0 if robot.simulated else float(os.environ.get("COGROUND_OBSERVE_TIMEOUT") or OBSERVE_TIMEOUT)

        self._confirmed: set[str] = set()
        self._stop = False           # stop を受けた（取り消されたスキルを失敗にしない）
        self._skipped_current = False
        self._wake = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._background: set[asyncio.Task[None]] = set()
        robot.on_change = self._notify
        # 台車が動いている間の家庭ルールの監視。代役のロボットは、1 歩進む前に gate を呼ぶ
        self.monitor = Monitor(state, robot, events, self._notify)
        if hasattr(robot, "gate"):
            robot.gate = self.monitor.gate

    # ------------------------------------------------------------------ 見せる

    def snapshot(self) -> dict[str, Any]:
        self._prune()
        steps: dict[str, dict[str, str]] = {}
        for s in self._plan_steps():
            if s.status != "ok" or s.to is None:
                steps[s.id] = {"status": "blocked", "detail": s.message or s.status}
            elif self._unworkable(s) is not None and step_key(s) not in self.records:
                # 検証して動作が成立しないと分かった step は、実行の対象から外す（元の場所に残す）
                steps[s.id] = {"status": "blocked", "detail": self._unworkable(s) or ""}
            else:
                steps[s.id] = dict(self.records.get(step_key(s), {"status": "pending", "detail": ""}))
        return {
            "mode": self.mode,
            "reason": self.reason,
            "pausing": self.pausing,
            "confirm": self.confirm,
            "on_failure": self.on_failure,
            "waiting_confirm": self.waiting_confirm,
            "current": dict(self.current) if self.current else None,
            "only": list(self.only) if self.only is not None else None,
            "allow_unplanned": self.allow_unplanned,
            "steps": steps,
            "history": list(self.history),
            "robot": self.robot.snapshot(),
            "monitor": self.monitor.snapshot(),
        }

    def _plan_steps(self) -> list[Step]:
        return list(self.state.plan.steps) if self.state.plan else []

    def _unworkable(self, step: Step) -> str | None:
        """動作計画で「成立しない」と検証された step なら理由。計画なしで動かす（allow_unplanned）ときは見ない"""
        if self.motion is None or self.allow_unplanned:
            return None
        return self.motion.infeasible_reason(step)

    def _prune(self) -> None:
        """Plan から無くなった step（運び終わって行き先に入った、行き先の指定が消えた）の記録を捨てる。"""
        keys = {step_key(s) for s in self._plan_steps()}
        for k in [k for k in self.records if k not in keys]:
            del self.records[k]
        self._confirmed &= keys

    def _notify(self) -> None:
        """状態が変わったことを全クライアントに知らせる（同期の場所から呼べる）。"""
        try:
            task = asyncio.get_running_loop().create_task(self._publish())
        except RuntimeError:
            return  # イベントループの外（テストの組み立て中など）
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    async def _publish(self) -> None:
        self.state.touch()
        await self._publish_state()

    # ------------------------------------------------------------------ 命令

    async def start(self, step_ids: list[str] | None = None, actor: str = "user", allow_unplanned: bool = False) -> None:
        if self.mode == "running":
            raise ExecError("Already running")
        if self.motion is not None and self.motion.status == "planning":
            raise ExecError("Motion planning in progress")
        if self.robot.busy:
            raise ExecError("The robot is moving (e.g. a unit-test skill. Wait for it to finish or stop it with robot.cancel)")
        only = None
        by_id = {s.id: s for s in self._plan_steps()}
        if step_ids:
            missing = [i for i in step_ids if i not in by_id]
            if missing:
                raise ExecError(f"Steps not in the Plan: {missing}")
            only = [by_id[i].object_id for i in step_ids]
        targets = [by_id[i] for i in step_ids] if step_ids else [
            s for s in self._plan_steps() if s.status == "ok" and s.to is not None
            and self.records.get(step_key(s), {}).get("status") not in FINISHED]
        if not allow_unplanned and self.motion is not None:
            # 名指しされていない step は、検証して成立しないと分かったものを外して、残りを実行する
            # （あるステップが成立しなくても、独立して成立する作業は実行できる）
            problems = self.motion.missing([s for s in targets if s.status == "ok" and s.to is not None],
                                           skip_infeasible=not step_ids)
            if problems:
                raise ExecError("No motion plan (Plan), or some steps are stale. Rebuild the Plan, or execute without a plan: "
                                + " / ".join(problems))
            if not step_ids and targets and all(self.motion.infeasible_reason(s) is not None for s in targets):
                raise ExecError("Nothing to execute: no step passed the check ("
                                + " / ".join(f"{s.id}: {self.motion.infeasible_reason(s)}" for s in targets) + ")")
        for s in targets if step_ids else []:  # 名指しで頼まれた step は、前の記録があってもやり直す
            self.records.pop(step_key(s), None)
        self.only = only
        self.allow_unplanned = allow_unplanned
        self._arrived = None
        if self.motion is not None:
            self.motion.notice = ""
        self.monitor.keepout = []
        self._begin("start", actor, step_ids=step_ids or None, allow_unplanned=allow_unplanned)
        await self._publish()

    async def resume(self, actor: str = "user") -> None:
        if self.mode != "paused":
            raise ExecError(f"Not stopped (mode = {self.mode})")
        if self.robot.busy:
            raise ExecError("The robot is moving (e.g. a unit-test skill. Wait for it to finish or stop it with robot.cancel)")
        self._begin("resume", actor)
        await self._publish()

    def _begin(self, what: str, actor: str, **data: Any) -> None:
        self.mode, self.reason, self.pausing, self._stop = "running", "", False, False
        self.events.add("exec", actor, action=what, **data)
        self.monitor.start()
        self._task = asyncio.create_task(self._run(), name="executor")

    async def pause(self, actor: str = "user") -> None:
        if self.mode != "running":
            raise ExecError(f"Not running (mode = {self.mode})")
        self.pausing = True
        self.events.add("exec", actor, action="pause")
        self._wake.set()
        await self._publish()

    async def stop(self, actor: str = "user") -> None:
        if self.mode != "running":
            raise ExecError(f"Not running (mode = {self.mode})")
        self._stop = True
        self.events.add("exec", actor, action="stop")
        await self.robot.cancel()
        self._wake.set()
        await self._publish()

    async def skip(self, step_id: str, actor: str = "user") -> None:
        step = self._step(step_id)
        self.records[step_key(step)] = {"status": "skipped", "detail": f"skipped by {actor}"}
        self.events.add("exec", actor, action="skip", step_id=step_id, object_id=step.object_id)
        if self.current and self.current["object_id"] == step.object_id and self.current["skill"] != "put_back":
            self._skipped_current = True
            await self.robot.cancel()
        self._wake.set()
        await self._publish()

    async def retry(self, step_id: str, actor: str = "user") -> None:
        step = self._step(step_id)
        self.records.pop(step_key(step), None)
        self.state.mark_row(step.object_id, "pending")
        self.events.add("exec", actor, action="retry", step_id=step_id, object_id=step.object_id)
        self._wake.set()
        await self._publish()

    async def confirm_step(self, actor: str = "user") -> None:
        if self.waiting_confirm is None:
            raise ExecError("No step is waiting for confirmation")
        step = self._step(self.waiting_confirm)
        self._confirmed.add(step_key(step))
        self.events.add("exec", actor, action="confirm", step_id=step.id, object_id=step.object_id)
        self._wake.set()
        await self._publish()

    async def set_policy(
        self, confirm: ConfirmPolicy | None = None, on_failure: FailurePolicy | None = None, actor: str = "user"
    ) -> None:
        if confirm is not None:
            self.confirm = confirm
        if on_failure is not None:
            self.on_failure = on_failure
        self.events.add("exec", actor, action="set_policy", confirm=self.confirm, on_failure=self.on_failure)
        self._wake.set()
        await self._publish()

    async def reset(self, actor: str = "user") -> None:
        if self.mode == "running":
            raise ExecError("Can't clear while running (stop first)")
        self.mode, self.reason, self.only = "idle", "", None
        self.records.clear()
        self.history.clear()
        self._confirmed.clear()
        self.events.add("exec", actor, action="reset")
        await self._publish()

    async def clear_all(self, actor: str = "user") -> None:
        """まっさらにする（system.reset）: 実行中でも止め、実行の状態と記録を全部消す。方針（confirm / on_failure）は残す。
        ロボットのスキルは呼ぶ側が robot.reset で終わらせる（そうすると _run が止まる）。"""
        if self.mode == "running":
            self._stop = True
            self._wake.set()
            task = self._task
            if task is not None and not task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=15.0)
                except asyncio.TimeoutError:
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
        self.mode, self.reason, self.only, self.pausing = "idle", "", None, False
        self.waiting_confirm, self.current, self._arrived = None, None, None
        self.allow_unplanned, self._stop, self._skipped_current = False, False, False
        self.records.clear()
        self.history.clear()
        self._confirmed.clear()
        await self.monitor.reset()
        self.events.add("exec", actor, action="clear_all")

    def _step(self, step_id: str) -> Step:
        step = next((s for s in self._plan_steps() if s.id == step_id), None)
        if step is None:
            raise ExecError(f"Step not in the Plan: {step_id!r}")
        return step

    async def close(self) -> None:
        tasks = [t for t in [self._task, *self._background] if t is not None]
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.monitor.close()

    # ------------------------------------------------------------------ 実行

    def _next_step(self, holding: str | None) -> Step | None:
        """次に実行する step。持っている物の step があれば、それが先。"""
        self._prune()
        steps = [
            s for s in self._plan_steps()
            if s.status == "ok" and s.to is not None
            and self.records.get(step_key(s), {}).get("status") not in FINISHED
            and (s.object_id == holding or self._unworkable(s) is None)
        ]
        if self.only is not None:
            order = {obj: i for i, obj in enumerate(self.only)}
            steps = sorted((s for s in steps if s.object_id in order), key=lambda s: order[s.object_id])
        held = next((s for s in steps if s.object_id == holding), None)
        return held or (steps[0] if steps else None)

    def _to_paused(self, reason: str) -> None:
        self.mode, self.reason, self.pausing = "paused", reason, False
        self.events.add("exec", "system", action="paused", reason=reason)

    async def _run(self) -> None:
        try:
            while self.mode == "running":
                if self._stop:
                    self._to_paused("stopped")
                    break
                if self.pausing:
                    self._to_paused("user")
                    break
                if not self.robot.connected:
                    self._to_paused("not connected to the robot")
                    break
                holding = self.robot.holding
                step = self._next_step(holding)

                if holding is not None and (step is None or step.object_id != holding):
                    # 持っている物の step が無い（飛ばされた、行き先が消えた、失敗した）: つかんだ元の場所へ戻す
                    result = await self._skill("put_back", holding, None, None)
                    if not result.ok:
                        self._to_paused("stopped" if self._stop else f"failed: can't return {holding}: {result.detail}")
                        break
                    continue

                if step is None:
                    self.mode, self.reason, self.only = "idle", "finished", None
                    self.events.add("exec", "system", action="finished")
                    break

                key = step_key(step)
                if holding is None and self.confirm == "each_step" and key not in self._confirmed:
                    self.waiting_confirm = step.id
                    await self._publish()
                    self._wake.clear()
                    await self._wake.wait()
                    self.waiting_confirm = None
                    continue

                kind = "pick" if holding != step.object_id else "place"
                entry = self.motion.entry_for(step, holding=kind == "place") if self.motion is not None else None
                if entry is None and not self.allow_unplanned and self.motion is not None:
                    # 実行中に計画が古くなった（物体が動いた、行き先が変わったなど）
                    self.records[key] = {"status": "failed", "detail": "Motion plan is stale (rebuild the Plan)"}
                    self._to_paused(f"failed: {step.object_id}: motion plan is stale (rebuild the Plan)")
                    break
                stop = entry["result"]["stops"].get(kind) if entry is not None else None
                if stop is not None and self._arrived != (key, kind):
                    # 計画した止まる位置へ移動する。着いたら Plan を読み直す（止める・飛ばすを受けられるように）
                    self.records[key] = {"status": "moving_to_" + kind, "detail": ""}
                    # 動作計画で避けた領域と、この実行の途中で避けることにした領域を、移動にも渡す
                    keepout = sorted({*(entry.get("keepout") or []), *self.monitor.keepout}) if entry is not None else []
                    self.monitor.begin_navigation(keepout)
                    result = await self._skill("navigate", step.object_id, None, step, pose=stop,
                                               keepout_zones=self.state.keepout_payload(keepout))
                    await self.monitor.finish_navigation()
                    blocked = self.monitor.take_block()
                    if blocked is not None:
                        # 家庭ルールに合う経路が無い（監視がスキルを止めた）: この物は保留にする
                        reason = blocked["block"].reason
                        self.records.pop(key, None)
                        self._arrived = None
                        self.events.add("exec", "system", action="route_blocked", object_id=step.object_id, reason=reason)
                        self.state.set_route_block(step.object_id, blocked["block"])
                        if holding == step.object_id:
                            self._to_paused(f"failed: {step.object_id}: {reason} (stopped while holding it)")
                            break
                        continue
                    if result.ok and not self._skipped_current:
                        self._arrived = (key, kind)
                        continue
                elif kind == "pick":
                    # つかむ直前に、いまの時刻・属性で判定をやり直す
                    self.state.recheck()
                    fresh = next((s for s in self._plan_steps() if s.object_id == step.object_id), None)
                    if fresh is None or fresh.status != "ok" or fresh.to is None:
                        self.events.add("exec", "system", action="pick_withheld", object_id=step.object_id,
                                        reason=(fresh.message if fresh is not None else "") or "")
                        self._arrived = None
                        continue
                    self.records[key] = {"status": "picking", "detail": ""}
                    self.state.mark_row(step.object_id, "in_progress")
                    result = await self._skill("pick", step.object_id, None, step,
                                               plan_ref=entry["ref"] if entry else None)
                    if result.ok and not self._skipped_current:
                        self.records[key] = {"status": "holding", "detail": ""}
                        continue  # Plan を読み直してから置く（行き先が変わっているかもしれない）
                else:
                    self.records[key] = {"status": "placing", "detail": ""}
                    assert step.to is not None
                    release = entry["place"] if entry is not None else place_for(self.state.scene, step)[0]
                    result = await self._skill("place", step.object_id, release, step,
                                               plan_ref=entry["ref"] if entry else None)
                    if result.ok:
                        self._confirmed.discard(key)
                        self._skipped_current = False  # 飛ばす命令が間に合わなかった（もう置いた）
                        if self.motion is not None:
                            self.motion.forget(step)
                        outcome, detail = await self._verify_placement(step, key)
                        if outcome != "done" and self.on_failure == "pause":
                            self._to_paused(f"failed: {step.object_id}: {detail}")
                            break
                        continue

                # ここに来るのは、スキルが成功しなかったとき
                if self._skipped_current:
                    # 飛ばされた。持っていれば、次の周で元の場所へ戻す
                    self._skipped_current = False
                    self.records[key] = {"status": "skipped", "detail": "Skipped during execution"}
                    continue
                if result.state == "canceled" and self._stop:
                    self.records.pop(key, None)  # 続きは resume で（持っていれば置くところから）
                    continue
                self.records[key] = {"status": "failed", "detail": result.detail or result.state}
                self.state.mark_row(step.object_id, "failed", result.detail or result.state)
                if self.on_failure == "pause":
                    self._to_paused(f"failed: {step.object_id}: {result.detail or result.state}")
                    break
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("executor: 想定外のエラー")
            self._to_paused(f"failed: internal error: {type(e).__name__}: {e}")
        finally:
            self.current = None
            self.waiting_confirm = None
            self._skipped_current = False
            await self._publish()

    async def _verify_placement(self, step: Step, key: str) -> tuple[str, str]:
        """置く動作が成功したあと、配置先の観測を待って記録する。戻り値は (done / misplaced / unverified, 理由)。

        行き先の領域にあるのを観測したら、すぐ done。待つ時間が過ぎたら、
        その間にシーンが届いていれば misplaced（届いた場所が行き先と違う）、届いていなければ unverified。
        """
        assert step.to is not None
        target = step.to.region_id
        self.records[key] = {"status": "placed_unverified", "detail": "Waiting for observation of the placement"}
        self.state.mark_row(step.object_id, "placed_unverified", "Waiting for observation of the placement")
        seen_from = self.state.scene_version
        if self.robot.simulated:
            # Unity がいないので、観測の代わりにここでシーンを書く（本物のときは Unity の scene.update で届く）
            observed = getattr(self.robot, "placement_observation", "auto")
            if observed == "auto":
                p = step.to.pose
                self.state.move_object(step.object_id, p.position, p.rotation, target)
            elif observed != "none":
                self.state.move_object(step.object_id, self._region_center(observed) or step.to.pose.position,
                                       step.to.pose.rotation, observed)
        await self._publish()

        deadline = asyncio.get_running_loop().time() + self.observe_timeout
        while self.state.region_of(step.object_id) != target:
            if self._stop or asyncio.get_running_loop().time() >= deadline:
                break
            await asyncio.sleep(OBSERVE_POLL)

        region = self.state.region_of(step.object_id)
        if region == target:
            outcome, detail = "done", ""
        elif self.state.scene_version > seen_from:
            outcome, detail = "misplaced", f"Wrong placement (it's in {region or 'outside any zone'}; specified {target})"
        else:
            outcome, detail = "unverified", "Couldn't observe the placement"
        self.records[key] = {"status": outcome, "detail": detail}
        self.state.record_placement(step.object_id, outcome, detail)  # type: ignore[arg-type]
        self.events.add("exec", "system", action="placement_observed", object_id=step.object_id, target=target,
                        observed=region, outcome=outcome)
        return outcome, detail

    def _region_center(self, region_id: str) -> tuple[float, float, float] | None:
        region = next((r for r in self.state.scene.regions if r.id == region_id), None)
        if region is None:
            return None
        if region.box is not None:
            return region.box.center
        poly = region.polygon or []
        return (sum(v[0] for v in poly) / len(poly), sum(v[1] for v in poly) / len(poly), sum(v[2] for v in poly) / len(poly))

    async def _skill(self, skill: str, object_id: str, place: dict[str, Any] | None, step: Step | None, *,
                     pose: list[float] | None = None, plan_ref: dict[str, Any] | None = None,
                     keepout_zones: list[dict[str, Any]] | None = None) -> SkillResult:
        """skill: navigate / pick / place / put_back（= place を行き先なしで呼ぶ。元の場所へ戻す）"""
        self.current = {"step_id": step.id if step else None, "object_id": object_id, "skill": skill,
                        "phase": None, "detail": ""}
        self.events.add("skill", "system", action="start", skill=skill, object_id=object_id,
                        step_id=self.current["step_id"], place=place, pose=pose, plan_ref=plan_ref)
        await self._publish()

        def on_phase(phase: str, detail: str) -> None:
            if self.current is not None:
                self.current["phase"], self.current["detail"] = phase, detail
            self.events.add("skill", "system", action="phase", skill=skill, object_id=object_id, phase=phase)
            self._notify()

        name = "place" if skill == "put_back" else skill
        if skill == "navigate":
            result = await self.robot.run_skill(name, object_id, place, on_phase, pose=pose, plan_ref=plan_ref,
                                                keepout_zones=keepout_zones)
        else:
            result = await self.robot.run_skill(name, object_id, place, on_phase, pose=pose, plan_ref=plan_ref)
        self.events.add("skill", "system", action="result", skill=skill, object_id=object_id,
                        state=result.state, detail=result.detail, mode=result.mode)
        self.history.append({"object_id": object_id, "skill": skill, "state": result.state, "detail": result.detail,
                             "mode": result.mode})
        del self.history[:-HISTORY]
        self.current = None
        await self._publish()
        return result
