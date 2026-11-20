from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ..errors import ErrorCode, RpcError
from ..llm import LlmError
from ..rpc import EmptyParams, RequestContext, Router

router = Router()


class Pong(BaseModel):
    reply: str


@router.method("llm.ping", description="LLM に届くかの確認用：短い答えを 1 つ返させる（数秒かかる）")
async def ping(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    try:
        pong = await ctx.services.llm.generate(
            name="ping", system="This is a connection check.", prompt='Return with only "pong" in reply.', output=Pong
        )
    except LlmError as e:
        raise RpcError(ErrorCode.LLM_FAILED, str(e)) from e
    return {"reply": pong.reply}
