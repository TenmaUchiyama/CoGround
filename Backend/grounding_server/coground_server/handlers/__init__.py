"""method / event ハンドラ。新しい機能はモジュールを足して build_router() に加える。"""

from __future__ import annotations

from ..rpc import Router
from . import debug, execution, home, llm, plan, robot_test, rules, scene, sequence, system, task


def build_router() -> Router:
    router = Router()
    for module in (system, scene, rules, task, sequence, home, plan, execution, robot_test, llm, debug):
        router.include(module.router)
    return router
