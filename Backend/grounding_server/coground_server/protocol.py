"""WebSocket で Unity とやりとりするメッセージの形式。

すべて 1 メッセージ = 1 つの JSON オブジェクト（テキストフレーム）。`type` で種類を分ける。

  Unity → サーバー
    request  {"type": "request", "id": "u-1", "method": "scene.update", "params": {...}}
    cancel   {"type": "cancel", "id": "u-1"}
    event    {"type": "event", "event": "client.log", "data": {...}}

  サーバー → Unity
    response {"type": "response", "id": "u-1", "ok": true,  "result": {...}}
             {"type": "response", "id": "u-1", "ok": false, "error": {"code": "...", "message": "...", "details": ...}}
    stream   {"type": "stream", "id": "u-1", "data": {...}}      # request の途中経過（response より前に 0 回以上）
    event    {"type": "event", "event": "state.updated", "data": {...}}

1 つの request には必ず 1 つの response が返る（成功・失敗・キャンセルのどれか）。
詳細は README.md の「プロトコル」。
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

PROTOCOL_VERSION = 1


class _Message(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequestMessage(_Message):
    type: Literal["request"]
    id: str = Field(min_length=1, max_length=128)
    method: str = Field(min_length=1, max_length=128)
    params: dict[str, Any] | None = None


class CancelMessage(_Message):
    type: Literal["cancel"]
    id: str = Field(min_length=1, max_length=128)


class EventMessage(_Message):
    type: Literal["event"]
    event: str = Field(min_length=1, max_length=128)
    data: dict[str, Any] | None = None


ClientMessage = Annotated[
    Union[RequestMessage, CancelMessage, EventMessage],
    Field(discriminator="type"),
]
CLIENT_MESSAGE: TypeAdapter[ClientMessage] = TypeAdapter(ClientMessage)


def response_ok(request_id: str, result: Any) -> dict[str, Any]:
    return {"type": "response", "id": request_id, "ok": True, "result": result}


def response_error(
    request_id: str, code: str, message: str, details: Any = None
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"type": "response", "id": request_id, "ok": False, "error": error}


def stream(request_id: str, data: Any) -> dict[str, Any]:
    return {"type": "stream", "id": request_id, "data": data}


def event(name: str, data: Any) -> dict[str, Any]:
    return {"type": "event", "event": name, "data": data}
