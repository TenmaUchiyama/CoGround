"""detector コンテナ（YOLOE-seg、segmentation.py）の POST /segment を呼ぶ。

COGROUND_DETECTOR_URL  detector の場所（既定 http://detector:8001。compose の中のサービス名）
"""

from __future__ import annotations

import os
from typing import Protocol

from .schema import Segmentation

DEFAULT_DETECTOR_URL = "http://detector:8001"


class SegmentError(Exception):
    """分割できなかった。status は HTTP で返すときの番号。"""

    def __init__(self, message: str, status: int = 502) -> None:
        super().__init__(message)
        self.status = status


class Segmenter(Protocol):
    async def segment(self, jpeg: bytes, embed: bool = False) -> Segmentation: ...


class HttpSegmenter:
    def __init__(self, url: str | None = None, timeout: float = 30.0) -> None:
        self.url = (url or os.environ.get("COGROUND_DETECTOR_URL") or DEFAULT_DETECTOR_URL).rstrip("/")
        self.timeout = timeout

    async def segment(self, jpeg: bytes, embed: bool = False) -> Segmentation:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.url}/segment", params={"embed": 1} if embed else None, content=jpeg, headers={"Content-Type": "image/jpeg"})
        except httpx.HTTPError as e:
            raise SegmentError(f"Can't reach the detector at {self.url} ({type(e).__name__}). Is the detector container up?") from e
        if response.status_code != 200:
            try:
                detail = response.json().get("detail")
            except ValueError:
                detail = response.text[:200]
            # 画像が悪い（400 / 413 / 415）はそのまま返す。それ以外は detector 側の問題
            status = response.status_code if response.status_code in (400, 413, 415) else 502
            raise SegmentError(f"The detector answered {response.status_code}: {detail}", status)
        return Segmentation.model_validate(response.json())
