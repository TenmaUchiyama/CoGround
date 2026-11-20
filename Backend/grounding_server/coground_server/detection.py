"""POST /detect（Quest が毎フレーム送る）の検出。モードは 2 つで、動いたまま切り替えられる（PUT /detect/mode）。

  open   YOLOE の prompt-free 版（yoloe-11s-seg-pf.pt）。探す物の名前を渡さなくてよい（内蔵の 4585 クラスから自分で名前を付ける）。
         名前はおかしいことがある（物体の名前は後で VLM が決めるので、ここでは目安）。
         机・椅子・「workplace」のような大きな領域も拾うので、画像の COGROUND_DETECT_OPEN_MAX_AREA（既定 0.25）を超える箱は捨てる
  vocab  YOLO-World。語彙（detection_vocab.json、PUT /detect/vocabulary）に書いた物だけを探す

どちらも、重なった箱は名前をまたいで 1 つにまとめる（agnostic NMS。同じマグに cup と mug の箱が重なって出ないように）。
既定のモードは COGROUND_DETECT_MODE（open / vocab、既定 open）。
"""
from __future__ import annotations

import io
import json
import logging
import os
import threading
import time
import uuid
import warnings
from collections import deque
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, TypeAdapter, model_validator
from starlette.concurrency import run_in_threadpool


class VocabularyEntry(BaseModel):
    prompt: str = Field(min_length=1, max_length=200, pattern=r"\S")
    label: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=100)


class Vocabulary(BaseModel):
    entries: list[VocabularyEntry] = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def unique_prompts(self):
        prompts = [entry.prompt.strip().casefold() for entry in self.entries]
        if len(prompts) != len(set(prompts)):
            raise ValueError("prompts must be unique")
        return self


def read_vocabulary(path: Path) -> Vocabulary:
    return Vocabulary(entries=TypeAdapter(list[VocabularyEntry]).validate_json(path.read_text()))


def decode_jpeg(data: bytes):
    """JPEG を RGB の画像にする。JPEG でない・大きすぎるなら 400。"""
    from PIL import Image, UnidentifiedImageError

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format != "JPEG":
                    raise ValueError("expected JPEG")
                if source.width * source.height > 16_000_000:
                    raise ValueError("image exceeds 16 megapixels")
                return source.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(400, "invalid or oversized JPEG") from exc


async def read_body(request: Request) -> bytes:
    """image/jpeg の本文を読む（10 MiB まで）。"""
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "image/jpeg":
        raise HTTPException(415, "Content-Type must be image/jpeg")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(413, "JPEG exceeds 10 MiB")
    return bytes(data)


MODES = ("open", "vocab")


class Mode(BaseModel):
    mode: str = Field(pattern=r"^(open|vocab)$")


def snake(name: str) -> str:
    """内蔵クラスの名前（"laptop keyboard"）→ ラベル（"laptop_keyboard"）。"""
    return "_".join("".join(c if c.isalnum() else " " for c in name.lower()).split()) or "object"


class Detector:
    def __init__(self):
        from ultralytics import YOLOE, YOLOWorld

        self.lock = threading.Lock()
        self.device = os.getenv("COGROUND_DETECT_DEVICE", "0")
        # "0" のような GPU 番号だけの指定は torch の .to() が受け付けないので "cuda:0" にする
        if self.device.isdigit():
            self.device = f"cuda:{self.device}"
        self.conf = float(os.getenv("COGROUND_DETECT_CONF", "0.25"))
        self.imgsz = int(os.getenv("COGROUND_DETECT_IMGSZ", "640"))
        if not 0 <= self.conf <= 1 or self.imgsz <= 0:
            raise ValueError("invalid detection confidence or image size")
        self.debug_dir = os.getenv("COGROUND_DETECT_DEBUG_DIR")
        self.vocabulary = read_vocabulary(Path(os.getenv(
            "COGROUND_DETECT_VOCAB", str(Path(__file__).with_name("detection_vocab.json")))))
        self.model = YOLOWorld(os.getenv("COGROUND_DETECT_MODEL", "yolov8s-worldv2.pt"))
        self.model.to(self.device)
        self.model.set_classes([e.prompt for e in self.vocabulary.entries])
        self.mode = os.getenv("COGROUND_DETECT_MODE", "open")
        if self.mode not in MODES:
            raise ValueError(f"COGROUND_DETECT_MODE must be open or vocab: {self.mode!r}")
        self.open_conf = float(os.getenv("COGROUND_DETECT_OPEN_CONF", "0.25"))
        self.open_max_area = float(os.getenv("COGROUND_DETECT_OPEN_MAX_AREA", "0.25"))
        self.open_model = YOLOE(os.getenv("COGROUND_DETECT_OPEN_MODEL", "yoloe-11s-seg-pf.pt"))
        self.open_model.to(self.device)
        # 初回の推論は CUDA の初期化で遅いので、起動中に 1 回済ませておく
        from PIL import Image
        blank = Image.new("RGB", (self.imgsz, self.imgsz))
        self.model.predict(blank, device=self.device, conf=self.conf, imgsz=self.imgsz, verbose=False)
        self.open_model.predict(blank, device=self.device, conf=self.open_conf, imgsz=self.imgsz, verbose=False)

    def update(self, vocabulary: Vocabulary):
        # Restore embeddings if a failed update partially modifies the model.
        try:
            self.model.set_classes([e.prompt for e in vocabulary.entries])
        except Exception:
            self.model.set_classes([e.prompt for e in self.vocabulary.entries])
            raise
        self.vocabulary = vocabulary
        return vocabulary.model_dump()

    def detect(self, data: bytes) -> dict:
        image = decode_jpeg(data)
        if getattr(self, "mode", "vocab") == "open":
            predictions = self._detect_open(image)
        else:
            result = self.model.predict(image, device=self.device, conf=self.conf, imgsz=self.imgsz,
                                        agnostic_nms=True, verbose=False)[0]
            predictions = [{"label": self.vocabulary.entries[int(cls)].label, "score": score, "box": xyxy}
                           for xyxy, score, cls in _boxes(result)]
        if self.debug_dir:
            save_debug(Path(self.debug_dir), data, image, predictions)
        return {"predictions": predictions}


    def _detect_open(self, image) -> list[dict]:
        result = self.open_model.predict(image, device=self.device, conf=self.open_conf, imgsz=self.imgsz,
                                         agnostic_nms=True, verbose=False)[0]
        limit = self.open_max_area * image.width * image.height
        return [{"label": snake(result.names[int(cls)]), "score": score, "box": xyxy}
                for xyxy, score, cls in _boxes(result)
                if (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1]) <= limit]


