"""起きたことの記録（誰が・いつ・何を）。実験のあとで追えるように、1 行 1 件の JSON で書き足す。

記録するもの:
  rpc     クライアントが呼んだ method（params と成否）。誰が呼んだか（actor）は session.identify で名乗る
  exec    実行の状態が変わった（start / pause / resume / stop / skip / retry / 終了など）
  skill   ロボットのスキルの始まり・phase・結果
  motion  動作計画を頼んだ・結果（step ごとの ok / infeasible と理由）

rpc 以外は、コンソールのログ（docker logs）にも 1 行で出す（rpc は session.py が出している）。

COGROUND_EVENT_LOG=/app/logs/events.jsonl があればファイルに書く。無ければメモリだけ（直近 TAIL 件。log.tail で読める）。
"""

from __future__ import annotations

import json
import logging
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

TAIL = 500


class EventLog:
    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path) if path else None
        self.recent: deque[dict[str, Any]] = deque(maxlen=TAIL)
        self._seq = 0

    @classmethod
    def from_env(cls) -> EventLog:
        return cls(os.environ.get("COGROUND_EVENT_LOG") or None)

    def add(self, type: str, actor: str = "system", **data: Any) -> dict[str, Any]:
        self._seq += 1
        record = {"seq": self._seq, "t": datetime.now(timezone.utc).isoformat(), "type": type, "actor": actor, **data}
        self.recent.append(record)
        if type != "rpc":
            level = logging.DEBUG if data.get("action") == "phase" else logging.INFO
            if log.isEnabledFor(level):
                fields = " ".join(f"{k}={json.dumps(v, ensure_ascii=False, default=str)}" for k, v in data.items()
                                  if v not in (None, "", [], {}) and k not in ("place", "pose"))
                log.log(level, "%s [%s] %s", type, actor, fields)
        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            except OSError as e:
                log.warning("event log: %s: %s", self.path, e)
        return record

    def tail(self, n: int = 50, type: str | None = None) -> list[dict[str, Any]]:
        items = [r for r in self.recent if type is None or r["type"] == type]
        return items[-n:]
