"""検出サーバー（grounding_server とは別のコンテナ ``detector`` で動かす）。YOLO-World（矩形）と YOLOE-seg（マスク）。

  REST  POST /detect             JPEG を受け取り、矩形を返す（Unity / Quest が直接呼ぶ）
        POST /segment            JPEG を受け取り、物体ごとの矩形・マスク・クラスを返す（grounding_server の perception が呼ぶ。segmentation.py）
        GET  /segment/status     分割モデルの設定
        GET  /detect/status      モデルの設定
        GET|PUT /detect/vocabulary  語彙（prompt → label）
        GET  /detect/live        どのクライアントから届いているか・最後の画像の検出結果（/detect/live.jpg が画像）
        GET  /health             死活確認
  画面  /detect/ui               ブラウザで検出を試す画面

起動: uvicorn coground_server.detect_app:app --host 0.0.0.0 --port 8001 --workers 1
モデルは起動時に 1 回だけ読み込む。COGROUND_DETECT_ENABLED=0 / COGROUND_SEGMENT_ENABLED=0 なら読み込まない（503）。
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from . import __version__
from .detection import Detector, detection_router
from .segmentation import Segmenter, segmentation_router

STATIC_DIR = Path(__file__).with_name("static")


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if os.getenv("COGROUND_DETECT_ENABLED", "1") == "1":
            app.state.detector = await run_in_threadpool(Detector)
        if os.getenv("COGROUND_SEGMENT_ENABLED", "1") == "1":
            app.state.segmenter = await run_in_threadpool(Segmenter)
        try:
            yield
        finally:
            app.state.detector = None
            app.state.segmenter = None

    app = FastAPI(title="CoGround Detector", version=__version__, lifespan=lifespan)
    app.state.detector = None
    app.state.segmenter = None
    app.include_router(detection_router())
    app.include_router(segmentation_router())
    app.mount("/detect/assets", StaticFiles(directory=STATIC_DIR), name="detection-assets")

    @app.get("/detect/ui", include_in_schema=False)
    async def detection_ui():
        return FileResponse(STATIC_DIR / "detect.html")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse(STATIC_DIR / "favicon.ico", media_type="image/vnd.microsoft.icon")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "server_version": __version__, "detector": app.state.detector is not None,
                "segmenter": app.state.segmenter is not None}

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse("/detect/ui")

    return app


logging.basicConfig(
    level=os.environ.get("COGROUND_LOG_LEVEL", "info").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


class _QuietLivePolling(logging.Filter):
    """ブラウザの /detect/live のポーリング（1 秒に何回も来る）をアクセスログから外す。"""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/detect/live" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_QuietLivePolling())
app = create_app()
