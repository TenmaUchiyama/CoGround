"""LLM の口（llm/client.py）: どちらを使うかの選び方と、API キーで呼ぶ口の答えの扱い（ネットワークは使わない）。"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from coground_server.llm import AgentSdkLlm, AnthropicApiLlm, LlmError, make_llm
from coground_server.llm.client import DEFAULT_API_MODEL


class Answer(BaseModel):
    reply: str


class _Usage:
    def model_dump(self, **_: Any) -> dict[str, int]:
        return {"input_tokens": 10, "output_tokens": 5}


def _response(text: str | None, stop_reason: str = "end_turn", stop_details: Any = None) -> Any:
    content = [SimpleNamespace(type="thinking", thinking="")]
    if text is not None:
        content.append(SimpleNamespace(type="text", text=text))
    return SimpleNamespace(model="claude-opus-5-5", usage=_Usage(), stop_reason=stop_reason,
                           stop_details=stop_details, content=content, _request_id="req_test")


class _FakeMessages:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self.responses.pop(0)


def _api(responses: list[Any], monkeypatch: pytest.MonkeyPatch, **env: str) -> tuple[AnthropicApiLlm, _FakeMessages]:
    for key in ("COGROUND_LLM_MODEL", "COGROUND_LLM_EFFORT", "COGROUND_LLM_LOG"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    llm = AnthropicApiLlm()
    messages = _FakeMessages(responses)
    llm._client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return llm, messages


def _generate(llm: AnthropicApiLlm) -> Answer:
    return asyncio.run(llm.generate(name="test", system="sys", prompt="hello", output=Answer))


def test_make_llm_prefers_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COGROUND_LLM_BACKEND", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert isinstance(make_llm(), AnthropicApiLlm)
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert isinstance(make_llm(), AgentSdkLlm)
    monkeypatch.setenv("COGROUND_LLM_BACKEND", "agent_sdk")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert isinstance(make_llm(), AgentSdkLlm)
    monkeypatch.setenv("COGROUND_LLM_BACKEND", "other")
    with pytest.raises(ValueError):
        make_llm()


def test_api_returns_typed_answer(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    log_path = tmp_path / "llm.jsonl"
    llm, messages = _api([_response('{"reply": "pong"}')], monkeypatch, COGROUND_LLM_LOG=str(log_path))
    assert _generate(llm).reply == "pong"

    call = messages.calls[0]
    assert call["model"] == DEFAULT_API_MODEL
    assert call["system"] == "sys"
    assert call["messages"] == [{"role": "user", "content": "hello"}]
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert call["output_config"]["format"]["schema"]["additionalProperties"] is False
    assert "effort" not in call["output_config"]
    assert call["fallbacks"] == "default"

    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert record["backend"] == "api" and record["request_id"] == "req_test"
    assert record["usage"] == {"input_tokens": 10, "output_tokens": 5}
    assert record["output"] == {"reply": "pong"}


def test_api_model_and_effort_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    llm, messages = _api([_response('{"reply": "x"}')], monkeypatch,
                         COGROUND_LLM_MODEL="claude-sonnet-5-5", COGROUND_LLM_EFFORT="low")
    _generate(llm)
    assert messages.calls[0]["model"] == "claude-sonnet-5-5"
    assert messages.calls[0]["output_config"]["effort"] == "low"


def test_api_retries_once_when_answer_does_not_match(monkeypatch: pytest.MonkeyPatch) -> None:
    llm, messages = _api([_response('{"other": 1}'), _response('{"reply": "ok"}')], monkeypatch)
    assert _generate(llm).reply == "ok"
    assert len(messages.calls) == 2


@pytest.mark.parametrize("response, message", [
    (_response(None, "refusal", SimpleNamespace(category="cyber", explanation="x")), "refused"),
    (_response('{"reply": "cut', "max_tokens"), "cut off"),
    (_response("not json"), "is not JSON"),
    (_response(None), "has no text"),
])
def test_api_errors_become_llm_error(monkeypatch: pytest.MonkeyPatch, response: Any, message: str) -> None:
    llm, _ = _api([response], monkeypatch)
    with pytest.raises(LlmError, match=message):
        _generate(llm)
