"""ロボットの単体テスト（Web UI の「ロボット単体テスト」）。ルールの Plan も Executor も通さず、スキルを 1 つだけ動かす。

  robot.plan        pick（その場でつかむ）か navigate（Goal へ移動）を、動かさずに計画する。
                    結果は pick_place_server が /coground/task/plan_result に出すので、Unity の CoGroundTaskPlanPlayer が
                    Ghost で再生する（本番の motion.plan と同じ経路）。Web UI には時間軸（関節角を除く）を返す
  robot.pick        物体をつかんで持ち上げる。台車は動かさない（ロボットが机の前にいる前提。MoveIt の確認用）
  robot.place_back  持っている物を、つかんだ元の場所へ戻す
  robot.navigate    台車を Goal へ動かす（move_base。ROS は NAV=true で起動しておく）
  robot.cancel      動いているスキルを止める

robot.pick / robot.navigate は、同じ対象の計画（robot.plan）があれば plan_ref を付けて、計画した軌道をそのまま再生する
（pick_place_server が今の状態で使えるか確かめ、だめならその場で計画し直す。結果の mode が replay / replanned）。
計画の後に物体が 2 cm 以上動いていたら、計画は使わない（その場で計画する）。

ROS（rosbridge）のときは pick_place_server.py の /coground/skill/* と /coground/task/* を、代役（FakeRobot）のときはその代役を使う。
スキルは終わるまで返らない（phase を {phase, detail} で stream する）。request を中断すると、スキルも止める。
結果は {state: succeeded / failed / canceled / rejected, detail, mode, holding}。失敗も error ではなく ok の応答で返す。
Plan の実行中（exec が running）と動作計画の途中は断る。
"""

from __future__ import annotations

import asyncio
import itertools
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..errors import ErrorCode, RpcError
from ..motion import STALE_OBJECT
from ..robot import unity_pose_to_ros, unity_to_ros
from ..rpc import EmptyParams, RequestContext, Router

router = Router()
STEP_ID = "t1"
_versions = itertools.count(1)  # 計画ごとに変える（古い結果を捨てるため）


class PickParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_id: str = Field(min_length=1, description="つかむ物体の ID（シーンにある物。Unity の GameObject 名）")
    use_plan: bool = Field(default=True, description="同じ物体の計画（robot.plan）があれば、それを再生する")


class PlaceBackParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_id: str | None = Field(default=None, description="戻す物体。省略すると、いま持っている物")


class GoalParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float = Field(description="Goal の位置（Unity のワールド座標 X）[m]")
    z: float = Field(description="Goal の位置（Unity のワールド座標 Z）[m]")
    yaw_deg: float = Field(default=0.0, description="台車の正面の向き（Unity の流儀: 上から見て +Z から右回り）[度]")


class NavigateParams(GoalParams):
    use_plan: bool = Field(default=True, description="同じ Goal の計画（robot.plan）があれば、その計画に付けて送る")


class PlanParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill: Literal["pick", "navigate"]
    object_id: str | None = Field(default=None, description="pick: つかむ物体")
    x: float | None = Field(default=None, description="navigate: Goal（Unity の X）[m]")
    z: float | None = Field(default=None, description="navigate: Goal（Unity の Z）[m]")
    yaw_deg: float = Field(default=0.0, description="navigate: 向き（Unity の流儀）[度]")


def _check_free(ctx: RequestContext) -> None:
    services = ctx.services
    if services.executor.mode == "running":
        raise RpcError(ErrorCode.INVALID_STATE, "The Plan is executing (stop it first with exec.stop / exec.pause)")
    if services.motion.status == "planning":
        raise RpcError(ErrorCode.INVALID_STATE, "Motion planning in progress")


def _goal_pose(x: float, z: float, yaw_deg: float) -> list[float]:
    """Unity の (x, z, 右回りの yaw [度]) -> ROS の world の [x, y, yaw]"""
    rx, ry, _ = unity_to_ros((x, 0.0, z))
    a = -math.radians(yaw_deg)  # 右回り（Unity）→ 左回り（ROS）
    return [rx, ry, math.atan2(math.sin(a), math.cos(a))]


