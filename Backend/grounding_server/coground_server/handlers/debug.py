from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..errors import ErrorCode, RpcError
from ..robot import FakeRobot
from ..rpc import RequestContext, Router

router = Router()


class CountParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: int = Field(default=5, ge=0, le=1000)
    interval: float = Field(default=0.2, ge=0.0, le=10.0, description="秒")


@router.method(
    "debug.count",
    params=CountParams,
    streams=True,
    description="ストリームの確認用：{i, of} を count 回 stream で送ってから応答する。cancel で止まる",
)
async def count(ctx: RequestContext, p: CountParams) -> dict[str, Any]:
    for i in range(p.count):
        await ctx.stream({"i": i, "of": p.count})
        await asyncio.sleep(p.interval)
    return {"done": p.count}


class FailParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = "debug_failure"
    message: str = "Failed on purpose"


@router.method("debug.fail", params=FailParams, description="エラー応答の確認用：必ず失敗する")
async def fail(ctx: RequestContext, p: FailParams) -> None:
    raise RpcError(p.code, p.message)


class ObservePlacementParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: str = Field(default="auto", min_length=1,
                      description="auto: 計画した置き先で観測される / none: 観測が来ない / 領域の ID: その領域で観測される（配置先違い）")


@router.method("debug.observe_placement", params=ObservePlacementParams,
               description="置いたあとの配置先の観測をどう返すかを決める（配置先違い・未確認を試すため）。"
               "ROS なしの代役のロボット（fake）のときだけ使える")
async def observe_placement(ctx: RequestContext, p: ObservePlacementParams) -> dict[str, Any]:
    robot = ctx.services.robot
    if not isinstance(robot, FakeRobot):
        raise RpcError(ErrorCode.INVALID_STATE, f"Not the stand-in robot (robot = {robot.kind})")
    regions = [r.id for r in ctx.services.state.scene.regions]
    if p.mode not in ("auto", "none") and p.mode not in regions:
        raise RpcError(ErrorCode.INVALID_PARAMS, f"Zone {p.mode!r} is not in the scene", {"regions": regions})
    robot.placement_observation = p.mode
    return {"mode": p.mode}
