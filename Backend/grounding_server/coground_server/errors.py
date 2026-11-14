"""response の error.code に入る値。Unity 側はこの文字列で分岐する。"""

from __future__ import annotations

from typing import Any


class ErrorCode:
    BAD_MESSAGE = "bad_message"  # JSON として読めない / 形式が違う
    UNKNOWN_METHOD = "unknown_method"  # method が登録されていない
    INVALID_PARAMS = "invalid_params"  # params が method のスキーマに合わない
    DUPLICATE_ID = "duplicate_id"  # 同じ id の request が処理中
    CANCELLED = "cancelled"  # cancel で中断した
    INTERNAL = "internal_error"  # ハンドラ内の想定外の例外


class RpcError(Exception):
    """ハンドラから投げると、そのまま error response になる。"""

    def __init__(self, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