def _object(ctx: RequestContext, object_id: str):
    obj = next((o for o in ctx.services.state.scene.objects if o.id == object_id), None)
    if obj is None:
        raise RpcError(ErrorCode.INVALID_PARAMS, f"Object {object_id!r} is not in the scene")
    return obj


def _plan_ref(ctx: RequestContext, skill: str, *, object_id: str = "", pose: list[float] | None = None
              ) -> tuple[dict[str, Any] | None, str]:
    """使える計画があれば (plan_ref, "")、無ければ (None, 理由)。"""
    plan = ctx.services.test_plan
    if plan is None:
        return None, "no plan"
    if plan["skill"] != skill or plan["status"] != "ok":
        return None, "no plan" if plan["skill"] != skill else "couldn't be planned"
    if skill == "pick":
        if plan["object_id"] != object_id:
            return None, f"the plan is for {plan['object_id']}"
        obj = next((o for o in ctx.services.state.scene.objects if o.id == object_id), None)
        if obj is not None and plan["start"] is not None and math.dist(obj.position, plan["start"]) > STALE_OBJECT:
            return None, f"{object_id} moved after planning"
    if skill == "navigate" and pose is not None:
        if math.dist(pose[:2], plan["pose"][:2]) > 0.01 or abs(math.remainder(pose[2] - plan["pose"][2], math.tau)) > 0.02:
            return None, "different Goal from the plan"
    return {"plan_id": plan["plan_id"], "plan_version": plan["plan_version"], "step_id": STEP_ID}, ""


async def _run(ctx: RequestContext, skill: str, object_id: str, *, place: dict[str, Any] | None = None,
               pose: list[float] | None = None, plan_ref: dict[str, Any] | None = None, note: str = "") -> dict[str, Any]:
    services, robot = ctx.services, ctx.services.robot
    actor = ctx.session.actor
    services.events.add("skill", actor, action="start", skill=skill, object_id=object_id, pose=pose,
                        plan_ref=plan_ref, source="test")
    loop = asyncio.get_running_loop()
    pending: set[asyncio.Task[None]] = set()

    def on_phase(phase: str, detail: str) -> None:
        services.events.add("skill", actor, action="phase", skill=skill, object_id=object_id, phase=phase, source="test")
        task = loop.create_task(ctx.stream({"phase": phase, "detail": detail}))
        pending.add(task)
        task.add_done_callback(pending.discard)

    try:
        result = await robot.run_skill(skill, object_id, place, on_phase, pose=pose, plan_ref=plan_ref)
    except asyncio.CancelledError:
        await robot.cancel()  # request を中断したら、ロボットも止める
        raise
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    services.events.add("skill", actor, action="result", skill=skill, object_id=object_id, state=result.state,
                        detail=result.detail, mode=result.mode, source="test")
    if result.ok and plan_ref is not None:
        services.test_plan = None  # 使い終わった（ほかの動きでずれた計画は、pick_place_server が再生の前に見つけて計画し直す）
    await services.publish_touched()  # holding / busy の変化を全クライアントへ
    return {"skill": skill, "object_id": object_id, "state": result.state, "detail": result.detail,
            "mode": result.mode, "planned": plan_ref is not None, "plan_note": note, "holding": robot.holding}


@router.method("robot.plan", params=PlanParams, streams=True,
               description="（単体テスト）pick（その場でつかむ）か navigate（Goal へ移動）を、動かさずに計画する。"
               "Unity の Ghost（CoGroundTaskPlanPlayer）が再生する。途中経過を {detail} で stream する")
