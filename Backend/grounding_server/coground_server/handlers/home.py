"""家庭ルールのための入力: 領域（zones.*）、人の位置（people.update）、ルールの訂正と登録（rules.update /
rules.add_exception / norms.compile / rules.confirm）。

訂正（rules.update / zones.update / rules.add_exception）は、objects.set_attribute と同じく、
判定をやり直して「訂正の前後で変わった行と項目」（correction.changes）を返す。
経路の判定（領域への進入の禁止）は動作計画が出すので、訂正のあとは motion.plan をやり直す。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..errors import ErrorCode, RpcError
from ..llm import LlmError
from ..llm.compile_rule import compile_norms
from ..models import Person, RegionBox, RuleCondition, SceneRegion, Vec3
from ..norms.model import NormRule, Scope, Target
from ..rpc import EmptyParams, RequestContext, Router

router = Router()


# ---------------------------------------------------------------- 領域


class ZoneParams(BaseModel):
    id: str | None = Field(default=None, description="領域の ID。省略すると zone_1, zone_2, ... を付ける")
    label: str = Field(default="", description="呼び名。例: リビングの遊び場")
    polygon: list[Vec3] | None = Field(default=None, min_length=3, description="床の多角形（Unity ワールド座標。高さは使わない）")
    box: RegionBox | None = Field(default=None, description="直方体で囲んだとき（底面を床の範囲として使う）")

    @model_validator(mode="after")
    def _has_shape(self) -> ZoneParams:
        if self.polygon is None and self.box is None:
            raise ValueError("Either polygon or box is required")
        return self


def _zone(p: ZoneParams, zone_id: str) -> SceneRegion:
    return SceneRegion(id=zone_id, label=p.label or zone_id, polygon=p.polygon, box=p.box)


def _pending(ctx: RequestContext) -> list[dict[str, Any]]:
    return [p.model_dump(mode="json", by_alias=True) for p in ctx.services.state.pending_rules]


@router.method(
    "zones.define",
    params=ZoneParams,
    description="住人が決めた領域（進入禁止の範囲など）を登録する。Quest で床を囲んだ範囲を送る。scene.update のあとも残る。"
    "同じ ID があれば置き換える。登録の途中のルール（pending_rules）があれば一緒に返すので、rules.confirm で確定する",
)
async def define_zone(ctx: RequestContext, p: ZoneParams) -> dict[str, Any]:
    state = ctx.services.state
    zone_id = p.id
    if zone_id is None:
        n = 1
        while f"zone_{n}" in state.zone_polygons():
            n += 1
        zone_id = f"zone_{n}"
    if any(o.id == zone_id for o in state.scene.objects):
        raise RpcError(ErrorCode.INVALID_PARAMS, f"{zone_id!r} collides with an object ID")
    version = state.define_zone(_zone(p, zone_id))
    ctx.services.events.add("zone", ctx.session.actor, action="define", zone_id=zone_id)
    await ctx.services.publish_state()
    return {"version": version, "zone": state.zones[zone_id].model_dump(mode="json"), "pending_rules": _pending(ctx)}


class ZoneUpdateParams(ZoneParams):
    id: str = Field(min_length=1, description="訂正する領域の ID")  # type: ignore[assignment]


@router.method(
    "zones.update",
    params=ZoneUpdateParams,
    description="領域の範囲を訂正する。その領域を読むルールの判定をやり直し、訂正の前後で変わった行と項目（changes）を返す",
)
async def update_zone(ctx: RequestContext, p: ZoneUpdateParams) -> dict[str, Any]:
    state = ctx.services.state
    try:
        correction = state.update_zone(_zone(p, p.id))
    except ValueError as e:
        raise RpcError(ErrorCode.INVALID_PARAMS, str(e)) from e
    ctx.services.events.add("correction", ctx.session.actor, action="zones.update", zone_id=p.id, changes=len(correction.changes))
    await ctx.services.publish_state()
    return {"version": state.version, "correction": correction.model_dump(mode="json")}


class ZoneIdParams(BaseModel):
    id: str = Field(min_length=1)


@router.method("zones.remove", params=ZoneIdParams, description="住人が決めた領域を消す")
async def remove_zone(ctx: RequestContext, p: ZoneIdParams) -> dict[str, Any]:
    state = ctx.services.state
    if p.id not in state.zones:
        raise RpcError(ErrorCode.INVALID_PARAMS, f"No zone {p.id!r}", {"zones": sorted(state.zones)})
    version = state.remove_zone(p.id)
    await ctx.services.publish_state()
    return {"version": version}


# ---------------------------------------------------------------- 人


class PeopleParams(BaseModel):
    people: list[Person] = Field(default_factory=list, description="いま見えている人すべて（空のリストは「誰もいない」）")
    valid_for: float | None = Field(
        default=None, ge=0.0,
        description="この観測を有効とみなす秒数（0 でずっと有効）。省略すると COGROUND_PEOPLE_TIMEOUT（既定 2 秒）。"
        "過ぎると「人の位置が観測できていない」扱いになり、子供の近くで止まるルールがあれば台車を止める")


@router.method(
    "people.update",
    params=PeopleParams,
    description="人の位置を置き換える（Unity / 検出が、見えている間は 1 秒に数回送る）。子供が近くにいる間は台車を止める、"
    "などの家庭ルールに使う",
)
async def update_people(ctx: RequestContext, p: PeopleParams) -> dict[str, Any]:
    ids = [x.id for x in p.people]
    if len(set(ids)) != len(ids):
        raise RpcError(ErrorCode.INVALID_PARAMS, "Duplicate person IDs")
    state = ctx.services.state
    changed = state.set_people(p.people, p.valid_for)
    await ctx.services.executor.monitor.tick()  # すぐ見張りに反映する（次の周期を待たない）
    if changed:  # 動いていなければ、全体状態は配らない（1 秒に何度も届く）
        await ctx.services.broadcast_state()
    return {"version": state.version, "people": len(p.people), "held": ctx.services.robot.held}


# ---------------------------------------------------------------- ルールの訂正


class RuleUpdateParams(BaseModel):
    """渡した項目だけを変える（null を渡すと、その項目を消す）。"""

    model_config = ConfigDict(populate_by_name=True)

    rule_id: str = Field(min_length=1)
    from_: str | None = Field(default=None, alias="from", description="効き始める時刻（HH:MM）")
    until: str | None = Field(default=None, description="効かなくなる時刻（HH:MM）")
    requester: str | None = Field(default=None, description="この人物が依頼したときだけ効く")


@router.method(
    "rules.update",
    params=RuleUpdateParams,
    description="家庭ルールの Scope を訂正する（例: 19 時からにして）。渡した項目だけを変える。"
    "判定をやり直し、訂正の前後で変わった行と項目（changes）を返す",
)
async def update_rule(ctx: RequestContext, p: RuleUpdateParams) -> dict[str, Any]:
    state = ctx.services.state
    given = p.model_fields_set - {"rule_id"}
    if not given:
        raise RpcError(ErrorCode.INVALID_PARAMS, "Nothing to change (from / until / requester)")

    def change(rule: NormRule) -> NormRule:
        scope = rule.scope.model_dump(by_alias=True)
        for name in given:
            scope["from" if name == "from_" else name] = getattr(p, name)
        return rule.model_copy(update={"scope": Scope.model_validate(scope)})

    try:
        correction = state.update_norm(p.rule_id, change)
    except ValueError as e:
        raise RpcError(ErrorCode.INVALID_PARAMS, str(e)) from e
    ctx.services.events.add("correction", ctx.session.actor, action="rules.update", rule_id=p.rule_id,
                            scope=correction.after, changes=len(correction.changes))
    await ctx.services.publish_state()
    return {"version": state.version, "correction": correction.model_dump(mode="json")}


class ExceptionParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    exception_of: str = Field(min_length=1, description="元の禁止の ID")
    original_text: str = Field(default="", description="住人の言葉。例: 私が頼んだときは触ってよい")
    author: str | None = Field(default=None, description="登録者の人物 ID")
    requester: str | None = Field(default=None, description="この人物が依頼したときだけ（省略すると、だれの依頼でも）")
    object_id: str | None = Field(default=None, description="この物体だけ（元の禁止が物体についてのとき）")
    where: RuleCondition | None = Field(default=None, description="この条件に合う物体だけ")
    from_: str | None = Field(default=None, alias="from", description="有効期間の始まり（HH:MM）")
    until: str | None = Field(default=None, description="有効期間の終わり（HH:MM）")
    id: str | None = Field(default=None, description="許可の ID。省略すると P1, P2, ... を付ける")


@router.method(
    "rules.add_exception",
    params=ExceptionParams,
    description="元の禁止に例外（許可）を足す: 依頼者・対象・有効期間を絞って「このときは、してよい」。"
    "判定をやり直し、訂正の前後で変わった行と項目（changes）を返す",
)
async def add_exception(ctx: RequestContext, p: ExceptionParams) -> dict[str, Any]:
    state = ctx.services.state
    base = next((n for n in state.all_norms() if n.id == p.exception_of), None)
    if base is None or base.norm != "prohibition":
        raise RpcError(ErrorCode.INVALID_PARAMS, f"No original prohibition {p.exception_of!r}",
                       {"prohibitions": [n.id for n in state.all_norms() if n.norm == "prohibition"]})
    if base.target.kind == "object":
        target = Target(kind="object", id=p.object_id, where=p.where)
    else:
        target = base.target  # 領域・ロボットについての禁止は、対象をそのまま引き継ぐ
    try:
        rule = NormRule(
            id=p.id or state.new_norm_id("P"), author=p.author, original_text=p.original_text, norm="permission",
            scope=Scope.model_validate({"from": p.from_, "until": p.until, "requester": p.requester}),
            target=target, requirement=base.requirement, exception_of=base.id,
        )
        correction = state.add_exception(rule)
    except ValueError as e:
        raise RpcError(ErrorCode.INVALID_PARAMS, str(e)) from e
    ctx.services.events.add("correction", ctx.session.actor, action="rules.add_exception", rule_id=rule.id,
                            exception_of=base.id, changes=len(correction.changes))
    await ctx.services.publish_state()
    return {"version": state.version, "rule": rule.model_dump(mode="json", by_alias=True),
            "correction": correction.model_dump(mode="json")}


# ---------------------------------------------------------------- ルールの登録（LLM）


class NormCompileParams(BaseModel):
    text: str = Field(min_length=1, description="住人の言葉。例: 夕方6時以降は子供が遊びまわるから、リビングのこのあたりには入るな")
    author: str | None = Field(default=None, description="登録者の人物 ID（「私が頼んだときだけ」の「私」）")
    apply: bool = Field(default=True, description="false なら、作ったルールを返すだけで状態は変えない")


@router.method(
    "norms.compile",
    params=NormCompileParams,
    streams=True,
    description="住人の言葉を LLM で家庭ルールにする（数秒かかる。cancel で止まる）。確定したルール（norms）は、apply ならすぐ効く。"
    "範囲が言葉だけでは決まらない（pending_refs）・解除時刻が言われていない（unresolved: scope.until）ルールは、"
    "勝手に補わず pending に入れて返す（zones.define で範囲を決め、rules.confirm で確定する）",
)
async def compile_norm(ctx: RequestContext, p: NormCompileParams) -> dict[str, Any]:
    state = ctx.services.state
    await ctx.stream({"stage": "llm"})
    zone_ids = {r.id: r.label for r in state.scene.regions}
    zone_ids.update({z.id: z.label for z in state.zones.values()})
    try:
        rules, pending, unresolved = await compile_norms(
            ctx.services.llm, p.text, state.scene, zone_ids=zone_ids, existing=state.all_norms(), author=p.author,
            new_id=lambda taken: state.new_norm_id("N", taken))
    except LlmError as e:
        raise RpcError(ErrorCode.LLM_FAILED, str(e)) from e
    result: dict[str, Any] = {
        "norms": [r.model_dump(mode="json", by_alias=True) for r in rules],
        "pending": [x.model_dump(mode="json", by_alias=True) for x in pending],
        "unresolved": unresolved,
        "applied": False,
    }
    if p.apply and (rules or pending):
        result["version"] = state.add_norms(rules, pending)
        result["applied"] = True
        ctx.services.events.add("norms", ctx.session.actor, action="compile", text=p.text,
                                norms=[r.id for r in rules], pending=[x.rule.id for x in pending])
        await ctx.services.publish_state()
    return result


class ConfirmParams(BaseModel):
    rule_id: str = Field(min_length=1, description="登録の途中のルールの ID")
    refs: dict[str, str] = Field(default_factory=dict, description="仮の参照（zone_ref_1 など）-> 領域の ID")
    until: str | None = Field(default=None, description="解除時刻（HH:MM）。未解決（scope.until）のときに渡す")
    keep_open: bool = Field(default=False, description="解除時刻を決めないままにする（その日のうちは効き続ける）と、住人が決めた")


@router.method(
    "rules.confirm",
    params=ConfirmParams,
    description="登録の途中のルールを確定する（範囲と解除時刻が決まったら）。足りないものがあれば invalid_params（勝手に補わない）",
)
async def confirm_rule(ctx: RequestContext, p: ConfirmParams) -> dict[str, Any]:
    state = ctx.services.state
    try:
        rule = state.confirm_pending(p.rule_id, p.refs, until=p.until, keep_open=p.keep_open)
    except ValueError as e:
        raise RpcError(ErrorCode.INVALID_PARAMS, str(e), {"pending_rules": _pending(ctx)}) from e
    ctx.services.events.add("norms", ctx.session.actor, action="confirm", rule_id=rule.id, refs=p.refs, until=p.until)
    await ctx.services.publish_state()
    return {"version": state.version, "rule": rule.model_dump(mode="json", by_alias=True), "pending_rules": _pending(ctx)}


class PendingIdParams(BaseModel):
    rule_id: str = Field(min_length=1)


@router.method("rules.discard_pending", params=PendingIdParams, description="登録の途中のルールを捨てる")
async def discard_pending(ctx: RequestContext, p: PendingIdParams) -> dict[str, Any]:
    state = ctx.services.state
    if not any(x.rule.id == p.rule_id for x in state.pending_rules):
        raise RpcError(ErrorCode.INVALID_PARAMS, f"No pending rule {p.rule_id!r}")
    version = state.drop_pending(p.rule_id)
    await ctx.services.publish_state()
    return {"version": version, "pending_rules": _pending(ctx)}


@router.method("monitor.get", description="実行中の監視の状態: いまの hold、終わった hold の記録（止めるよう求めた時刻と"
               "実際に止まった時刻・距離）、避けている領域、見張っている条件")
async def get_monitor(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    return ctx.services.executor.monitor.snapshot()
