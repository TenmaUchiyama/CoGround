"""1 本の WebSocket 接続（= Unity クライアント 1 つ）を扱う。

- request は 1 つずつ asyncio.Task で並行に処理する（長い LLM 呼び出しが他を止めない）
- 送信は 1 本のロックで直列化する（stream / response / event が混ざって壊れないように）
- 接続直後に session.welcome と state.updated（現在の全体状態）を送る。
  再接続したクライアントはこれだけで最新状態に戻れる
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from . import __version__, protocol
from .errors import ErrorCode, RpcError
from .rpc import MethodSpec, RequestContext, Router, to_jsonable

if TYPE_CHECKING:
    from .services import Services

log = logging.getLogger(__name__)


class Session:
    def __init__(self, ws: WebSocket, router: Router, services: Services) -> None:
        self.id = uuid.uuid4().hex[:8]
        self.ws = ws
        self.router = router
        self.services = services
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._send_lock = asyncio.Lock()
        self._closed = False
        self.actor = "user"  # だれの操作か（user / llm / script）。session.identify で名乗る。記録（eventlog）に残る

    @property
    def client(self) -> str:
        c = self.ws.client
        return f"{c.host}:{c.port}" if c else "?"

    # ------------------------------------------------------------------ 送信

    async def send(self, message: dict[str, Any]) -> None:
        if self._closed:
            return
        text = json.dumps(message, ensure_ascii=False)
        try:
            async with self._send_lock:
                await self.ws.send_text(text)
        except Exception as e:  # 切断済みなど
            log.debug("session %s: send failed: %s", self.id, e)
            self._closed = True

    async def send_event(self, name: str, data: Any) -> None:
        await self.send(protocol.event(name, to_jsonable(data)))

    async def _session_error(self, code: str, message: str, details: Any = None) -> None:
        """id が分からないメッセージの失敗は、session.error イベントで知らせる。"""
        log.warning("session %s: %s: %s", self.id, code, message)
        data: dict[str, Any] = {"code": code, "message": message}
        if details is not None:
            data["details"] = details
        await self.send(protocol.event("session.error", data))

    # ------------------------------------------------------------------ 受信ループ

    async def run(self) -> None:
        await self.ws.accept()
        self.services.hub.add(self)
        log.info("session %s: connected from %s", self.id, self.client)
        try:
            await self.send_event(
                "session.welcome",
                {
                    "session_id": self.id,
                    "server_version": __version__,
                    "protocol_version": protocol.PROTOCOL_VERSION,
                    "methods": sorted(self.router.methods),
                },
            )
            await self.send_event("state.updated", self.services.snapshot())

            while True:
                raw = await self.ws.receive()
                if raw["type"] == "websocket.disconnect":
                    break
                text = raw.get("text")
                if text is None:
                    data = raw.get("bytes") or b""
                    try:
                        text = data.decode("utf-8")
                    except UnicodeDecodeError:
                        await self._session_error(ErrorCode.BAD_MESSAGE, "Not readable as UTF-8")
                        continue
                await self._handle_text(text)
        except WebSocketDisconnect:
            pass
        finally:
            self._closed = True
            self.services.hub.remove(self)
            tasks = list(self._tasks.values())
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            log.info("session %s: disconnected", self.id)

    async def _handle_text(self, text: str) -> None:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            await self._session_error(ErrorCode.BAD_MESSAGE, f"Not readable as JSON: {e}")
            return

        try:
            msg = protocol.CLIENT_MESSAGE.validate_python(data)
        except ValidationError as e:
            details = _validation_details(e)
            request_id = (
                data.get("id")
                if isinstance(data, dict) and data.get("type") == "request"
                else None
            )
            if isinstance(request_id, str) and request_id:
                log.warning("session %s: request [%s] rejected: bad_message", self.id, request_id)
                await self.send(
                    protocol.response_error(
                        request_id, ErrorCode.BAD_MESSAGE, "Wrong message format", details
                    )
                )
            else:
                await self._session_error(ErrorCode.BAD_MESSAGE, "Wrong message format", details)
            return

        if isinstance(msg, protocol.RequestMessage):
            await self._start_request(msg)
        elif isinstance(msg, protocol.CancelMessage):
            self._cancel(msg.id)
        else:
            await self._handle_event(msg)

    # ------------------------------------------------------------------ request

    async def _start_request(self, msg: protocol.RequestMessage) -> None:
        def reject(code: str) -> None:
            log.warning("session %s: %s [%s] rejected: %s", self.id, msg.method, msg.id, code)

        if msg.id in self._tasks:
            reject(ErrorCode.DUPLICATE_ID)
            await self.send(
                protocol.response_error(
                    msg.id, ErrorCode.DUPLICATE_ID, f"Request with id {msg.id!r} is still in progress"
                )
            )
            return

        spec = self.router.methods.get(msg.method)
        if spec is None:
            reject(ErrorCode.UNKNOWN_METHOD)
            await self.send(
                protocol.response_error(
                    msg.id,
                    ErrorCode.UNKNOWN_METHOD,
                    f"No method {msg.method!r}",
                    {"available": sorted(self.router.methods)},
                )
            )
            return

        try:
            params = spec.params_model.model_validate(msg.params or {})
        except ValidationError as e:
            reject(ErrorCode.INVALID_PARAMS)
            await self.send(
                protocol.response_error(
                    msg.id, ErrorCode.INVALID_PARAMS, "Invalid params", _validation_details(e)
                )
            )
            return

        task = asyncio.create_task(
            self._run_request(spec, msg.id, params), name=f"rpc:{msg.method}:{msg.id}"
        )
        self._tasks[msg.id] = task

        def _forget(t: asyncio.Task[None], request_id: str = msg.id) -> None:
            if self._tasks.get(request_id) is t:
                del self._tasks[request_id]

        task.add_done_callback(_forget)

    async def _run_request(self, spec: MethodSpec, request_id: str, params: BaseModel) -> None:
        ctx = RequestContext(session=self, request_id=request_id, services=self.services)
        started = time.perf_counter()
        tag = f"session {self.id}: {spec.name} [{request_id}]"
        quiet = spec.name in _QUIET  # 1 秒に何度も届く method は、成功のログを出さない
        if not quiet:
            log.info("%s <- request", tag)

        def elapsed() -> str:
            return f"{(time.perf_counter() - started) * 1000:.0f}ms"

        def record(outcome: str) -> None:
            if spec.name in _NOT_LOGGED:
                return
            # シーンは大きく、何度も届くので、中身は記録しない
            logged = None if spec.name == "scene.update" else params.model_dump(mode="json", by_alias=True)
            self.services.events.add("rpc", self.actor, session=self.id, method=spec.name, params=logged, outcome=outcome)

        try:
            result = await spec.handler(ctx, params)
            await self.send(protocol.response_ok(request_id, to_jsonable(result)))
            if not quiet:
                log.info("%s -> ok (%s)", tag, elapsed())
                record("ok")
        except asyncio.CancelledError:
            if self._closed:
                raise
            await self.send(
                protocol.response_error(request_id, ErrorCode.CANCELLED, "Cancelled")
            )
            log.info("%s -> cancelled (%s)", tag, elapsed())
        except RpcError as e:
            await self.send(protocol.response_error(request_id, e.code, e.message, e.details))
            log.warning("%s -> error %s: %s (%s)", tag, e.code, e.message, elapsed())
            record(f"error: {e.code}: {e.message}")
        except Exception as e:
            log.exception("%s -> internal error (%s)", tag, elapsed())
            await self.send(
                protocol.response_error(
                    request_id, ErrorCode.INTERNAL, f"{type(e).__name__}: {e}"
                )
            )

    def _cancel(self, request_id: str) -> None:
        task = self._tasks.get(request_id)
        log.info("session %s: cancel [%s]%s", self.id, request_id, "" if task else " (already finished)")
        if task is not None:
            task.cancel()
        # 終わった request の cancel は無視する（行き違いは普通に起きる）

    # ------------------------------------------------------------------ event

    async def _handle_event(self, msg: protocol.EventMessage) -> None:
        handler = self.router.events.get(msg.event)
        log.debug("session %s: event %s <- %s", self.id, msg.event, msg.data)
        if handler is None:
            log.info("session %s: no handler for event %r", self.id, msg.event)
            return
        try:
            await handler(self, msg.data or {})
        except Exception:
            log.exception("session %s: event handler %r failed", self.id, msg.event)


# 記録（eventlog）に残さない method（読むだけのもの）
_NOT_LOGGED = {"system.ping", "system.describe", "state.get", "log.tail", "llm.ping"}
_QUIET = frozenset({"people.update"})


def _validation_details(e: ValidationError) -> Any:
    return json.loads(e.json(include_url=False))