def _boxes(result):
    if result.boxes is None:
        return []
    return list(zip(result.boxes.xyxy.cpu().tolist(), result.boxes.conf.cpu().tolist(), result.boxes.cls.cpu().tolist()))


def save_debug(directory, data, image, predictions):
    from PIL import ImageDraw

    directory.mkdir(parents=True, exist_ok=True)
    stem = uuid.uuid4().hex
    (directory / f"{stem}.jpg").write_bytes(data)
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    for p in predictions:
        draw.rectangle(p["box"], outline="red", width=3)
        draw.text(p["box"][:2], f'{p["label"]} {p["score"]:.2f}', fill="red")
    annotated.save(directory / f"{stem}_boxes.jpg")
    (directory / f"{stem}.json").write_text(json.dumps({"predictions": predictions}))


log = logging.getLogger("coground.detect")


class Traffic:
    """/detect に何が届いているかの記録（Quest とつながっているかを確かめるため）。

    - 新しいクライアントから初めて届いたら、すぐログに出す
    - 届いている間は summary_interval 秒ごとに件数・推論時間・検出ラベルをまとめてログに出す
    - 最後に受け取った JPEG と結果を 1 枚だけ持つ（GET /detect/live, /detect/live.jpg）
    """

    def __init__(self, summary_interval: float = 5.0):
        self.lock = threading.Lock()
        self.summary_interval = summary_interval
        self.clients: dict[str, dict] = {}
        self.recent_ok: deque[float] = deque(maxlen=300)
        self.last: dict | None = None
        self.last_jpeg: bytes | None = None
        self.window = self._empty_window()
        self.next_summary = 0.0

    @staticmethod
    def _empty_window():
        return {"ok": 0, "busy": 0, "errors": {}, "infer_ms": 0.0, "labels": {}}

    def record(self, client: str, status: int, data: bytes | None = None,
               result: dict | None = None, infer_ms: float = 0.0):
        now = time.time()
        with self.lock:
            info = self.clients.get(client)
            if info is None:
                info = self.clients[client] = {"host": client, "first_seen": now, "requests": 0,
                                               "ok": 0, "busy": 0, "errors": 0}
                log.info("新しいクライアントから /detect: %s（status=%s）", client, status)
            info["requests"] += 1
            info["last_seen"] = now
            info["last_status"] = status
            w = self.window
            if status == 200:
                info["ok"] += 1
                w["ok"] += 1
                w["infer_ms"] += infer_ms
                self.recent_ok.append(now)
                for p in result["predictions"]:
                    w["labels"][p["label"]] = w["labels"].get(p["label"], 0) + 1
                self.last = {"time": now, "client": client, "bytes": len(data),
                             "size": image_size(data), "infer_ms": round(infer_ms, 1),
                             "predictions": result["predictions"]}
                self.last_jpeg = data
            elif status == 429:
                info["busy"] += 1
                w["busy"] += 1
            else:
                info["errors"] += 1
                w["errors"][status] = w["errors"].get(status, 0) + 1
                log.warning("/detect が %s を返しました（client=%s）", status, client)
            if now >= self.next_summary:
                self._log_summary(now)

    def _log_summary(self, now: float):
        w = self.window
        avg = f"{w['infer_ms'] / w['ok']:.0f}ms" if w["ok"] else "-"
        labels = ", ".join(f"{k}×{v}" for k, v in sorted(w["labels"].items())) or "なし"
        log.info("受信 成功=%d 429=%d エラー=%s 平均推論=%s 検出=%s",
                 w["ok"], w["busy"], w["errors"] or 0, avg, labels)
        self.window = self._empty_window()
        self.next_summary = now + self.summary_interval

    def snapshot(self) -> dict:
        now = time.time()
        with self.lock:
            fps = sum(1 for t in self.recent_ok if now - t <= 5.0) / 5.0
            clients = [{**c, "last_seen_ago": round(now - c["last_seen"], 1),
                        "first_seen_ago": round(now - c["first_seen"], 1)}
                       for c in sorted(self.clients.values(), key=lambda c: -c["last_seen"])]
            last = None
            if self.last:
                last = {**self.last, "age": round(now - self.last["time"], 1)}
            return {"fps": fps, "clients": clients, "last": last}


