"""perception の REST と確認用の画面。

  POST   /perception/analyze            本文 = JPEG（Content-Type: image/jpeg）。検出 →（新しい物体だけ）VLM → 記憶
           ?object_ids=mug_a,cup_b       検出の左からの順に付ける object_id（省略すると obj_001, obj_002, ...）
           ?reanalyze=true               属性があっても VLM に聞き直す（attribute_version が上がる）
  POST   /perception/frame              Quest のフレーム（multipart: rgb = JPEG、depth = 深度、meta = JSON。frame.py）。
                                        物体を 3D にして同じ物体に同じ ID を付け、新しい物体だけ VLM に聞く
           ?record=<名前>                 フレームをそのまま残す（logs/sequences/<名前>/<番号>/。あとで流し直せる）
           ?analyze=false                残すだけで解析しない
  GET    /perception/memory             記憶している物体と、VLM を呼んだ回数
  DELETE /perception/memory             全部忘れる（テストのやり直し用）
  DELETE /perception/memory/{object_id} 1 つ忘れる
  GET    /perception/runs               最近の run（VLM の回数・時間）
  GET    /perception/runs/{run_id}/{file}  run に残したファイル（input.jpg / som.jpg / segmentation_overlay.jpg / *.json）
  画面   /perception/ui
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from .pipeline import Perception, PerceptionError
from .segment_client import SegmentError

STATIC_DIR = Path(__file__).parent.parent / "static"
MAX_BYTES = 10 * 1024 * 1024


def perception_router(perception: Perception) -> APIRouter:
    router = APIRouter()

    @router.post("/perception/analyze")
    async def analyze(request: Request, object_ids: str | None = None, reanalyze: bool = False) -> dict[str, Any]:
        if request.headers.get("content-type", "").split(";")[0].strip().lower() != "image/jpeg":
            raise HTTPException(415, "Content-Type must be image/jpeg")
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > MAX_BYTES:
                raise HTTPException(413, "JPEG exceeds 10 MiB")
        ids = [i.strip() for i in object_ids.split(",")] if object_ids else None
        try:
            result = await perception.analyze(bytes(data), object_ids=ids, reanalyze=reanalyze)
        except (PerceptionError, SegmentError) as e:
            raise HTTPException(e.status, str(e)) from e
        return result.model_dump(mode="json", by_alias=True)

    @router.post("/perception/frame")
    async def frame(rgb: UploadFile = File(...), depth: UploadFile = File(...), meta: str = Form(...),
                    record: str | None = None, analyze: bool = True, reanalyze: bool = False) -> dict[str, Any]:
        rgb_bytes, depth_bytes = await rgb.read(), await depth.read()
        if len(rgb_bytes) > MAX_BYTES or len(depth_bytes) > 4 * MAX_BYTES:
            raise HTTPException(413, "frame is too large")
        out: dict[str, Any] = {}
        try:
            if record:
                out["recorded"] = perception.record_frame(record, rgb_bytes, depth_bytes, meta)
            if analyze:
                result = await perception.analyze_frame(rgb_bytes, depth_bytes, meta, reanalyze=reanalyze)
                out.update(result.model_dump(mode="json", by_alias=True))
        except (PerceptionError, SegmentError) as e:
            raise HTTPException(e.status, str(e)) from e
        return out

    @router.get("/perception/memory")
    async def memory() -> dict[str, Any]:
        return perception.memory.snapshot()

    @router.delete("/perception/memory")
    async def reset_memory() -> dict[str, Any]:
        perception.reset()
        return perception.memory.snapshot()

    @router.delete("/perception/memory/{object_id}")
    async def forget(object_id: str) -> dict[str, Any]:
        if not perception.forget(object_id):
            raise HTTPException(404, f"No object {object_id!r} to forget (unknown, or being analyzed)")
        return perception.memory.snapshot()

    @router.get("/perception/runs")
    async def runs(limit: int = 20) -> dict[str, Any]:
        return {"runs": perception.runs(max(1, min(limit, 200)))}

    @router.get("/perception/runs/{run_id}/{name}")
    async def run_file(run_id: str, name: str) -> FileResponse:
        path = perception.run_file(run_id, name)
        if path is None:
            raise HTTPException(404, "No such run file")
        return FileResponse(path, headers={"Cache-Control": "no-store"})

    @router.get("/perception/ui", include_in_schema=False)
    async def ui() -> FileResponse:
        return FileResponse(STATIC_DIR / "perception.html", headers={"Cache-Control": "no-store"})

    return router
