"""method / event ハンドラ。新しい機能はモジュールを足して build_router() に加える。"""

from __future__ import annotations

from ..rpc import Router
from . import debug, scene, system


def build_router() -> Router:
    router = Router()
    for module in (system, scene, debug):
        router.include(module.router)
    return router
