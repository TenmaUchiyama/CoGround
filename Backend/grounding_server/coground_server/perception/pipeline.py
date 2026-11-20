"""画像 → 検出 → 物体の ID →（新しい物体だけ）VLM → 記憶、をつなぐ。入口は 2 つ。

  analyze(jpeg)                         画像 1 枚だけ。object_id は固定（呼ぶ側が渡すか、左からの順に obj_001, ...）
  analyze_frame(rgb, depth, meta)       Quest のフレーム（RGB + 深度 + 撮影時のカメラ）。物体を 3D にして、
                                        association.py の ObjectTracker が同じ物体に同じ ID を付ける（視点を変えても、動かしても）

どちらも、ID が決まった後は同じ: 記憶に属性があれば返し、無ければ（新しい物体）まとめて VLM に 1 回だけ聞く。

COGROUND_PERCEPTION_RUNS=/app/logs/perception があれば、run ごとにフォルダを作って残す:
  input.jpg / detections.json / segmentation_overlay.jpg / som.jpg / attributes.json（VLM を呼んだときだけ）/ result.json
  フレームのときは、さらに meta.json / depth_overlay.jpg（RGB に、位置を合わせた深度を色で重ねたもの。位置合わせの確認用）
と、1 行 1 run の runs.jsonl（VLM を呼んだ回数とかかった時間）。

COGROUND_PERCEPTION_SEQUENCES=/app/logs/sequences があれば、record=<名前> で受けたフレームを
<名前>/<番号>/{rgb.jpg, depth.bin, meta.json} にそのまま残す（scripts/perception_replay.py で流し直せる）。

COGROUND_OBJECT_TRACKS=/app/data/object_tracks.json があれば、3D で追っている物体（箱・特徴量）も残す（再起動しても同じ ID）。
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
from PIL import Image
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from ..llm import LlmClient
from . import frame as framelib
from . import som
from .association import AssociationConfig, Observation, ObjectTracker, lift_polygon
from .object_store import ObjectMemory
from .schema import AnalyzedObject, AnalyzeResult, AttributeQuestion, Detection, FrameSummary, Segmentation, VlmUsage
from .segment_client import HttpSegmenter, Segmenter
from .vlm_analyzer import MAX_IMAGE_SIDE, VlmAnalyzer

log = logging.getLogger(__name__)

# これより小さい画像は、描く前に拡大する（長い辺）
MIN_DRAW_SIDE = 1280

RUN_FILES = ("input.jpg", "detections.json", "segmentation_overlay.jpg", "som.jpg", "attributes.json", "result.json",
             "meta.json", "depth_overlay.jpg")
SEQUENCE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class PerceptionError(Exception):
    """依頼が受けられない（object_ids の数が合わない、フレームの形が違う、など）。status は HTTP で返すときの番号。"""

    def __init__(self, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.status = status


def default_object_id(detection_id: int) -> str:
    return f"obj_{detection_id:03d}"


class Perception:
    def __init__(self, get_llm: Callable[[], LlmClient], *, segmenter: Segmenter | None = None, memory: ObjectMemory | None = None,
                 runs_dir: str | Path | None = None, sequences_dir: str | Path | None = None,
                 tracks_path: str | Path | None = None, config: AssociationConfig | None = None,
                 get_questions: Callable[[], Sequence[AttributeQuestion]] | None = None) -> None:
        self.segmenter: Segmenter = segmenter or HttpSegmenter()
        self.analyzer = VlmAnalyzer(get_llm)
        # いまあるルールが使っている属性（VLM に聞く）。呼ぶたびに取り直す（ルールが変われば、質問も変わる）
        self.get_questions = get_questions
        self.memory = memory if memory is not None else ObjectMemory()
        self.runs_dir = Path(runs_dir) if runs_dir else None
        self.sequences_dir = Path(sequences_dir) if sequences_dir else None
        self.tracks_path = Path(tracks_path) if tracks_path else None
        # 記憶にすでにある ID（画像 1 枚の analyze で付けた obj_001 など）は、新しい物体に付けない
        self.tracker = ObjectTracker(config or AssociationConfig(), reserved=lambda object_id: object_id in self.memory.objects)
        self._load_tracks()

    @classmethod
    def from_env(cls, get_llm: Callable[[], LlmClient],
                 get_questions: Callable[[], Sequence[AttributeQuestion]] | None = None) -> Perception:
        env = os.environ.get
        return cls(get_llm, get_questions=get_questions,
                   memory=ObjectMemory.from_env(), runs_dir=env("COGROUND_PERCEPTION_RUNS") or None,
                   sequences_dir=env("COGROUND_PERCEPTION_SEQUENCES") or None,
                   tracks_path=env("COGROUND_OBJECT_TRACKS") or None, config=AssociationConfig.from_env())

    # ---------------------------------------------------------------- 入口 1: 画像 1 枚

    async def analyze(self, jpeg: bytes, *, object_ids: Sequence[str] | None = None, reanalyze: bool = False) -> AnalyzeResult:
        started = time.perf_counter()
        run_id = _run_id()
        timings: dict[str, float] = {}
        t = time.perf_counter()
        segmentation = await self.segmenter.segment(jpeg)
        timings["segment"] = _ms(t)
        ids = self._object_ids(segmentation.detections, object_ids)
        return await self._attribute(run_id, started, timings, jpeg, segmentation, ids, reanalyze)

    # ---------------------------------------------------------------- 入口 2: Quest のフレーム

    async def analyze_frame(self, rgb: bytes, depth: bytes, meta: str | bytes, *, reanalyze: bool = False) -> AnalyzeResult:
        started = time.perf_counter()
        run_id = _run_id()
        timings: dict[str, float] = {}
        try:
            frame = framelib.decode_frame(depth, meta)
        except (ValueError, ValidationError) as e:
            raise PerceptionError(f"Invalid frame: {e}") from e
        size = _jpeg_size(rgb)
        if size != (frame.meta.rgb.width, frame.meta.rgb.height):
            raise PerceptionError(f"rgb is {size[0]}x{size[1]} but meta.rgb says "
                                  f"{frame.meta.rgb.width}x{frame.meta.rgb.height} (intrinsics must match the sent image)")

        t = time.perf_counter()
        segmentation = await self.segmenter.segment(rgb, embed=True)
        timings["segment"] = _ms(t)

        # 深度を RGB に合わせ、検出ごとに 3D の箱を作る
        t = time.perf_counter()
        aligned, camera = await run_in_threadpool(framelib.align_depth, frame.points, frame.camera, size)
        observations = []
        for d in segmentation.detections:
            box = lift_polygon(d.mask or _bbox_polygon(d.bbox), size, aligned, camera, self.tracker.config)
            if box is not None:
                embedding = np.asarray(d.embedding, dtype=float) if d.embedding else None
                observations.append(Observation(d.detection_id, d.cls, box, embedding))
        timings["lift"] = _ms(t)

        # 同じ物体を見つけ直す。update と、続く記憶の claim の間に await をはさまない（ほかの依頼と混ざらないように）
        track = self.tracker.update(observations, frame.meta.timestamp, depth=aligned, camera=camera)
        for dropped in track.merged:
            self.memory.forget(dropped)
        ids = {e.detection_id: e.object_id for e in track.events}
        kinds = {e.detection_id: e.kind for e in track.events}
        summary = FrameSummary(timestamp=frame.meta.timestamp, depth_points=len(frame.points),
                               depth_coverage=round(float((aligned > 0).mean()), 3), located=len(observations),
                               displaced=track.displaced, missing=track.missing, merged=track.merged)
        result = await self._attribute(run_id, started, timings, rgb, segmentation, ids, reanalyze, kinds=kinds,
                                       summary=summary, depth=(aligned, frame.meta))
        self._save_tracks()
        return result

    def record_frame(self, name: str, rgb: bytes, depth: bytes, meta: str | bytes) -> str:
        """フレームをそのまま残す（<sequences>/<name>/<番号>/）。残した場所（sequences からの相対）を返す。"""
        if self.sequences_dir is None:
            raise PerceptionError("Recording is off (set COGROUND_PERCEPTION_SEQUENCES)", 409)
        if not SEQUENCE_NAME.match(name):
            raise PerceptionError("record name must be 1-64 letters, digits, _ or -")
        directory = self.sequences_dir / name
        directory.mkdir(parents=True, exist_ok=True)
        number = 1 + max((int(p.name) for p in directory.iterdir() if p.name.isdigit()), default=0)
        target = directory / f"{number:04d}"
        target.mkdir()
        (target / "rgb.jpg").write_bytes(rgb)
        (target / "depth.bin").write_bytes(depth)
        (target / "meta.json").write_bytes(meta if isinstance(meta, bytes) else meta.encode("utf-8"))
        return f"{name}/{number:04d}"

    # ---------------------------------------------------------------- 記憶を消す

    def reset(self) -> None:
        self.memory.reset()
        self.tracker.reset()
        self._save_tracks()

    def forget(self, object_id: str) -> bool:
        if not self.memory.forget(object_id):
            return False
        self.tracker.forget(object_id)
        self._save_tracks()
        return True

    # ---------------------------------------------------------------- 共通: ID が決まった後

    async def _attribute(self, run_id: str, started: float, timings: dict[str, float], jpeg: bytes,
                         segmentation: Segmentation, ids: dict[int, str], reanalyze: bool, *,
                         kinds: dict[int, str] | None = None, summary: FrameSummary | None = None,
                         depth: tuple[np.ndarray, framelib.FrameMeta] | None = None) -> AnalyzeResult:
        detections = segmentation.detections

        # 1. 画像を描く（VLM を呼ばないときも、確認用に残す）
        t = time.perf_counter()
        original_jpeg, som_jpeg, overlay_jpeg = await run_in_threadpool(_render, jpeg, detections)
        timings["som"] = _ms(t)

        # 2. 記憶に聞く。新しい物体だけ、まとめて VLM に 1 回聞く
        questions = list(self.get_questions()) if self.get_questions is not None else []
        claim = self.memory.claim(ids.values(), reanalyze=reanalyze, required=[q.name for q in questions])
        usage = VlmUsage(calls=0, analyzed=list(claim.new), reused=list(claim.cached))
        by_object = {object_id: d for d in detections if (object_id := ids.get(d.detection_id))}
        answer_json: dict[str, Any] | None = None
        if claim.new:
            targets = [by_object[i] for i in claim.new]
            self.memory.count_vlm_call(claim.new)
            usage.calls = 1
            t = time.perf_counter()
            try:
                answer = await self.analyzer.analyze(original_jpeg, som_jpeg, targets, questions)
            except Exception as e:  # noqa: BLE001 失敗しても、待っている依頼を動かし、次の依頼でやり直せるようにする
                log.warning("perception %s: VLM failed: %s", run_id, e)
                usage.error = str(e)
                for object_id in claim.new:
                    self.memory.fail(object_id, str(e))
            else:
                answer_json = answer.model_dump(mode="json")
                answered = {a.mark_id: a for a in answer.objects}
                for object_id in claim.new:
                    a = answered.get(by_object[object_id].detection_id)
                    if a is None:
                        self.memory.fail(object_id, "The VLM gave no answer for this mark")
                    else:
                        # ルールが使う属性は、答えが無くても unknown として残す（「聞いたが分からなかった」を区別する）
                        asked = {q.name: "unknown" for q in questions}
                        asked.update({x.name: x.value for x in a.answers})
                        self.memory.complete(object_id, a.category, {
                            "material": a.material, "fragility": a.fragility, "appearance": a.appearance, **asked},
                            evidence={x.name: x.evidence for x in a.answers if x.evidence})
            usage.seconds = round(time.perf_counter() - t, 2)
            timings["vlm"] = _ms(t)
        if claim.waiting:
            t = time.perf_counter()
            await self.memory.wait(claim.waiting)
            timings["wait"] = _ms(t)

        # 3. 3D で追っている物体の場所と状態を、記憶にも写す
        if kinds is not None:
            self._sync_presence()

        # 4. 答えを組み立てる
        objects = []
        for d in detections:
            object_id = ids.get(d.detection_id)
            if object_id is None:
                objects.append(AnalyzedObject(detection_id=d.detection_id, object_id=None, cls=d.cls, bbox=d.bbox,
                                              confidence=d.confidence, source="unlocated"))
                continue
            self.memory.observe(object_id, detected_class=d.cls, bbox=d.bbox, run_id=run_id)
            record = self.memory.objects[object_id]
            source = "vlm" if object_id in claim.new else "waited" if object_id in claim.waiting else "memory"
            objects.append(AnalyzedObject(
                detection_id=d.detection_id, object_id=object_id, cls=d.cls, bbox=d.bbox, confidence=d.confidence,
                category=record.category, attributes=dict(record.attributes), evidence=dict(record.evidence),
                vlm_status=record.vlm_status,
                attribute_version=record.attribute_version, source=source, error=record.error,
                track=(kinds or {}).get(d.detection_id), position=record.position, size=record.size))
        self.memory.save()
        timings["total"] = _ms(started)
        result = AnalyzeResult(run_id=run_id, image=segmentation.image, objects=objects, vlm=usage, timings_ms=timings,
                               memory_stats=self.memory.stats(), frame=summary)
        log.info("perception %s: %d object(s), vlm_calls=%d analyzed=%s reused=%s%s total=%.0fms",
                 run_id, len(objects), usage.calls, usage.analyzed, usage.reused,
                 f" displaced={summary.displaced} missing={summary.missing}" if summary else "", timings["total"])
        if self.runs_dir is not None:
            await run_in_threadpool(self._save_run, result, segmentation, jpeg, som_jpeg, overlay_jpeg, answer_json, depth)
        return result

    def _sync_presence(self) -> None:
        for obj in self.tracker.objects.values():
            record = self.memory.get(obj.object_id)
            if record is not None:
                record.presence = obj.state
                record.position = [round(float(v), 4) for v in obj.box.center]
                record.size = [round(float(v), 4) for v in obj.box.max - obj.box.min]

    def _object_ids(self, detections: Sequence[Detection], object_ids: Sequence[str] | None) -> dict[int, str]:
        """detection_id -> object_id（画像 1 枚のとき）。"""
        if object_ids is None:
            return {d.detection_id: default_object_id(d.detection_id) for d in detections}
        if len(object_ids) != len(detections):
            raise PerceptionError(f"object_ids has {len(object_ids)} id(s) but {len(detections)} object(s) were detected "
                                  f"(left to right: {[d.cls for d in detections]})")
        if len(set(object_ids)) != len(object_ids) or not all(i.strip() for i in object_ids):
            raise PerceptionError("object_ids must be unique and non-empty")
        return {d.detection_id: object_id for d, object_id in zip(detections, object_ids)}

    # ---------------------------------------------------------------- 3D で追っている物体のファイル

    def _save_tracks(self) -> None:
        if self.tracks_path is None:
            return
        try:
            self.tracks_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.tracks_path.with_suffix(self.tracks_path.suffix + ".tmp")
            tmp.write_text(json.dumps(self.tracker.to_dict()), encoding="utf-8")
            os.replace(tmp, self.tracks_path)
        except OSError as e:
            log.warning("perception: can't write %s: %s", self.tracks_path, e)

    def _load_tracks(self) -> None:
        if self.tracks_path is None or not self.tracks_path.exists():
            return
        try:
            self.tracker.load_dict(json.loads(self.tracks_path.read_text(encoding="utf-8")))
            log.info("perception: %d tracked object(s) from %s", len(self.tracker.objects), self.tracks_path)
        except (OSError, ValueError, KeyError) as e:
            log.warning("perception: can't read %s (starting empty): %s", self.tracks_path, e)

    # ---------------------------------------------------------------- run の記録

    def _save_run(self, result: AnalyzeResult, segmentation: Segmentation, jpeg: bytes, som_jpeg: bytes,
                  overlay_jpeg: bytes, answer: dict[str, Any] | None,
                  depth: tuple[np.ndarray, framelib.FrameMeta] | None) -> None:
        try:
            directory = self.runs_dir / result.run_id  # type: ignore[operator]
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "input.jpg").write_bytes(jpeg)
            (directory / "som.jpg").write_bytes(som_jpeg)
            (directory / "segmentation_overlay.jpg").write_bytes(overlay_jpeg)
            # 特徴量は長いので detections.json には入れない
            _write_json(directory / "detections.json", segmentation.model_dump(
                mode="json", by_alias=True, exclude={"detections": {"__all__": {"embedding"}}}))
            if answer is not None:
                _write_json(directory / "attributes.json", answer)
            if depth is not None:
                aligned, meta = depth
                _write_json(directory / "meta.json", meta.model_dump(mode="json"))
                overlay = framelib.depth_overlay(som.load_image(jpeg), aligned)
                (directory / "depth_overlay.jpg").write_bytes(som.to_jpeg(overlay))
            result.artifacts = {name: f"/perception/runs/{result.run_id}/{name}"
                                for name in RUN_FILES if (directory / name).exists() or name == "result.json"}
            _write_json(directory / "result.json", result.model_dump(mode="json", by_alias=True))
            with (self.runs_dir / "runs.jsonl").open("a", encoding="utf-8") as f:  # type: ignore[union-attr]
                f.write(json.dumps({"run_id": result.run_id, "at": datetime.now(timezone.utc).isoformat(),
                                    "objects": [o.object_id for o in result.objects],
                                    "vlm": result.vlm.model_dump(mode="json"), "timings_ms": result.timings_ms,
                                    "memory_stats": result.memory_stats,
                                    "frame": result.frame.model_dump(mode="json") if result.frame else None},
                                   ensure_ascii=False) + "\n")
        except OSError as e:
            log.warning("perception: can't save run %s: %s", result.run_id, e)

    def runs(self, limit: int = 20) -> list[dict[str, Any]]:
        """新しい順の run（runs.jsonl の行）。"""
        if self.runs_dir is None or not (self.runs_dir / "runs.jsonl").exists():
            return []
        lines = (self.runs_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in reversed(lines[-limit:]) if line.strip()]

    def run_file(self, run_id: str, name: str) -> Path | None:
        """run のファイルの場所。決めた名前だけ（ほかの場所は読ませない）。"""
        if self.runs_dir is None or name not in RUN_FILES or not run_id.replace("-", "").isalnum():
            return None
        path = self.runs_dir / run_id / name
        return path if path.is_file() else None


def _render(jpeg: bytes, detections: Sequence[Detection]) -> tuple[bytes, bytes, bytes]:
    """（VLM に見せる元の画像, SoM 画像, 確認用の分割結果）。

    小さい画像は、長い辺が MIN_DRAW_SIDE になるまで拡大してから描く（番号の札が物体に対して大きくなりすぎないように）。
    大きい画像は、描いてから VLM 用に縮める。"""
    image = som.load_image(jpeg)
    if max(image.size) < MIN_DRAW_SIDE:
        factor = MIN_DRAW_SIDE / max(image.size)
        image = image.resize((round(image.width * factor), round(image.height * factor)), Image.LANCZOS)
        detections = som.scale_detections(detections, factor)
    return (som.to_jpeg(image, MAX_IMAGE_SIDE), som.to_jpeg(som.draw_marks(image, detections), MAX_IMAGE_SIDE),
            som.to_jpeg(som.draw_overlay(image, detections)))


def _bbox_polygon(bbox: list[float]) -> list[list[float]]:
    x1, y1, x2, y2 = bbox
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]


def _jpeg_size(data: bytes) -> tuple[int, int]:
    import io

    try:
        with Image.open(io.BytesIO(data)) as image:
            return image.size
    except Exception as e:  # noqa: BLE001
        raise PerceptionError("rgb is not a readable image", 400) from e


def _run_id() -> str:
    return f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)
