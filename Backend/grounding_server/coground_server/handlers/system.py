from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from ..rpc import EmptyParams, RequestContext, Router

router = Router()
log = logging.getLogger("coground_server.client")


@router.method("system.ping", description="疎通確認。サーバー時刻を返す")
async def ping(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    return {"pong": True, "server_time": datetime.now(timezone.utc).isoformat()}


@router.method("system.describe", description="使える method とその params スキーマの一覧")
async def describe(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    return {"methods": ctx.session.router.describe()}


@router.method("system.reset",
               description="まっさらにする: 実行・動作計画・単体テストの計画を止めて消し、ロボットの持っている物を忘れ、"
               "腕を初期姿勢へ戻す（ROS の latch した古い計画・経路も消える）。ルールとシーンの物体は残す")
async def reset(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    services = ctx.services
    actor = ctx.session.actor
    services.events.add("system", actor, action="reset")
    # 実行を止める指示を先に出し（スキルは robot.reset が終わらせる）、ロボットをリセットしてから、止まるのを待つ
    stopping = asyncio.create_task(services.executor.clear_all(actor))
    try:
        ok, detail = await services.robot.reset()
    finally:
        await stopping
    services.motion.clear()
    services.test_plan = None
    services.events.add("system", "system", action="reset_done", ok=ok, detail=detail)
    await services.publish_touched()
    return {"ok": ok, "detail": detail, "robot": services.robot.snapshot()}


@router.method("state.get", description="現在の全体状態（state.updated と同じ内容）")
async def get_state(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    return ctx.services.snapshot()


@router.on_event("client.log")
async def client_log(session: Any, data: dict[str, Any]) -> None:
    """Unity のログをサーバーのログに出す（Quest 実機のデバッグ用）。"""
    level = getattr(logging, str(data.get("level", "info")).upper(), logging.INFO)
    log.log(level, "[%s] %s", session.id, data.get("message", ""))
