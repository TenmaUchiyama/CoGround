"""ハンドラから使う共有オブジェクト（ctx.services）。LLM / VLM / clingo もここに足していく。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .hub import Hub
from .state import StateStore


@dataclass
class Services:
    hub: Hub = field(default_factory=Hub)
    state: StateStore = field(default_factory=StateStore)

    async def publish_state(self) -> None:
        """現在の全体状態を全クライアントに送る。状態を変えたら必ず呼ぶ。"""
        logging.getLogger(__name__).info(
            "state v%d -> %d client(s)", self.state.version, self.hub.count
        )
        await self.hub.broadcast("state.updated", self.state.snapshot())
