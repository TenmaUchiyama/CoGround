"""ハンドラから使う共有オブジェクト（ctx.services）。VLM / clingo もここに足していく。"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field

from typing import Any

from .eventlog import EventLog
from .executor import ExecError, Executor
from .hub import Hub
from .motion import MotionStore
from .llm import LlmClient, make_llm
from .norms.attributes import questions
from .perception import Perception
from .perception.schema import AttributeQuestion
from .robot import Robot, make_robot
from .rulebank import RuleBank
from .state import StateStore


@dataclass
class Services:
    hub: Hub = field(default_factory=Hub)
    state: StateStore = field(default_factory=StateStore)
    llm: LlmClient = field(default_factory=make_llm)  # API キーか Claude Agent SDK（llm/client.py）。テストでは FakeLlm に差し替える
    robot: Robot = field(default_factory=make_robot)  # ROS（rosbridge）か、ROS なしの代役（robot.py）
    events: EventLog = field(default_factory=EventLog.from_env)
    test_plan: dict[str, Any] | None = None  # ロボット単体テストの直近の計画（handlers/robot_test.py の robot.plan）
    # 依頼（task.request）を受けたら、続けて動作計画（motion.plan）を自動で始める。COGROUND_AUTO_MOTION_PLAN=0 で無効
    auto_motion_plan: bool = field(default_factory=lambda: os.environ.get("COGROUND_AUTO_MOTION_PLAN", "1") not in ("0", "false", ""))
    motion: MotionStore = field(init=False)
    executor: Executor = field(init=False)
    perception: Perception = field(init=False)  # 画像 → 検出 → VLM → 物体の記憶（perception/）

    def _vlm_questions(self) -> list[AttributeQuestion]:
        return [AttributeQuestion(name=a.name, how_to_tell=a.how_to_tell, values=a.values)
                for a in questions(self.state.all_norms())]

    def __post_init__(self) -> None:
        # VLM に聞く属性は、いまあるルールから作る（ルールが変われば、次の解析から質問も変わる）
        self.perception = Perception.from_env(lambda: self.llm, self._vlm_questions)
        # ルールをファイルに残す（COGROUND_RULE_BANK。空なら残さない）。先に読み込んでから、書き出しを有効にする
        bank = RuleBank.from_env()
        if bank is not None:
            bank.load(self.state)
            self.state.rule_bank = bank
        self.motion = MotionStore(self.state, self.robot, self.events, self.publish_touched)
        self.executor = Executor(self.state, self.robot, self.events, self.broadcast_state, self.motion)

    def start_auto_motion_plan(self) -> bool:
        """動作計画を裏で始める（依頼を受けたとき）。始めたら True。
        「Plan（どの物をどこへ）」だけでは、腕が届くか・禁止区域を通らずに行けるかは分からないので、
        依頼の結果は動作計画まで済んでから見せる（Unity の CoGroundFuture）。"""
        if not self.auto_motion_plan or self.executor.mode == "running" or self.motion.status == "planning":
            return False
        plan = self.state.plan
        if plan is None or not any(s.status == "ok" and s.to is not None for s in plan.steps):
            return False

        async def run() -> None:
            try:
                for _ in range(10):
                    epoch = self.motion.epoch
                    await self.motion.plan(actor="auto")
                    if self.motion.epoch == epoch:
                        break  # 計画している間にシーケンスが編集されていたら、新しい順序でもう一度
            except Exception as e:  # noqa: BLE001 失敗は motion の status / error に出る。ここでは記録だけ
                logging.getLogger(__name__).warning("auto motion.plan failed: %s", e)

        self._auto_task = asyncio.get_running_loop().create_task(run())  # 参照を持っておく（途中で消されないように）
        return True

    async def start_execution(self, step_ids: list[str] | None = None, *, actor: str = "user", allow_unplanned: bool = False,
                              preview_id: str | None = None, revalidate: bool | None = None) -> None:
        """実行を始める。preview_id（住人が確認した予測の版）を渡すと、次を確かめてから始める:

          1. いまの予測がその版のままで、検証が済んでいる（編集のあと検証が終わるまで、古い After からは始めない）
          2. revalidate（省略すると true）なら、実行の直前に動作計画をやり直す（プレビューのあとで環境が変わったかもしれない）。
             動かす対象・順序・置き先が変わっていたら、始めずに断る。更新した予測は state.updated で届くので、
             住人が確認してから、新しい preview_id でもう一度呼ぶ
        """
        if preview_id is not None and not allow_unplanned:
            preview = self.motion.preview()
            if self.motion.status == "planning" or preview["status"] == "checking":
                raise ExecError("Still checking the plan. Wait for the check to finish")
            if preview["id"] != preview_id:
                raise ExecError("The predicted result changed after you looked at it. Check the updated After, then execute again")
            if preview["status"] != "ready":
                raise ExecError("Some steps aren't checked yet. Run the check again before executing")
            if self.executor.mode == "running":
                raise ExecError("Already running")
            if not preview["executable"]:
                raise ExecError("Nothing to execute: no object can be moved in this plan")
            if revalidate is None or revalidate:
                before = self.motion.outcome()
                try:
                    await self.motion.plan(actor="pre-exec")  # 順序どおりに全部（前の step の結果が、後ろの step の前提になる）
                except ValueError as e:
                    raise ExecError(f"Couldn't re-check before execution: {e}") from e
                if self.motion.status != "ready":
                    self.motion.notice = f"Couldn't re-check before execution: {self.motion.error}"
                    await self.publish_touched()
                    raise ExecError(self.motion.notice)
                after = self.motion.outcome()
                if after != before:
                    self.motion.notice = "The situation changed, so the plan was updated: " + "; ".join(_differences(before, after))
                    self.events.add("exec", actor, action="revalidation_changed", before=before, after=after)
                    await self.publish_touched()
                    raise ExecError(self.motion.notice + ". Check the updated After, then execute again")
        await self.executor.start(step_ids, actor=actor, allow_unplanned=allow_unplanned)

    async def publish_touched(self) -> None:
        self.state.touch()
        await self.broadcast_state()

    def snapshot(self) -> dict[str, Any]:
        """全体状態（シーン、ルール、Plan）に、動作計画の要約（motion）と実行の状態（execution）を足したもの。state.updated の中身。"""
        return {**self.state.snapshot(), "motion": self.motion.summary(), "execution": self.executor.snapshot()}

    async def broadcast_state(self) -> None:
        await self.hub.broadcast("state.updated", self.snapshot())

    async def publish_state(self) -> None:
        """現在の全体状態を全クライアントに送る。状態を変えたら必ず呼ぶ。"""
        logging.getLogger(__name__).info(
            "state v%d -> %d client(s)", self.state.version, self.hub.count
        )
        await self.broadcast_state()


def _differences(before: list[tuple[str, str | None, str]], after: list[tuple[str, str | None, str]]) -> list[str]:
    """実行前の再検証で、予測のどこが変わったか（住人に見せる文）。"""
    words = {"move": "will be moved", "stay_rule": "stays (household rule)", "stay_infeasible": "stays (can't be done)",
             "checking": "is being checked", "unverified": "is unverified"}
    old = {o: (to, state) for o, to, state in before}
    new = {o: (to, state) for o, to, state in after}
    out = []
    for o, (to, state) in new.items():
        if o not in old:
            out.append(f"{o} was added")
        elif old[o] != (to, state):
            out.append(f"{o} now {words.get(state, state)}" + (f" (to {to})" if state == "move" and to else ""))
    out.extend(f"{o} is no longer in the plan" for o in old if o not in new)
    if not out and [o for o, _, _ in before] != [o for o, _, _ in after]:
        out.append("the order changed")
    return out or ["the result changed"]
