from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from ..errors import ErrorCode, RpcError
from ..llm import LlmError
from ..llm.compile_rule import compile_rules
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
            raise ValueError(f"rule の ID が重複している: {dup}")
        return self


@router.method(
    "rules.set",
    params=SetRulesParams,
    description="ルール全体を置き換える（空のリストで消す）。Plan を作り直し、全クライアントに state.updated が届く",
)
async def set_rules(ctx: RequestContext, p: SetRulesParams) -> dict[str, Any]:
    state = ctx.services.state
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


class CompileParams(BaseModel):
    text: str = Field(min_length=1, description="自然言語の指示。例: 食器はシンクに、燃えるごみは燃えるごみ箱に")
    mode: Literal["append", "replace"] = Field(default="append", description="いまのルールに足すか、置き換えるか")
    apply: bool = Field(default=True, description="false なら、作ったルールを返すだけで状態は変えない")


@router.method(
    "rules.compile",
    params=CompileParams,
    streams=True,
    description="自然言語の指示を LLM でルールにする（数秒かかる。cancel で止まる）。apply なら Plan も作り直す",
)
async def compile_rule(ctx: RequestContext, p: CompileParams) -> dict[str, Any]:
    state = ctx.services.state
    existing = [] if p.mode == "replace" else list(state.rules)
    await ctx.stream({"stage": "llm"})
    try:
        rules, unresolved = await compile_rules(ctx.services.llm, p.text, state.scene, {r.id for r in existing})
    except LlmError as e:
        raise RpcError(ErrorCode.LLM_FAILED, str(e)) from e

    result: dict[str, Any] = {
        "rules": [r.model_dump(mode="json") for r in rules],
        "unresolved": unresolved,  # ルールにできなかった部分と理由
        "applied": False,
    }
    if p.apply and rules:
        result["version"] = state.set_rules([*existing, *rules])
        result["steps"] = len(state.plan.steps) if state.plan else 0
        result["applied"] = True
        await ctx.services.publish_state()
    return result
