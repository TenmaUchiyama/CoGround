"""LLM を 1 回呼び、決めた型（Pydantic モデル）で答えを受け取る口。

本物は 2 つ。どちらもツールは使わせず、JSON Schema に合った答えを 1 つ返させるだけ。

  AnthropicApiLlm  Anthropic の API キーで Messages API を直接呼ぶ（anthropic SDK。structured outputs）。
                   CLI を起動しないので速い。使った分だけ API の料金がかかる
  AgentSdkLlm      Claude Agent SDK（claude-agent-sdk。Claude Code の CLI を子プロセスで動かす）。
                   Claude のサブスクリプション（CLAUDE_CODE_OAUTH_TOKEN）で動かせる。1 回ごとに CLI を起動するので数秒かかる

どちらを使うか（make_llm）:
  COGROUND_LLM_BACKEND  api / agent_sdk。省略すると、ANTHROPIC_API_KEY があれば api、無ければ agent_sdk

認証（コンテナの環境変数。.env に書く）:
  ANTHROPIC_API_KEY        Anthropic の API キー（api。agent_sdk でも使える）
  CLAUDE_CODE_OAUTH_TOKEN  Claude のサブスクリプション（agent_sdk だけ。ホストで `claude setup-token` を実行して作る）

設定（環境変数）:
  COGROUND_LLM_MODEL    モデル名（省略すると api は DEFAULT_API_MODEL、agent_sdk は CLI の既定）
  COGROUND_LLM_EFFORT   low / medium / high / xhigh / max（省略するとモデルの既定）
  COGROUND_LLM_TIMEOUT  1 回の呼び出しを待つ秒数（既定 120）
  COGROUND_LLM_LOG      呼び出しの記録を足していく JSONL ファイル（省略すると書かない）。
                        実験で「どのプロンプトにどう答えたか」を後から確かめるため
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Callable, Protocol, Sequence, TypeVar

from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LlmError(Exception):
    """LLM を呼べなかった、または決めた型の答えが返らなかった。"""


class LlmClient(Protocol):
    async def generate(self, *, name: str, system: str, prompt: str, output: type[T],
                       images: Sequence[bytes] | None = None) -> T:
        """system と prompt を渡し、output の型の答えを返す。name は記録用（"compile_rule" など）。
        images（JPEG のバイト列）を渡すと、prompt の前に画像として付ける（VLM として使う。perception/vlm_analyzer.py）。"""
        ...


DEFAULT_API_MODEL = "claude-opus-5-5"


def _user_content(prompt: str, images: Sequence[bytes] | None) -> str | list[dict[str, Any]]:
    """user メッセージの中身。画像があれば、画像 → 文の順のブロックにする。"""
    if not images:
        return prompt
    blocks: list[dict[str, Any]] = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                     "data": base64.standard_b64encode(data).decode("ascii")}}
        for data in images
    ]
    return [*blocks, {"type": "text", "text": prompt}]


def make_llm() -> LlmClient:
    """環境変数から、本物の LLM の口を選ぶ（上の「どちらを使うか」）。"""
    backend = (os.environ.get("COGROUND_LLM_BACKEND") or "").strip().lower()
    if not backend:
        backend = "api" if os.environ.get("ANTHROPIC_API_KEY") else "agent_sdk"
    if backend == "api":
        return AnthropicApiLlm()
    if backend == "agent_sdk":
        return AgentSdkLlm()
    raise ValueError(f"COGROUND_LLM_BACKEND must be api or agent_sdk: {backend!r}")


class _RecordedLlm:
    """1 回の呼び出しの共通部分: 型に合わなければ 1 回だけやり直す、記録（ログと JSONL）を残す。

    子クラスは _call で「型に合うはずの JSON（dict など）」を返す。
    """

    backend = ""

    def __init__(self) -> None:
        self.model = os.environ.get("COGROUND_LLM_MODEL") or None
        self.effort = os.environ.get("COGROUND_LLM_EFFORT") or None
        self.timeout = float(os.environ.get("COGROUND_LLM_TIMEOUT", "120"))
        self.log_path = os.environ.get("COGROUND_LLM_LOG") or None

    async def _call(self, system: str, prompt: str, output: type[BaseModel], record: dict[str, Any],
                    images: Sequence[bytes] | None = None) -> Any:
        raise NotImplementedError

    async def generate(self, *, name: str, system: str, prompt: str, output: type[T],
                       images: Sequence[bytes] | None = None) -> T:
        started = time.monotonic()
        record: dict[str, Any] = {
            "at": datetime.now(timezone.utc).isoformat(), "name": name, "backend": self.backend,
            "system": system, "prompt": prompt,
        }
        if images:
            # 画像そのものは記録に入れない（大きいので）。どの画像だったかは大きさとハッシュで追える
            record["images"] = [{"bytes": len(d), "sha256": hashlib.sha256(d).hexdigest()[:16]} for d in images]
        try:
            # 型に合わない答えが返ったら、1 回だけやり直す
            for attempt in (1, 2):
                raw = await self._call(system, prompt, output, record, images)
                try:
                    value = output.model_validate(raw)
                    break
                except ValidationError as e:
                    log.warning("llm %s: 答えが型に合わない（%d 回目）: %s", name, attempt, e)
                    if attempt == 2:
                        raise LlmError(f"The LLM's answer doesn't match the {output.__name__} type") from e
            record["output"] = value.model_dump(mode="json")
            return value
        except LlmError as e:
            record["error"] = str(e)
            raise
        finally:
            record["seconds"] = round(time.monotonic() - started, 2)
            log.info("llm %s: %s (%.1fs, %s, model=%s, $%s)", name, "error" if "error" in record else "ok",
                     record["seconds"], self.backend, record.get("model"), record.get("cost_usd"))
            self._write_log(record)

    def _write_log(self, record: dict[str, Any]) -> None:
        if not self.log_path:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except OSError as e:
            log.warning("LLM の記録を書けない (%s): %s", self.log_path, e)


class AnthropicApiLlm(_RecordedLlm):
    """API キー（ANTHROPIC_API_KEY）で Messages API を直接呼ぶ。

    答えの型は structured outputs（output_config.format）で JSON Schema に縛る。
    安全のための判定で断られた（stop_reason = refusal）ときは、サーバー側で別のモデルが答え直す
    （fallbacks = default。どのモデルに替わったかは記録の model に残る）。
    """

    backend = "api"
    MAX_TOKENS = 16000
    FALLBACK_BETA = "server-side-fallback-2026-07-01"

    def __init__(self) -> None:
        super().__init__()
        self.model = self.model or DEFAULT_API_MODEL
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic
            except ImportError as e:
                raise LlmError("anthropic is not installed (rebuild the image with make build)") from e
            # ANTHROPIC_API_KEY は SDK が環境変数から読む。時間切れ・429・5xx は SDK が 2 回までやり直す
            self._client = anthropic.AsyncAnthropic(timeout=self.timeout, max_retries=2)
        return self._client

    async def _call(self, system: str, prompt: str, output: type[BaseModel], record: dict[str, Any],
                    images: Sequence[bytes] | None = None) -> Any:
        client = self._get_client()
        import anthropic

        output_config: dict[str, Any] = {
            # SDK の transform_schema で、structured outputs が受け付ける形に直す
            "format": {"type": "json_schema", "schema": anthropic.transform_schema(output.model_json_schema())},
        }
        if self.effort:
            output_config["effort"] = self.effort
        try:
            response = await client.beta.messages.create(
                model=self.model,
                max_tokens=self.MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": _user_content(prompt, images)}],
                output_config=output_config,
                betas=[self.FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as e:
            raise LlmError("API key rejected (check ANTHROPIC_API_KEY)") from e
        except anthropic.PermissionDeniedError as e:
            raise LlmError(f"Not allowed with this API key: {e.message}") from e
        except anthropic.NotFoundError as e:
            raise LlmError(f"Model {self.model!r} not found (check COGROUND_LLM_MODEL)") from e
        except anthropic.RateLimitError as e:
            raise LlmError("API rate limit reached (wait a while and retry)") from e
        except anthropic.BadRequestError as e:
            raise LlmError(f"The API rejected the request: {e.message}") from e
        except anthropic.APIStatusError as e:
            raise LlmError(f"The API returned an error ({e.status_code}): {e.message}") from e
        except anthropic.APITimeoutError as e:
            raise LlmError(f"The LLM didn't answer within {self.timeout:.0f} s") from e
        except anthropic.APIConnectionError as e:
            raise LlmError("Can't connect to the API (check the network)") from e

        record["model"] = response.model
        record["request_id"] = getattr(response, "_request_id", None)
        record["usage"] = response.usage.model_dump(mode="json", exclude_none=True)
        record["stop_reason"] = response.stop_reason
        if response.stop_reason == "refusal":
            details = response.stop_details
            reason = f"{details.category}: {details.explanation}" if details is not None else "no reason"
            raise LlmError(f"The LLM refused to answer ({reason})")
        if response.stop_reason == "max_tokens":
            raise LlmError(f"The LLM's answer was cut off at {self.MAX_TOKENS} tokens")
        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise LlmError("The LLM's answer has no text")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise LlmError("The LLM's answer is not JSON") from e


class AgentSdkLlm(_RecordedLlm):
    backend = "agent_sdk"

    def __init__(self) -> None:
        super().__init__()
        # CLI がプロジェクトの設定やファイルを読まないように、空のフォルダで動かす
        self._cwd = tempfile.mkdtemp(prefix="coground_llm_")

    async def _call(self, system: str, prompt: str, output: type[BaseModel], record: dict[str, Any],
                    images: Sequence[bytes] | None = None) -> Any:
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKError, ResultMessage, query
        except ImportError as e:
            raise LlmError("claude-agent-sdk is not installed (rebuild the image with make build)") from e

        options = ClaudeAgentOptions(
            system_prompt=system,
            tools=[],  # ツールは使わせない
            setting_sources=[],  # ユーザーやプロジェクトの設定を読まない
            output_format={"type": "json_schema", "schema": output.model_json_schema()},
            model=self.model,
            effort=self.effort,  # type: ignore[arg-type]
            cwd=self._cwd,
        )
        sdk_prompt: Any = prompt
        if images:
            # 画像は文字列の prompt では渡せないので、メッセージ（画像 + 文のブロック）を 1 つ流す
            async def messages():
                yield {"type": "user", "message": {"role": "user", "content": _user_content(prompt, images)},
                       "parent_tool_use_id": None, "session_id": "default"}
            sdk_prompt = messages()
        result: ResultMessage | None = None
        try:
            async with asyncio.timeout(self.timeout):
                async for message in query(prompt=sdk_prompt, options=options):
                    if isinstance(message, ResultMessage):
                        result = message
        except TimeoutError as e:
            raise LlmError(f"The LLM didn't answer within {self.timeout:.0f} s") from e
        except ClaudeSDKError as e:
            raise LlmError(f"Calling the Claude Agent SDK failed: {e}") from e

        if result is None:
            raise LlmError("No result returned from the LLM")
        record["model"] = ", ".join(result.model_usage or {}) or self.model  # CLI が使ったモデルすべて
        record["cost_usd"] = result.total_cost_usd
        record["usage"] = result.usage
        if result.is_error:
            detail = "; ".join(result.errors or []) or result.result or result.subtype
            raise LlmError(f"The LLM returned an error: {detail} (authenticate with CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY)")
        if result.structured_output is not None:
            return result.structured_output
        try:
            return json.loads(result.result or "")
        except json.JSONDecodeError as e:
            raise LlmError("The LLM's answer is not JSON") from e


class FakeLlm:
    """テスト用。name ごとに、返す値（dict / モデル）か、(system, prompt) を受け取る関数を登録する。
    calls に呼び出しの記録が残る（画像を渡した呼び出しは images に枚数）。"""

    def __init__(self, answers: dict[str, Any | Callable[[str, str], Any]] | None = None) -> None:
        self.answers = dict(answers or {})
        self.calls: list[dict[str, Any]] = []

    async def generate(self, *, name: str, system: str, prompt: str, output: type[T],
                       images: Sequence[bytes] | None = None) -> T:
        call: dict[str, Any] = {"name": name, "system": system, "prompt": prompt}
        if images:
            call["images"] = len(images)
        self.calls.append(call)
        if name not in self.answers:
            raise LlmError(f"FakeLlm has no answer for {name!r}")
        answer = self.answers[name]
        if callable(answer):
            answer = answer(system, prompt)
        if isinstance(answer, Exception):
            raise answer
        return output.model_validate(answer)
