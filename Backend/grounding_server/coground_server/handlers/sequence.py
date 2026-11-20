"""シーケンスの編集（sequence.*）: 住人が、ロボットの提案した作業の順序を足す・外す・並べ替える。

住人が決めるのは「何を、どの順で、どこへ」。変えたら、最初に影響を受ける step 以降の検証結果を未確認に戻し
（motion.invalidate）、動作計画（検証）を自動でやり直す。検証が終わるまで、古い After からは実行を始められない
（exec.start の preview_id）。step の位置（index）は、いまの Plan の step の並びで数える（0 始まり）。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..errors import ErrorCode, RpcError
from ..rpc import RequestContext, Router

router = Router()


class AddParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_id: str = Field(min_length=1, description="運ぶ物体")
    target_region: str | None = Field(
        default=None, description="置き先の領域。収納先を決めるルールと照合する（合わなければ、その step は保留になり理由が付く）。"
        "省略すると、ルールが決める")
    index: int | None = Field(default=None, ge=0, description="挿入する位置（この位置の step の前）。省略すると最後")


class RemoveParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_id: str = Field(min_length=1)


class MoveParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_id: str = Field(min_length=1)
    index: int = Field(ge=0, description="動かしたあとの位置")


class ReorderParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_ids: list[str] = Field(min_length=1, description="新しい順序（いまの step の物体を並べ替えたもの）")


async def _edit(ctx: RequestContext, what: str, change, **data: Any) -> dict[str, Any]:
    services = ctx.services
    if services.executor.mode == "running":
        raise RpcError(ErrorCode.INVALID_STATE, "Can't edit the sequence while executing (stop first)")
    try:
        first = change()
    except ValueError as e:
        raise RpcError(ErrorCode.INVALID_PARAMS, str(e)) from e
    services.motion.invalidate(first)
    services.events.add("task", ctx.session.actor, action=f"sequence_{what}", first_affected=first, **data)
    await services.publish_state()
    rechecking = services.start_auto_motion_plan()
    plan = services.state.plan
    return {"version": services.state.version, "first_affected": first, "rechecking": rechecking,
            "steps": [{"step_id": s.id, "object_id": s.object_id, "to_region": s.to.region_id if s.to else None,
                       "status": s.status, "message": s.message} for s in (plan.steps if plan else [])],
            "preview": services.motion.preview()}


@router.method("sequence.add", params=AddParams,
               description="物体を運ぶ step を足す（対象、置き先、挿入位置）。家庭ルールで触れない物や、置き先がルールに合わない物は、"
               "step は入るが保留になり、理由が付く。影響を受ける step 以降を検証し直す")
async def add(ctx: RequestContext, p: AddParams) -> dict[str, Any]:
    state = ctx.services.state
    return await _edit(ctx, "add", lambda: state.sequence_add(p.object_id, p.target_region, p.index),
                       object_id=p.object_id, target_region=p.target_region, index=p.index)


@router.method("sequence.remove", params=RemoveParams,
               description="step を外す（その物体は動かさない）。残りの順序と予測を更新する")
async def remove(ctx: RequestContext, p: RemoveParams) -> dict[str, Any]:
    state = ctx.services.state
    return await _edit(ctx, "remove", lambda: state.sequence_remove(p.object_id), object_id=p.object_id)


@router.method("sequence.move", params=MoveParams, description="step を 1 つ、別の位置へ動かす（ほかの順序は保つ）")
async def move(ctx: RequestContext, p: MoveParams) -> dict[str, Any]:
    state = ctx.services.state

    def change() -> int:
        order = [s.object_id for s in state.plan.steps] if state.plan else []
        if p.object_id not in order:
            raise ValueError(f"{p.object_id} is not in the sequence")
        order.remove(p.object_id)
        order.insert(min(p.index, len(order)), p.object_id)
        return state.sequence_reorder(order)

    return await _edit(ctx, "move", change, object_id=p.object_id, index=p.index)


@router.method("sequence.reorder", params=ReorderParams,
               description="step の順序をまとめて変える（順序変更の提案 motion.preview.suggestion.order を採用するときにも使う）")
async def reorder(ctx: RequestContext, p: ReorderParams) -> dict[str, Any]:
    state = ctx.services.state
    return await _edit(ctx, "reorder", lambda: state.sequence_reorder(p.object_ids), object_ids=p.object_ids)
