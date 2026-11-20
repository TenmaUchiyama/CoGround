"""Object Memory: 物体（object_id）ごとの属性を覚えておき、同じ物体で VLM を 2 回呼ばないようにする。

使い方（pipeline.py）:
  claim = memory.claim(ids)        # 同期。ここで「だれが解析するか」が決まる
    claim.new      この依頼が解析する（vlm_status = pending になった）
    claim.cached   属性がある（completed）。保存した値を使う
    claim.waiting  ほかの依頼が解析中（pending）。await memory.wait(ids) で終わるのを待つ
  memory.complete(id, ...) / memory.fail(id, error)   # new の結果を書く。待っている依頼が動き出す

claim は await をはさまないので、同時に来た依頼のうち 1 つだけが new を受け取る（重複して VLM を呼ばない）。
failed の物体は、次の claim でもう一度 new になる（やり直せる）。

COGROUND_OBJECT_MEMORY=/app/data/object_memory.json があれば、変わるたびにファイルに書く（再起動しても残る）。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .schema import ObjectRecord

log = logging.getLogger(__name__)


@dataclass
class Claim:
    new: list[str] = field(default_factory=list)
    cached: list[str] = field(default_factory=list)
    waiting: list[str] = field(default_factory=list)


class ObjectMemory:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.objects: dict[str, ObjectRecord] = {}
        self.vlm_calls = 0  # VLM を呼んだ回数（1 回で複数の物体を聞いても 1）
        self._inflight: dict[str, asyncio.Event] = {}
        if self.path is not None and self.path.exists():
            self._load()

    @classmethod
    def from_env(cls) -> ObjectMemory:
        return cls(os.environ.get("COGROUND_OBJECT_MEMORY") or None)

    # ---------------------------------------------------------------- 解析の割り当て

    def claim(self, object_ids: Iterable[str], *, reanalyze: bool = False, required: Iterable[str] = ()) -> Claim:
        """object_ids を「解析する / 記憶を使う / 待つ」に分ける。reanalyze なら、属性があっても解析し直す。

        required は、いまのルールが使っている属性。記憶の属性にそれが無い物体は、解析し直す
        （ルールを足したあと、前に見た物体にも新しい属性を聞くため）。"""
        required = list(required)
        claim = Claim()
        now = time.time()
        for object_id in object_ids:
            record = self.objects.get(object_id)
            if record is not None and object_id in self._inflight:
                claim.waiting.append(object_id)
            elif (record is not None and record.vlm_status == "completed" and not reanalyze
                  and all(name in record.attributes for name in required)):
                record.cache_hits += 1
                claim.cached.append(object_id)
            else:
                if record is None:
                    record = self.objects[object_id] = ObjectRecord(object_id=object_id, created_at=now)
                record.vlm_status = "pending"
                record.error = None
                self._inflight[object_id] = asyncio.Event()
                claim.new.append(object_id)
        return claim

    def count_vlm_call(self, object_ids: Iterable[str]) -> None:
        """VLM を 1 回呼んだ（object_ids をまとめて聞いた）。"""
        self.vlm_calls += 1
        for object_id in object_ids:
            self.objects[object_id].vlm_calls += 1

    def complete(self, object_id: str, category: str, attributes: dict[str, str],
                 evidence: dict[str, str] | None = None) -> ObjectRecord:
        record = self.objects[object_id]
        record.category = category
        record.attributes = dict(attributes)
        record.evidence = dict(evidence or {})
        record.vlm_status = "completed"
        record.attribute_version += 1
        record.error = None
        record.updated_at = time.time()
        self._release(object_id)
        return record

    def fail(self, object_id: str, error: str) -> ObjectRecord:
        """解析できなかった。前に得た属性があれば残す（attribute_version は変えない）。"""
        record = self.objects[object_id]
        record.vlm_status = "failed"
        record.error = error
        self._release(object_id)
        return record

    def _release(self, object_id: str) -> None:
        event = self._inflight.pop(object_id, None)
        if event is not None:
            event.set()

    async def wait(self, object_ids: Iterable[str]) -> None:
        """ほかの依頼が解析している物体の結果を待つ。"""
        events = [self._inflight[i] for i in object_ids if i in self._inflight]
        for event in events:
            await event.wait()

    # ---------------------------------------------------------------- 見えたことの記録

    def observe(self, object_id: str, *, detected_class: str, bbox: list[float], run_id: str) -> None:
        record = self.objects.get(object_id)
        if record is None:
            return
        record.detected_class = detected_class
        record.last_bbox = bbox
        record.last_run_id = run_id
        record.last_seen_at = time.time()

    # ---------------------------------------------------------------- 読む・消す

    def get(self, object_id: str) -> ObjectRecord | None:
        return self.objects.get(object_id)

    def stats(self) -> dict[str, Any]:
        records = list(self.objects.values())
        return {
            "objects": len(records),
            "completed": sum(r.vlm_status == "completed" for r in records),
            "pending": sum(r.vlm_status == "pending" for r in records),
            "failed": sum(r.vlm_status == "failed" for r in records),
            "vlm_calls": self.vlm_calls,
            "cache_hits": sum(r.cache_hits for r in records),
        }

    def snapshot(self) -> dict[str, Any]:
        return {"stats": self.stats(), "objects": [r.model_dump(mode="json") for r in self.objects.values()]}

    def forget(self, object_id: str) -> bool:
        """物体を 1 つ忘れる。解析中のものは消さない（False）。"""
        if object_id in self._inflight or object_id not in self.objects:
            return False
        del self.objects[object_id]
        self.save()
        return True

    def reset(self) -> None:
        """全部忘れる（解析中のものは残す）。VLM の回数も 0 に戻す。"""
        self.objects = {i: r for i, r in self.objects.items() if i in self._inflight}
        self.vlm_calls = 0
        self.save()

    # ---------------------------------------------------------------- ファイル

    def save(self) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps({"vlm_calls": self.vlm_calls,
                                       "objects": [r.model_dump(mode="json") for r in self.objects.values()]},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as e:
            log.warning("object memory: can't write %s: %s", self.path, e)

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
            self.vlm_calls = int(data.get("vlm_calls", 0))
            for raw in data.get("objects", []):
                record = ObjectRecord.model_validate(raw)
                if record.vlm_status == "pending":
                    # 解析の途中でサーバーが止まった。次に見えたときにやり直す
                    record.vlm_status = "failed"
                    record.error = "interrupted (server restarted during analysis)"
                self.objects[record.object_id] = record
            log.info("object memory: %d object(s) from %s", len(self.objects), self.path)
        except (OSError, ValueError) as e:
            log.warning("object memory: can't read %s (starting empty): %s", self.path, e)
