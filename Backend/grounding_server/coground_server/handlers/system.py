from __future__ import annotations

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


@router.method("state.get", description="現在の全体状態（state.updated と同じ内容）")
async def get_state(ctx: RequestContext, _: EmptyParams) -> dict[str, Any]:
    return ctx.services.state.snapshot()


@router.on_event("client.log")
async def client_log(session: Any, data: dict[str, Any]) -> None:
    """Unity のログをサーバーのログに出す（Quest 実機のデバッグ用）。"""
    level = getattr(logging, str(data.get("level", "info")).upper(), logging.INFO)
    log.log(level, "[%s] %s", session.id, data.get("message", ""))
