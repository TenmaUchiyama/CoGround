"""FastAPI アプリ。

  WebSocket  /ws             Unity との主経路（request / stream / event）
  REST       /health         死活確認
             /api/state      現在の全体状態（デバッグ用。state.get と同じ）
             /api/protocol   method の一覧とスキーマ
             /api/fixtures   テスト用のシーンとシナリオ（tests/fixtures の JSON。テスト画面が使う）
  画面       /ui             ブラウザで開くテスト画面（static/ui.html。Unity の代わりに WebSocket でつなぐ）
             /rules          ルールバンク（static/rules.html。家庭ルール・片付けルール・登録の途中のルールを管理する）
             /perception/ui  画像 → 検出 → VLM の属性 → 物体の記憶 を試す画面（REST は /perception/...。perception/api.py）

物体検出（YOLO-World, /detect）は別のコンテナで動く: detect_app.py
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, RedirectResponse

from . import __version__, protocol
from .handlers import build_router
from .perception.api import perception_router
from .services import Services
from .session import Session

STATIC_DIR = Path(__file__).parent / "static"
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def create_app() -> FastAPI:
    router = build_router()
    services = Services()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await services.robot.start()
        services.executor.monitor.start()  # 台車が動いている間の家庭ルールの監視（実行していないときの移動も見張る）
        try:
            yield
        finally:
            await services.executor.close()
            await services.robot.close()

    app = FastAPI(title="CoGround Grounding Server", version=__version__, lifespan=lifespan)

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse(STATIC_DIR / "favicon.ico", media_type="image/vnd.microsoft.icon")

    app.state.services = services
    app.state.router = router
    app.include_router(perception_router(services.perception))

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
        return services.snapshot()

    @app.get("/api/protocol")
    async def get_protocol() -> dict[str, Any]:
        return {
            "protocol_version": protocol.PROTOCOL_VERSION,
            "methods": router.describe(),
            "client_events": sorted(router.events),
            "server_events": ["session.welcome", "session.error", "state.updated"],
        }

    @app.get("/api/fixtures")
    async def get_fixtures() -> dict[str, Any]:
        # ファイル名（拡張子なし）-> 中身。フォルダが無ければ空
        return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(FIXTURES_DIR.glob("*.json"))}

    @app.get("/ui", include_in_schema=False)
    async def ui() -> FileResponse:
        # 開発中に書き換えてもすぐ反映されるよう、キャッシュさせない
        return FileResponse(STATIC_DIR / "ui.html", headers={"Cache-Control": "no-store"})

    @app.get("/rules", include_in_schema=False)
    async def rules_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "rules.html", headers={"Cache-Control": "no-store"})

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse("/ui")

    return app


# COGROUND_LOG_LEVEL=debug にすると、届いた event の中身も出る
logging.basicConfig(
    level=os.environ.get("COGROUND_LOG_LEVEL", "info").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
app = create_app()