async def plan(ctx: RequestContext, p: PlanParams) -> dict[str, Any]:
    _check_free(ctx)
    services, robot = ctx.services, ctx.services.robot
    services.test_plan = None
    if p.skill == "pick":
        if not p.object_id:
            raise RpcError(ErrorCode.INVALID_PARAMS, "pick requires object_id")
        if robot.holding:
            raise RpcError(ErrorCode.INVALID_STATE, f"Holding {robot.holding}, so can't plan (return it first)")
        obj = _object(ctx, p.object_id)
        start = unity_pose_to_ros(obj.pose)
        step = {"step_id": STEP_ID, "kind": "pick", "object": p.object_id, "stay": True, "start": start, "place": None}
        target, pose = p.object_id, None
    else:
        if p.x is None or p.z is None:
            raise RpcError(ErrorCode.INVALID_PARAMS, "navigate requires x and z")
        pose = _goal_pose(p.x, p.z, p.yaw_deg)
        step = {"step_id": STEP_ID, "kind": "navigate", "object": "", "pose": pose}
        target, obj = f"({p.x:.2f}, {p.z:.2f}) {p.yaw_deg:.0f}°", None

    plan_id = f"test_{p.skill}"
    version = next(_versions)
    request = {"plan_id": plan_id, "plan_version": version, "steps": [step]}
    services.events.add("motion", ctx.session.actor, action="plan", plan_id=plan_id, version=version,
                        skill=p.skill, target=target, source="test")

    async def progress(data: dict[str, Any]) -> None:
        await ctx.stream({"detail": data.get("detail", "")})

    result = await robot.plan_motion(request, progress)
    steps = result.get("steps") or []
    s = steps[0] if steps else {"status": "infeasible", "reason": result.get("error") or "empty result"}
    status = "ok" if not result.get("error") and s.get("status") == "ok" else "infeasible"
    reason = result.get("error") or s.get("reason", "")
    services.test_plan = {
        "skill": p.skill, "object_id": p.object_id or "", "pose": pose, "status": status,
        "start": list(obj.position) if obj is not None else None,
        "plan_id": result.get("plan_id", plan_id), "plan_version": result.get("plan_version", version),
    }
    services.events.add("motion", "system", action="result", plan_id=plan_id, version=version, status=status,
                        reason=reason, source="test")
    timeline = result.get("timeline") or None
    if timeline is not None:
        timeline = {k: v for k, v in timeline.items() if k not in ("joints", "joint_names")}  # 関節角は Unity が使う
    return {"skill": p.skill, "target": target, "status": status, "reason": reason,
            "duration": timeline["duration"] if timeline else 0.0,
            "stops": s.get("stops", {}), "stop_source": s.get("stop_source", {}), "timeline": timeline}


@router.method("robot.pick", params=PickParams, streams=True,
               description="（単体テスト）物体をつかんで持ち上げる。台車は動かさない（ロボットが机の前にいる前提）。"
               "同じ物体の robot.plan があれば、その軌道を再生する。phase を stream する")
async def pick(ctx: RequestContext, p: PickParams) -> dict[str, Any]:
    _check_free(ctx)
    _object(ctx, p.object_id)
    ref, note = _plan_ref(ctx, "pick", object_id=p.object_id) if p.use_plan else (None, "not using a plan")
    return await _run(ctx, "pick", p.object_id, plan_ref=ref, note=note)


@router.method("robot.place_back", params=PlaceBackParams, streams=True,
               description="（単体テスト）持っている物を、つかんだ元の場所へ戻す。台車は動かさない")
async def place_back(ctx: RequestContext, p: PlaceBackParams) -> dict[str, Any]:
    _check_free(ctx)
    object_id = p.object_id or ctx.services.robot.holding
    if not object_id:
        raise RpcError(ErrorCode.INVALID_STATE, "Not holding anything")
    return await _run(ctx, "place", object_id)


@router.method("robot.navigate", params=NavigateParams, streams=True,
               description="（単体テスト）台車を Goal へ動かす（move_base。ROS は NAV=true で起動しておく）。"
               "位置と向きは Unity のワールド座標で渡す")
async def navigate(ctx: RequestContext, p: NavigateParams) -> dict[str, Any]:
    _check_free(ctx)
    pose = _goal_pose(p.x, p.z, p.yaw_deg)
    ref, note = _plan_ref(ctx, "navigate", pose=pose) if p.use_plan else (None, "not using a plan")
    return await _run(ctx, "navigate", "", pose=pose, plan_ref=ref, note=note)


@router.method("robot.cancel", description="（単体テスト）動いているスキルを止める。Plan の実行中は exec.stop を使う")
async def cancel(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    if ctx.services.executor.mode == "running":
        raise RpcError(ErrorCode.INVALID_STATE, "The Plan is executing (use exec.stop)")
    await ctx.services.robot.cancel()
    return {"robot": ctx.services.robot.snapshot()}
