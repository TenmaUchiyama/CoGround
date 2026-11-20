"""依頼（task.*）、家庭ルール（norms.*）、家の時計（clock.*）。

依頼をすると、対象の物体がそのとき決まり、行ごとに家庭ルールを判定して Plan を作る（norms/planner.py）。
依頼がある間、Plan はその行から作る。task.close で、依頼なしの作り方（旧 Rule と手の指定）に戻る。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from ..errors import ErrorCode, RpcError
from ..llm import LlmError
from ..llm.compile_rule import interpret_task
from ..models import AttributeValue
from ..norms.model import NormRule
from ..norms.report import build_report
from ..rpc import EmptyParams, RequestContext, Router

router = Router()


class TaskRequestParams(BaseModel):
    text: str = Field(min_length=1, description="依頼の言葉。例: 机の上のものを全部片づけて")
    requester: str | None = Field(default=None, description="依頼者の人物 ID（分からなければ省略）")
    source_region: str | None = Field(
        default=None, description="この領域にある物（role = item）すべてを対象にする。省略すると、シーンに 1 つだけある机")
    object_ids: list[str] | None = Field(default=None, description="対象を直接指定する（source_region より先）")
    interpret: bool = Field(
        default=False, description="true なら、依頼の言葉から対象の物体を LLM に決めさせる（数秒かかる。"
        "object_ids と source_region は使わない）。決められない部分は unresolved で返す")


@router.method(
    "task.request",
    params=TaskRequestParams,
    description="片付けを依頼する。対象の物体はここで決まり、あとでシーンが変わっても選び直さない。"
    "既定では言葉を解釈せず、source_region（省略すると机）にある物すべてを対象にする。"
    "interpret = true なら、言葉から対象を LLM に決めさせる。前の依頼は閉じる",
)
async def request_task(ctx: RequestContext, p: TaskRequestParams) -> dict[str, Any]:
    state = ctx.services.state
    scene = state.scene
    source = p.source_region
    unresolved: list[str] = []
    if p.interpret:
        try:
            answer = await interpret_task(ctx.services.llm, p.text, scene)
        except LlmError as e:
            raise RpcError(ErrorCode.LLM_FAILED, str(e)) from e
        object_ids, source, unresolved = answer.object_ids, answer.source_region, answer.unresolved
        if not object_ids:
            raise RpcError(ErrorCode.INVALID_STATE, "Couldn't decide the target objects from the request words", {"unresolved": unresolved})
    elif p.object_ids is not None:
        object_ids = list(p.object_ids)
    else:
        if source is None:
            tables = [o.id for o in scene.objects if o.category == "table" and any(r.id == o.id for r in scene.regions)]
            if len(tables) != 1:
                raise RpcError(ErrorCode.INVALID_PARAMS, "There isn't exactly one desk, so specify source_region",
                               {"tables": tables, "regions": [r.id for r in scene.regions]})
            source = tables[0]
        elif source not in {r.id for r in scene.regions}:
            raise RpcError(ErrorCode.INVALID_PARAMS, f"Zone {source!r} is not in the scene",
                           {"regions": [r.id for r in scene.regions]})
        object_ids = [o.id for o in scene.objects if o.role == "item" and o.region_id == source]
    if not object_ids:
        raise RpcError(ErrorCode.INVALID_STATE, "No target objects", {"source_region": source})
    try:
        task = state.open_task(p.text, object_ids, requester=p.requester, source_region=source)
    except ValueError as e:
        raise RpcError(ErrorCode.INVALID_PARAMS, str(e)) from e
    ctx.services.events.add("task", ctx.session.actor, action="request", task_id=task.id, objects=object_ids,
                            interpreted=p.interpret, unresolved=unresolved)
    await ctx.services.publish_state()
    motion_planning = ctx.services.start_auto_motion_plan()  # 続けて動作計画（結果は state.updated の motion）
    return {"version": state.version, "task": task.model_dump(mode="json"), "counts": task.counts(),
            "steps": len(state.plan.steps) if state.plan else 0, "unresolved": unresolved,
            "motion_planning": motion_planning}


@router.method("task.get", description="いまの依頼（いちばん新しいもの）と、状態ごとの件数")
async def get_task(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    task = ctx.services.state.task
    return {"task": task.model_dump(mode="json") if task else None, "counts": task.counts() if task else None}


@router.method("task.close", description="いまの依頼を閉じる（記録は残る）。Plan は、依頼なしの作り方に戻る")
async def close_task(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    state = ctx.services.state
    if state.active_task is None:
        raise RpcError(ErrorCode.INVALID_STATE, "No open request")
    version = state.close_task()
    await ctx.services.publish_state()
    return {"version": version}


class SetNormsParams(BaseModel):
    norms: list[NormRule] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> SetNormsParams:
        ids = [n.id for n in self.norms]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            raise ValueError(f"Duplicate rule IDs: {dup}")
        unknown = sorted({n.exception_of for n in self.norms if n.exception_of} - set(ids))
        if unknown:
            raise ValueError(f"exception_of refers to missing rules: {unknown}")
        return self


@router.method(
    "norms.set",
    params=SetNormsParams,
    description="家庭ルール（義務・禁止・許可）のうち、片付けルール（rules.set で入れたもの）以外を置き換える（空のリストで消す）。"
    "判定のときは片付けルールも同じ家庭ルールとして使う。Plan を作り直す",
)
async def set_norms(ctx: RequestContext, p: SetNormsParams) -> dict[str, Any]:
    state = ctx.services.state
    rule_ids = {n.id for n in state.norms if n.origin == "tidy"}
    clash = sorted(rule_ids & {n.id for n in p.norms})
    if clash:
        raise RpcError(ErrorCode.INVALID_PARAMS, f"IDs collide with tidy rules (rules.set): {clash}")
    version = state.set_norms(p.norms)
    await ctx.services.publish_state()
    return {"version": version, "norms": len(p.norms), "steps": len(state.plan.steps) if state.plan else 0}


class ClockSetParams(BaseModel):
    time: str = Field(min_length=1, description="家の時計の時刻。HH:MM（今日のその時刻）か ISO 8601")
    freeze: bool = Field(default=False, description="true なら、その時刻で止める（clock.advance で進める）")


@router.method("clock.get", description="家の時計（ルールの「18 時以降」などを判定する時計）")
async def get_clock(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    return ctx.services.state.clock.snapshot()


@router.method("clock.set", params=ClockSetParams,
               description="家の時計を合わせる（デモ・評価用）。判定をやり直し、依頼があれば Plan を作り直す")
async def set_clock(ctx: RequestContext, p: ClockSetParams) -> dict[str, Any]:
    clock = ctx.services.state.clock
    try:
        t = clock.at(p.time) if len(p.time) <= 5 else datetime.fromisoformat(p.time)
    except ValueError as e:
        raise RpcError(ErrorCode.INVALID_PARAMS, f"Can't parse the time: {p.time!r} (HH:MM or ISO 8601)") from e
    (clock.freeze if p.freeze else clock.set)(t)
    ctx.services.events.add("clock", ctx.session.actor, action="set", time=clock.now().isoformat(), freeze=p.freeze)
    ctx.services.state.replan()
    await ctx.services.publish_state()
    return clock.snapshot()


class ClockAdvanceParams(BaseModel):
    seconds: float = Field(description="進める秒数（負なら戻す）")


@router.method("clock.advance", params=ClockAdvanceParams, description="家の時計を進める（デモ・評価用）")
async def advance_clock(ctx: RequestContext, p: ClockAdvanceParams) -> dict[str, Any]:
    clock = ctx.services.state.clock
    clock.advance(p.seconds)
    ctx.services.state.replan()
    await ctx.services.publish_state()
    return clock.snapshot()


@router.method("clock.reset", description="家の時計を実時刻に戻す")
async def reset_clock(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    clock = ctx.services.state.clock
    clock.reset()
    ctx.services.state.replan()
    await ctx.services.publish_state()
    return clock.snapshot()


@router.method("task.report", description="いまの依頼の結果を、住人に伝える形で返す: 物体ごとの結果と理由（根拠にした取り決めの原文）、"
               "件数、訂正の前後で変わった項目")
async def report_task(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    state = ctx.services.state
    if state.task is None:
        raise RpcError(ErrorCode.INVALID_STATE, "No request")
    return build_report(state.task, state.all_norms(), holds=ctx.services.executor.monitor.snapshot()["holds"],
                        objects=state.scene.objects)


class SetAttributeParams(BaseModel):
    object_id: str = Field(min_length=1)
    key: str = Field(min_length=1, description="属性のキー（fragile など。taxonomy.ATTRIBUTES）")
    value: AttributeValue | None = Field(default=None, description="訂正した値。null なら訂正を取り消す（届いた値に戻す）")


@router.method(
    "objects.set_attribute",
    params=SetAttributeParams,
    description="住人が物体の属性を訂正する（例: この皿は割れ物ではない）。訂正は scene.update のあとも効く。"
    "依頼があれば判定をやり直し、訂正の前後で変わった行と項目（changes）を返す",
)
async def set_attribute(ctx: RequestContext, p: SetAttributeParams) -> dict[str, Any]:
    state = ctx.services.state
    try:
        correction = state.set_attribute(p.object_id, p.key, p.value)
    except ValueError as e:
        raise RpcError(ErrorCode.INVALID_PARAMS, str(e)) from e
    ctx.services.events.add("correction", ctx.session.actor, action="set_attribute", object_id=p.object_id, key=p.key,
                            value=p.value, changes=len(correction.changes))
    await ctx.services.publish_state()
    task = state.task
    return {"version": state.version, "correction": correction.model_dump(mode="json"),
            "counts": task.counts() if task else None}
