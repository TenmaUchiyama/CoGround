"""method（要求→応答）と event（一方向の通知）の登録先。

    router = Router()

    class Params(BaseModel):
        count: int

    @router.method("debug.count", params=Params, streams=True)
    async def count(ctx: RequestContext, p: Params):
        await ctx.stream({"i": 0})     # 途中経過（任意）
        return {"done": p.count}       # これが response の result になる

    @router.on_event("client.log")
    async def on_log(session, data: dict): ...
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from pydantic import BaseModel, ConfigDict
from pydantic_core import to_jsonable_python

from . import protocol

if TYPE_CHECKING:
    from .services import Services
    from .session import Session


class EmptyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


@dataclass
class RequestContext:
    session: Session
    request_id: str
    services: Services

    async def stream(self, data: Any) -> None:
        """この request の途中経過を送る（response より前に何度でも）。"""
        await self.session.send(protocol.stream(self.request_id, to_jsonable(data)))


MethodHandler = Callable[[RequestContext, Any], Awaitable[Any]]
EventHandler = Callable[["Session", dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class MethodSpec:
    name: str
    handler: MethodHandler
    params_model: type[BaseModel]
    description: str
    streams: bool


class Router:
    def __init__(self) -> None:
        self.methods: dict[str, MethodSpec] = {}
        self.events: dict[str, EventHandler] = {}

    def method(
        self,
        name: str,
        *,
        params: type[BaseModel] = EmptyParams,
        description: str = "",
        streams: bool = False,
    ) -> Callable[[MethodHandler], MethodHandler]:
        def decorator(fn: MethodHandler) -> MethodHandler:
            if name in self.methods:
                raise ValueError(f"method {name!r} is already registered")
            self.methods[name] = MethodSpec(name, fn, params, description, streams)
            return fn

        return decorator

    def on_event(self, name: str) -> Callable[[EventHandler], EventHandler]:
        def decorator(fn: EventHandler) -> EventHandler:
            if name in self.events:
                raise ValueError(f"event handler {name!r} is already registered")
            self.events[name] = fn
            return fn

        return decorator

    def include(self, other: Router) -> None:
        for name, spec in other.methods.items():
            if name in self.methods:
                raise ValueError(f"method {name!r} is already registered")
            self.methods[name] = spec
        for name, handler in other.events.items():
            if name in self.events:
                raise ValueError(f"event handler {name!r} is already registered")
            self.events[name] = handler

    def describe(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "streams": spec.streams,
                "params_schema": spec.params_model.model_json_schema(),
            }
            for spec in sorted(self.methods.values(), key=lambda s: s.name)
        ]


def to_jsonable(value: Any) -> Any:
    return to_jsonable_python(value)