def image_size(data: bytes):
    from PIL import Image
    try:
        with Image.open(io.BytesIO(data)) as image:
            return list(image.size)
    except Exception:
        return None


def detection_router() -> APIRouter:
    router = APIRouter()
    traffic = Traffic()

    def backend(request):
        detector = request.app.state.detector
        if detector is None:
            raise HTTPException(503, "detection is disabled")
        return detector

    def acquire(detector):
        if not detector.lock.acquire(blocking=False):
            raise HTTPException(429, "detector busy; drop this frame", headers={"Retry-After": "1"})

    @router.get("/detect/status")
    async def status(request: Request):
        detector = request.app.state.detector
        if detector is None:
            return {"enabled": False}
        return {"enabled": True, "device": detector.device,
                "conf": detector.conf, "imgsz": detector.imgsz, "mode": getattr(detector, "mode", "vocab")}

    @router.get("/detect/mode")
    async def get_mode(request: Request):
        return {"mode": getattr(backend(request), "mode", "vocab")}

    @router.put("/detect/mode")
    async def set_mode(request: Request, mode: Mode):
        """open（prompt-free。名前を渡さなくてよい）/ vocab（語彙の物だけ）。再起動すると COGROUND_DETECT_MODE に戻る。"""
        detector = backend(request)
        if mode.mode == "open" and getattr(detector, "open_model", None) is None:
            raise HTTPException(409, "open mode model is not loaded")
        detector.mode = mode.mode
        log.info("/detect のモードを %s にしました", mode.mode)
        return {"mode": detector.mode}

    @router.post("/detect")
    async def detect(request: Request):
        client = request.client.host if request.client else "unknown"
        try:
            detector = backend(request)
            if request.headers.get("content-type", "").split(";")[0].strip().lower() != "image/jpeg":
                raise HTTPException(415, "Content-Type must be image/jpeg")
            acquire(detector)
            try:
                data = bytearray()
                async for chunk in request.stream():
                    data.extend(chunk)
                    if len(data) > 10 * 1024 * 1024:
                        raise HTTPException(413, "JPEG exceeds 10 MiB")
                start = time.perf_counter()
                result = await run_in_threadpool(detector.detect, bytes(data))
            finally:
                detector.lock.release()
        except HTTPException as exc:
            traffic.record(client, exc.status_code)
            raise
        except Exception:
            traffic.record(client, 500)
            raise
        traffic.record(client, 200, bytes(data), result, (time.perf_counter() - start) * 1000)
        return result

    @router.get("/detect/live")
    async def live():
        """どのクライアントから届いているか、最後に受け取った画像の検出結果。"""
        return traffic.snapshot()

    @router.get("/detect/live.jpg")
    async def live_image():
        """最後に受け取った JPEG（そのまま）。まだ何も届いていなければ 404。"""
        data = traffic.last_jpeg
        if data is None:
            raise HTTPException(404, "no frame received yet")
        return Response(data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @router.get("/detect/vocabulary")
    async def get_vocabulary(request: Request):
        return backend(request).vocabulary.model_dump()

    @router.put("/detect/vocabulary")
    async def update_vocabulary(request: Request, vocabulary: Vocabulary):
        detector = backend(request)
        acquire(detector)
        try:
            result = await run_in_threadpool(detector.update, vocabulary)
        finally:
            detector.lock.release()
        # /segment（YOLOE-seg）も同じ語彙で探す
        segmenter = getattr(request.app.state, "segmenter", None)
        if segmenter is not None:
            def update_segmenter():
                with segmenter.lock:
                    segmenter.update(vocabulary)
            await run_in_threadpool(update_segmenter)
        return result

    return router
