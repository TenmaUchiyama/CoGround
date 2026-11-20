"""YOLOE-seg によるインスタンス分割（detector コンテナの POST /segment）。

/detect（YOLO-World、矩形だけ、Quest が毎フレーム送る）とは別のモデル。こちらは 1 枚の画像から
物体ごとの矩形・マスク・クラス・確信度を返し、grounding_server の perception（SoM → VLM → 記憶）が使う。

返す形（perception/schema.py の Segmentation と同じ）:
  {"image": {"width": 1280, "height": 960}, "model": "yoloe-11s-seg.pt", "infer_ms": 12.3,
   "detections": [{"detection_id": 1, "class": "cup", "bbox": [x1, y1, x2, y2], "confidence": 0.94,
                   "mask": [[x, y], ...]}]}

?embed=1 を付けると、物体ごとに見た目の特徴量 "embedding"（DINOv2 ViT-S/14 の CLS、384 次元、長さ 1）も返す。
同じ物体を見つけ直すとき（perception/association.py）に使う。

detection_id はその画像の中だけの仮の番号（左から右へ 1, 2, 3...）。物体をまたいで続く ID（object_id）は
grounding_server の記憶が持つ。

語彙（何を探すか）は /detect と同じもの（detection_vocab.json、PUT /detect/vocabulary で両方に効く）。

環境変数:
  COGROUND_SEGMENT_ENABLED  1（既定）で読み込む。0 なら /segment は 503
  COGROUND_SEGMENT_MODEL    重み（既定 yoloe-11s-seg.pt。イメージには /models に入れてある）
  COGROUND_SEGMENT_CONF     確信度のしきい値（既定 0.25）
  COGROUND_EMBED_MODEL      特徴量のモデル（torch.hub の DINOv2 のフォルダ。イメージには /models/torch/hub に入れてある）。
                            空なら特徴量を出さない（embedding は null）
  COGROUND_DETECT_DEVICE / COGROUND_DETECT_IMGSZ / COGROUND_DETECT_VOCAB は /detect と共通
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from .detection import Vocabulary, decode_jpeg, read_body, read_vocabulary


class Segmenter:
    def __init__(self):
        from ultralytics import YOLOE

        self.lock = threading.Lock()
        self.device = os.getenv("COGROUND_DETECT_DEVICE", "0")
        if self.device.isdigit():
            self.device = f"cuda:{self.device}"
        self.conf = float(os.getenv("COGROUND_SEGMENT_CONF", "0.25"))
        self.imgsz = int(os.getenv("COGROUND_DETECT_IMGSZ", "640"))
        if not 0 <= self.conf <= 1 or self.imgsz <= 0:
            raise ValueError("invalid segmentation confidence or image size")
        self.vocabulary = read_vocabulary(Path(os.getenv(
            "COGROUND_DETECT_VOCAB", str(Path(__file__).with_name("detection_vocab.json")))))
        self.model_name = os.getenv("COGROUND_SEGMENT_MODEL", "yoloe-11s-seg.pt")
        self.model = YOLOE(self.model_name)
        self._set_classes(self.vocabulary)
        self.model.to(self.device)
        from PIL import Image
        self._predict(Image.new("RGB", (self.imgsz, self.imgsz)))  # 初回は CUDA の初期化で遅いので、起動中に済ませる
        self.embedder = Embedder.from_env(self.device)

    def _set_classes(self, vocabulary: Vocabulary):
        prompts = [e.prompt for e in vocabulary.entries]
        self.model.set_classes(prompts, self.model.get_text_pe(prompts))

    def _predict(self, image):
        # agnostic_nms: 「cup」と「mug」のように近い語彙で、同じ物体が 2 回出るのを防ぐ
        return self.model.predict(image, device=self.device, conf=self.conf, imgsz=self.imgsz,
                                  agnostic_nms=True, verbose=False)[0]

    def update(self, vocabulary: Vocabulary):
        try:
            self._set_classes(vocabulary)
        except Exception:
            self._set_classes(self.vocabulary)
            raise
        self.vocabulary = vocabulary

    def segment(self, data: bytes, embed: bool = False) -> dict:
        image = decode_jpeg(data)
        start = time.perf_counter()
        result = self._predict(image)
        infer_ms = (time.perf_counter() - start) * 1000
        found = []
        if result.boxes is not None:
            polygons = result.masks.xy if result.masks is not None else []
            for i, (xyxy, score, cls) in enumerate(zip(result.boxes.xyxy.cpu().tolist(),
                                                       result.boxes.conf.cpu().tolist(),
                                                       result.boxes.cls.cpu().tolist())):
                polygon = polygons[i].tolist() if i < len(polygons) else []
                found.append({"class": self.vocabulary.entries[int(cls)].label,
                              "bbox": [round(v, 1) for v in xyxy], "confidence": round(score, 4),
                              "mask": [[round(x, 1), round(y, 1)] for x, y in polygon]})
        # 左から右（同じなら上から下）に番号を振る。同じ並びの写真なら、撮り直しても同じ番号になる
        found.sort(key=lambda d: ((d["bbox"][0] + d["bbox"][2]) / 2, (d["bbox"][1] + d["bbox"][3]) / 2))
        detections = [{"detection_id": n, **d} for n, d in enumerate(found, start=1)]
        if embed:
            embedder = getattr(self, "embedder", None)
            embeddings = embedder.embed(image, [d["bbox"] for d in detections]) if embedder else None
            for i, d in enumerate(detections):
                d["embedding"] = embeddings[i] if embeddings is not None else None
        return {"image": {"width": image.width, "height": image.height}, "model": Path(self.model_name).name,
                "infer_ms": round(infer_ms, 1), "detections": detections}


class Embedder:
    """切り出した物体の画像 → 見た目の特徴量（DINOv2 の CLS トークン、長さ 1 にそろえる）。"""

    PAD = 0.1  # 矩形をこの割合だけ広げて切り出す
    SIZE = 224

    def __init__(self, model, device: str):
        import torch
        import torchvision.transforms as T

        self.torch = torch
        self.model = model.to(device).eval()
        self.device = device
        self.transform = T.Compose([T.Resize((self.SIZE, self.SIZE), interpolation=T.InterpolationMode.BICUBIC),
                                    T.ToTensor(), T.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))])

    @classmethod
    def from_env(cls, device: str) -> Embedder | None:
        path = os.getenv("COGROUND_EMBED_MODEL", "")
        if not path:
            return None
        import torch

        # source="local": イメージに入れたコードと重みだけを使う（起動時にネットワークを使わない）
        return cls(torch.hub.load(path, "dinov2_vits14", source="local"), device)

    def embed(self, image, boxes: list[list[float]]) -> list[list[float]]:
        if not boxes:
            return []
        crops = []
        for x1, y1, x2, y2 in boxes:
            pw, ph = (x2 - x1) * self.PAD, (y2 - y1) * self.PAD
            crop = image.crop((max(0, x1 - pw), max(0, y1 - ph), min(image.width, x2 + pw), min(image.height, y2 + ph)))
            crops.append(self.transform(crop))
        with self.torch.no_grad():
            features = self.model(self.torch.stack(crops).to(self.device))
            features = self.torch.nn.functional.normalize(features, dim=1)
        return [[round(v, 5) for v in row] for row in features.cpu().tolist()]


def segmentation_router() -> APIRouter:
    router = APIRouter()

    def backend(request: Request) -> Segmenter:
        segmenter = getattr(request.app.state, "segmenter", None)
        if segmenter is None:
            raise HTTPException(503, "segmentation is disabled")
        return segmenter

    def locked_segment(segmenter: Segmenter, data: bytes, embed: bool) -> dict:
        # /detect と違って毎フレームは来ないので、混んでいたら捨てずに順番を待つ
        with segmenter.lock:
            return segmenter.segment(data, embed=embed)

    @router.get("/segment/status")
    async def status(request: Request):
        segmenter = getattr(request.app.state, "segmenter", None)
        if segmenter is None:
            return {"enabled": False}
        return {"enabled": True, "model": Path(segmenter.model_name).name, "device": segmenter.device,
                "conf": segmenter.conf, "imgsz": segmenter.imgsz,
                "classes": [e.label for e in segmenter.vocabulary.entries],
                "embedding": getattr(segmenter, "embedder", None) is not None}

    @router.post("/segment")
    async def segment(request: Request, embed: bool = False):
        segmenter = backend(request)
        data = await read_body(request)
        return await run_in_threadpool(locked_segment, segmenter, data, embed)

    return router
