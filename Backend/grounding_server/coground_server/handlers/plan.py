from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..errors import ErrorCode, RpcError
from ..rpc import RequestContext, Router

router = Router()


class PlaceParams(BaseModel):
    object_id: str = Field(min_length=1, description="運ぶ物体の ID（シーンにある物）")
    target_region: str = Field(min_length=1, description="行き先の領域の ID（place_zone を持つ物体の ID など）")


@router.method(
    "plan.place",
    params=PlaceParams,
    description="物体の行き先を手で指定する。ルールは見ない（合っているかも確かめない）。"
    "Plan を作り直し、全クライアントに state.updated が届く。物体がその領域に入ったら指定は消える",
)
async def place(ctx: RequestContext, p: PlaceParams) -> dict[str, Any]:
    state = ctx.services.state
    obj = next((o for o in state.scene.objects if o.id == p.object_id), None)
    if obj is None:
        raise RpcError(ErrorCode.INVALID_PARAMS, f"Object {p.object_id!r} is not in the scene",
                       {"objects": [o.id for o in state.scene.objects]})
    region_ids = [r.id for r in state.scene.regions]
    if p.target_region not in region_ids:
        raise RpcError(ErrorCode.INVALID_PARAMS, f"Zone {p.target_region!r} is not in the scene", {"regions": region_ids})
    if p.target_region == p.object_id:
        raise RpcError(ErrorCode.INVALID_PARAMS, "An object can't be placed in its own zone")

    version = state.set_placement(p.object_id, p.target_region)
    await ctx.services.publish_state()
    step = next((s for s in state.plan.steps if s.object_id == p.object_id), None) if state.plan else None
    return {
        "version": version,
        "already_there": step is None,  # もうその領域にあるので、何もしない（指定も残さない）
        "step": step.model_dump(mode="json") if step else None,
    }


class UnplaceParams(BaseModel):
    object_id: str | None = Field(default=None, description="指定を消す物体の ID。省略すると全部消す")


@router.method(
    "plan.unplace",
    params=UnplaceParams,
    description="手で指定した行き先を消す（object_id を省略すると全部）。Plan を作り直す",
)
async def unplace(ctx: RequestContext, p: UnplaceParams) -> dict[str, Any]:
    state = ctx.services.state
    version = state.clear_placements(p.object_id)
    await ctx.services.publish_state()
    return {"version": version, "placements": len(state.placements)}
