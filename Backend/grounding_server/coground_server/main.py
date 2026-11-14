"""FastAPI アプリ。

  WebSocket  /ws             Unity との主経路（request / stream / event）
  REST       /health         死活確認
             /api/state      現在の全体状態（デバッグ用。state.get と同じ）
             /api/protocol   method の一覧とスキーマ
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, WebSocket

from . import __version__, protocol
from .handlers import build_router
from .services import Services
from .session import Session


def create_app() -> FastAPI:
    router = build_router()
    services = Services()

    app = FastAPI(title="CoGround Grounding Server", version=__version__)
    app.state.services = services
    app.state.router = router

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket) -> None:
        await Session(ws, router, services).run()

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "server_version": __version__,
            "protocol_version": protocol.PROTOCOL_VERSION,
            "clients": services.hub.count,
            "state_version": services.state.version,
        }

    @app.get("/api/state")
    async def get_state() -> dict[str, Any]:
        return services.state.snapshot()

    @app.get("/api/protocol")
    async def get_protocol() -> dict[str, Any]:
        return {
            "protocol_version": protocol.PROTOCOL_VERSION,
            "methods": router.describe(),
            "client_events": sorted(router.events),
            "server_events": ["session.welcome", "session.error", "state.updated"],
        }

    return app


# COGROUND_LOG_LEVEL=debug にすると、届いた event の中身も出る
logging.basicConfig(
    level=os.environ.get("COGROUND_LOG_LEVEL", "info").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
app = create_app()
