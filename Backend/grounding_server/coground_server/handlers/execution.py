"""Plan の実行を操作する method（exec.*）と、記録を読む method。中身は executor.py。

どの method も、終わると全クライアントに state.updated が届く（実行の状態は state の execution に入っている）。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..errors import ErrorCode, RpcError
from ..executor import ExecError
from ..robot import FakeRobot
from ..rpc import EmptyParams, RequestContext, Router

router = Router()


async def _do(ctx: RequestContext, action) -> dict[str, Any]:
    """Executor の命令を呼び、いまの実行の状態を返す。受けられない命令は invalid_state にする。"""
    try:
        await action
    except ExecError as e:
        raise RpcError(ErrorCode.INVALID_STATE, str(e), {"execution": ctx.services.executor.snapshot()})
    return {"version": ctx.services.state.version, "execution": ctx.services.executor.snapshot()}


class StartParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_ids: list[str] = Field(default_factory=list, description="実行する step（この順に）。空なら Plan の ok の step を全部")
    allow_unplanned: bool = Field(
        default=False, description="動作計画（motion.plan）が無い・古い step も動かす（移動はせず、その場で腕を計画する）")
    preview_id: str | None = Field(
        default=None, description="住人が確認した予測の版（state の motion.preview.id）。渡すと、いまの予測がその版のままか確かめ、"
        "違えば始めない（シーケンスを編集したあと、検証が終わる前の古い After から実行しないため）")
    revalidate: bool | None = Field(
        default=None, description="preview_id を渡したとき、実行の直前に動作計画をやり直す（既定 true）。"
        "動かす対象・順序・置き先が変わったら、始めずに断る（更新した予測を確認して、新しい preview_id で呼び直す）")


class StepParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str = Field(min_length=1)


class PolicyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm: Literal["auto", "each_step"] | None = Field(
        default=None, description="auto = 確認なしで進む / each_step = 物をつかむ前に毎回 exec.confirm を待つ")
    on_failure: Literal["pause", "continue"] | None = Field(
        default=None, description="step が失敗したとき: pause = 止まって待つ / continue = 次の step へ進む")


@router.method("exec.start", params=StartParams,
               description="Plan の実行を始める（先に motion.plan で動作計画を作る）。step_ids を渡すと、その step だけをその順に実行する")
async def start(ctx: RequestContext, p: StartParams) -> dict[str, Any]:
    return await _do(ctx, ctx.services.start_execution(p.step_ids, actor=ctx.session.actor, allow_unplanned=p.allow_unplanned,
                                                       preview_id=p.preview_id, revalidate=p.revalidate))


@router.method("exec.pause", description="いまの動き（つかむ、または置く）が終わったら止まる。物を持ったまま止まることもある")
async def pause(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    return await _do(ctx, ctx.services.executor.pause(actor=ctx.session.actor))


@router.method("exec.stop", description="いますぐ止める（動いている途中でも）。物を持っていれば持ったまま。exec.resume で続きから")
async def stop(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    return await _do(ctx, ctx.services.executor.stop(actor=ctx.session.actor))


@router.method("exec.resume", description="止まった所から続ける。物を持っていれば、置くところから（行き先はいまの Plan のもの）")
async def resume(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    return await _do(ctx, ctx.services.executor.resume(actor=ctx.session.actor))


@router.method("exec.skip", params=StepParams,
               description="step を飛ばす。いま実行中の step なら止めて、物を持っていれば元の場所へ戻す")
async def skip(ctx: RequestContext, p: StepParams) -> dict[str, Any]:
    return await _do(ctx, ctx.services.executor.skip(p.step_id, actor=ctx.session.actor))


@router.method("exec.retry", params=StepParams,
               description="失敗した・飛ばした・終わった step の記録を消して、もう一度実行できるようにする")
async def retry(ctx: RequestContext, p: StepParams) -> dict[str, Any]:
    return await _do(ctx, ctx.services.executor.retry(p.step_id, actor=ctx.session.actor))


@router.method("exec.confirm", description="確認待ちの step（execution.waiting_confirm）を進める")
async def confirm(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    return await _do(ctx, ctx.services.executor.confirm_step(actor=ctx.session.actor))


@router.method("exec.set_policy", params=PolicyParams, description="確認の方針（confirm）と、失敗したときの方針（on_failure）を変える")
async def set_policy(ctx: RequestContext, p: PolicyParams) -> dict[str, Any]:
    return await _do(ctx, ctx.services.executor.set_policy(p.confirm, p.on_failure, actor=ctx.session.actor))


@router.method("exec.reset", description="実行の記録（done / failed / skipped）を全部消す。実行中はできない")
async def reset(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    return await _do(ctx, ctx.services.executor.reset(actor=ctx.session.actor))


class InjectFailureParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill: Literal["", "pick", "place"] = Field(default="", description="失敗させるスキル。空ならどれでも")
    detail: str = "Failed on purpose"


@router.method("exec.inject_failure", params=InjectFailureParams,
               description="次のスキルを途中で失敗させる（立て直しを試すため）。ROS なしの代役のロボット（fake）のときだけ使える")
async def inject_failure(ctx: RequestContext, p: InjectFailureParams) -> dict[str, Any]:
    robot = ctx.services.robot
    if not isinstance(robot, FakeRobot):
        raise RpcError(ErrorCode.INVALID_STATE, f"Not the stand-in robot (robot = {robot.kind})")
    robot.inject_failure(p.skill, p.detail)
    return {"pending_failures": len(robot.fail_next)}


class MotionPlanParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_ids: list[str] = Field(default_factory=list, description="計画する step（この順に）。空なら Plan の ok の step を全部")


@router.method("motion.plan", params=MotionPlanParams, streams=True,
               description="動作計画（Plan ボタン）: 移動 → ピック → 移動 → プレース を、動かさずに計画する。"
               "途中経過を {step_id, detail} で stream する。結果の要約は state の motion、時間軸は motion.get")
async def motion_plan(ctx: RequestContext, p: MotionPlanParams) -> dict[str, Any]:
    services = ctx.services
    if services.executor.mode == "running":
        raise RpcError(ErrorCode.INVALID_STATE, "Can't plan while executing (stop first)")
    try:
        return await services.motion.plan(p.step_ids or None, actor=ctx.session.actor, on_progress=ctx.stream)
    except ValueError as e:
        raise RpcError(ErrorCode.INVALID_STATE, str(e))


@router.method("motion.get", description="動作計画の時間軸（通しで再生するためのデータ）。無ければ null")
async def motion_get(ctx: RequestContext, _: EmptyParams) -> dict[str, Any] | None:
    return ctx.services.motion.timeline()


@router.method("motion.clear", description="動作計画を捨てる")
async def motion_clear(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    if ctx.services.motion.status == "planning":
        raise RpcError(ErrorCode.INVALID_STATE, "Planning in progress")
    ctx.services.motion.clear()
    await ctx.services.publish_touched()
    return {"motion": ctx.services.motion.summary()}


class InfeasibleParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_ids: list[str] = Field(default_factory=list, description="計画で infeasible にする物体。空で元に戻す")


@router.method("motion.inject_infeasible", params=InfeasibleParams,
               description="動作計画で、この物体の step を計画できないことにする（代役のロボットのときだけ）")
async def inject_infeasible(ctx: RequestContext, p: InfeasibleParams) -> dict[str, Any]:
    robot = ctx.services.robot
    if not isinstance(robot, FakeRobot):
        raise RpcError(ErrorCode.INVALID_STATE, f"Not the stand-in robot (robot = {robot.kind})")
    robot.infeasible = set(p.object_ids)
    return {"infeasible": sorted(robot.infeasible)}


class ObstaclesParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    polygons: list[list[tuple[float, float]]] = Field(
        default_factory=list, description="床の障害物（Unity のワールド座標の [x, z] の多角形）。空で元に戻す")


@router.method("motion.inject_obstacles", params=ObstaclesParams,
               description="台車が避ける床の障害物を置く（代役のロボットのときだけ。本物では Unity の地図が担う）。"
               "プレビューのあとで経路をふさぐ、などを試すのに使う")
async def inject_obstacles(ctx: RequestContext, p: ObstaclesParams) -> dict[str, Any]:
    robot = ctx.services.robot
    if not isinstance(robot, FakeRobot):
        raise RpcError(ErrorCode.INVALID_STATE, f"Not the stand-in robot (robot = {robot.kind})")
    # Unity (x, z) -> ROS (x = z, y = -x)
    robot.obstacles = [[[z, -x] for x, z in poly] for poly in p.polygons if len(poly) >= 3]
    return {"obstacles": len(robot.obstacles)}


class IdentifyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor: Literal["user", "llm", "script"] = Field(description="この接続の操作を、だれのものとして記録するか")


@router.method("session.identify", params=IdentifyParams, description="この接続がだれか（user / llm / script）を名乗る。既定は user")
async def identify(ctx: RequestContext, p: IdentifyParams) -> dict[str, Any]:
    ctx.session.actor = p.actor
    return {"session_id": ctx.session.id, "actor": p.actor}


class TailParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n: int = Field(default=50, ge=1, le=500)
    type: Literal["rpc", "exec", "skill", "motion"] | None = Field(default=None, description="この種類だけ")


@router.method("log.tail", params=TailParams, description="直近の記録（だれが何を呼んだか、実行とスキルの経過）を返す")
async def tail(ctx: RequestContext, p: TailParams) -> dict[str, Any]:
    return {"events": ctx.services.events.tail(p.n, p.type)}
