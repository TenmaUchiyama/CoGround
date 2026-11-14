"""接続中のセッションの一覧と、全員への event 送信。"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from . import protocol
from .rpc import to_jsonable

if TYPE_CHECKING:
    from .session import Session


class Hub:
    def __init__(self) -> None:
        self._sessions: set[Session] = set()

    def add(self, session: Session) -> None:
        self._sessions.add(session)

    def remove(self, session: Session) -> None:
        self._sessions.discard(session)

    @property
    def count(self) -> int:
        return len(self._sessions)

    async def broadcast(self, name: str, data: Any) -> None:
        message = protocol.event(name, to_jsonable(data))
        await asyncio.gather(
            *(s.send(message) for s in list(self._sessions)), return_exceptions=True
        )
