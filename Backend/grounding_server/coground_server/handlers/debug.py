from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..errors import RpcError
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
    message: str = "わざと失敗した"


@router.method("debug.fail", params=FailParams, description="エラー応答の確認用：必ず失敗する")
async def fail(ctx: RequestContext, p: FailParams) -> None:
    raise RpcError(p.code, p.message)
