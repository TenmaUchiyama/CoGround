from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from ..errors import ErrorCode, RpcError
from ..models import Rule
from ..rpc import RequestContext, Router

router = Router()


class SetRulesParams(BaseModel):
    rules: list[Rule] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_ids(self) -> SetRulesParams:
        ids = [r.id for r in self.rules]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            raise ValueError(f"Duplicate rule IDs: {dup}")
        return self


@router.method(
    "rules.set",
    params=SetRulesParams,
    description="片付けルール（属性 = 値 → 行き先）全体を置き換える（空のリストで消す）。収納先の義務として家庭ルールと一緒に持ち、"
    "ほかの家庭ルールは消さない。Plan を作り直し、全クライアントに state.updated が届く",
)
async def set_rules(ctx: RequestContext, p: SetRulesParams) -> dict[str, Any]:
    state = ctx.services.state
    clash = sorted({n.id for n in state.norms if n.origin != "tidy"} & {r.id for r in p.rules})
    if clash:
        raise RpcError(ErrorCode.INVALID_PARAMS, f"IDs collide with household rules (norms.set): {clash}")
    version = state.set_rules(p.rules)
    await ctx.services.publish_state()
    region_ids = {r.id for r in state.scene.regions}
    return {
        "version": version,
        "rules": len(p.rules),
        "steps": len(state.plan.steps) if state.plan else 0,
        # シーンがまだ届いていないだけかもしれないので、エラーにはしない
        "unknown_regions": sorted({r.target_region for r in p.rules} - region_ids),
    }
