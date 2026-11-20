"""家の時計（home_local）。ルールの「18 時以降」などは、この時計の時刻で判定する。

デモや評価では時刻を差し替える（17:55 に依頼して 18:02 に進入、など）:
  clock.set(datetime)    その時刻に合わせる。そこから実時間と同じ速さで進む
  clock.freeze(datetime) その時刻で止める（テスト用。advance で進める）
  clock.reset()          実時刻に戻す

タイムゾーンは環境変数 COGROUND_HOME_TZ（既定は Asia/Tokyo）。
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo

DEFAULT_TZ = "Asia/Tokyo"


class HomeClock:
    def __init__(self, tz: str | None = None, source: Callable[[], datetime] | None = None) -> None:
        self.tz = ZoneInfo(tz or os.environ.get("COGROUND_HOME_TZ") or DEFAULT_TZ)
        self._source = source or (lambda: datetime.now(timezone.utc))  # 実時刻（テストで差し替えられる）
        self._offset = timedelta(0)
        self._frozen: datetime | None = None

    def now(self) -> datetime:
        if self._frozen is not None:
            return self._frozen
        return (self._source() + self._offset).astimezone(self.tz)

    @property
    def overridden(self) -> bool:
        return self._frozen is not None or self._offset != timedelta(0)

    def set(self, t: datetime) -> None:
        self._frozen = None
        self._offset = self._local(t) - self._source()

    def freeze(self, t: datetime) -> None:
        self._frozen = self._local(t)

    def advance(self, seconds: float) -> None:
        """時計を進める。止めているときは止めた時刻を、動いているときはずれを進める。"""
        if self._frozen is not None:
            self._frozen += timedelta(seconds=seconds)
        else:
            self._offset += timedelta(seconds=seconds)

    def reset(self) -> None:
        self._offset, self._frozen = timedelta(0), None

    def at(self, hhmm: str) -> datetime:
        """今日のその時刻（家の時計）。clock.set(clock.at("17:55")) のように使う。"""
        h, m = hhmm.split(":")
        return self.now().replace(hour=int(h), minute=int(m), second=0, microsecond=0)

    def snapshot(self) -> dict[str, object]:
        return {"now": self.now().isoformat(), "tz": str(self.tz), "overridden": self.overridden,
                "frozen": self._frozen is not None}

    def _local(self, t: datetime) -> datetime:
        # タイムゾーンが無い時刻は、家の時計の時刻とみなす
        return t.replace(tzinfo=self.tz) if t.tzinfo is None else t.astimezone(self.tz)
