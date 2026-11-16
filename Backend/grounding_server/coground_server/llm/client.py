"""LLM を 1 回呼び、決めた型（Pydantic モデル）で答えを受け取る口。

本物は Claude Agent SDK（claude-agent-sdk。Claude Code の CLI を子プロセスで動かす。CLI は SDK に入っている）。
ツールは使わせず、JSON Schema に合った答えを 1 つ返させるだけ。
別の SDK（anthropic など）に替えるときは、LlmClient を実装したクラスをもう 1 つ作って Services に渡す。

認証（コンテナの環境変数。.env に書く。どちらか 1 つ）:
  CLAUDE_CODE_OAUTH_TOKEN  Claude のサブスクリプション（ホストで `claude setup-token` を実行して作る）
  ANTHROPIC_API_KEY        Anthropic の API キー

設定（環境変数）:
  COGROUND_LLM_MODEL    モデル名（省略すると CLI の既定）
  COGROUND_LLM_EFFORT   low / medium / high / xhigh / max（省略すると CLI の既定）
  COGROUND_LLM_TIMEOUT  1 回の呼び出しを待つ秒数（既定 120）
  COGROUND_LLM_LOG      呼び出しの記録を足していく JSONL ファイル（省略すると書かない）。
                        実験で「どのプロンプトにどう答えたか」を後から確かめるため

1 回呼ぶたびに CLI を起動するので、数秒かかる。何度も続けて呼ぶ処理には向かない。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Callable, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LlmError(Exception):
    """LLM を呼べなかった、または決めた型の答えが返らなかった。"""


class LlmClient(Protocol):
    async def generate(self, *, name: str, system: str, prompt: str, output: type[T]) -> T:
        """system と prompt を渡し、output の型の答えを返す。name は記録用（"compile_rule" など）。"""
        ...


class AgentSdkLlm:
    def __init__(self) -> None:
        self.model = os.environ.get("COGROUND_LLM_MODEL") or None
        self.effort = os.environ.get("COGROUND_LLM_EFFORT") or None
        self.timeout = float(os.environ.get("COGROUND_LLM_TIMEOUT", "120"))
        self.log_path = os.environ.get("COGROUND_LLM_LOG") or None
        # CLI がプロジェクトの設定やファイルを読まないように、空のフォルダで動かす
        self._cwd = tempfile.mkdtemp(prefix="coground_llm_")

    async def generate(self, *, name: str, system: str, prompt: str, output: type[T]) -> T:
        started = time.monotonic()
        record: dict[str, Any] = {
            "at": datetime.now(timezone.utc).isoformat(), "name": name, "system": system, "prompt": prompt,
        }
        try:
            # 型に合わない答えが返ったら、1 回だけやり直す
            for attempt in (1, 2):
                raw = await self._call(system, prompt, output, record)
                try:
                    value = output.model_validate(raw)
                    break
                except ValidationError as e:
                    log.warning("llm %s: 答えが型に合わない（%d 回目）: %s", name, attempt, e)
                    if attempt == 2:
                        raise LlmError(f"LLM の答えが {output.__name__} の型に合わない") from e
            record["output"] = value.model_dump(mode="json")
            return value
        except LlmError as e:
            record["error"] = str(e)
            raise
        finally:
            record["seconds"] = round(time.monotonic() - started, 2)
            log.info("llm %s: %s (%.1fs, model=%s, $%s)", name, "error" if "error" in record else "ok",
                     record["seconds"], record.get("model"), record.get("cost_usd"))
            self._write_log(record)

    async def _call(self, system: str, prompt: str, output: type[BaseModel], record: dict[str, Any]) -> Any:
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKError, ResultMessage, query
        except ImportError as e:
            raise LlmError("claude-agent-sdk が入っていない（make build でイメージを作り直す）") from e

        options = ClaudeAgentOptions(
            system_prompt=system,
            tools=[],  # ツールは使わせない
            setting_sources=[],  # ユーザーやプロジェクトの設定を読まない
            output_format={"type": "json_schema", "schema": output.model_json_schema()},
            model=self.model,
            effort=self.effort,  # type: ignore[arg-type]
            cwd=self._cwd,
        )
        result: ResultMessage | None = None
        try:
            async with asyncio.timeout(self.timeout):
                async for message in query(prompt=prompt, options=options):
                    if isinstance(message, ResultMessage):
                        result = message
        except TimeoutError as e:
            raise LlmError(f"LLM が {self.timeout:.0f} 秒以内に答えなかった") from e
        except ClaudeSDKError as e:
            raise LlmError(f"Claude Agent SDK の呼び出しに失敗した: {e}") from e

        if result is None:
            raise LlmError("LLM から結果が返らなかった")
        record["model"] = ", ".join(result.model_usage or {}) or self.model  # CLI が使ったモデルすべて
        record["cost_usd"] = result.total_cost_usd
        record["usage"] = result.usage
        if result.is_error:
            detail = "; ".join(result.errors or []) or result.result or result.subtype
            raise LlmError(f"LLM がエラーを返した: {detail}（認証は CLAUDE_CODE_OAUTH_TOKEN か ANTHROPIC_API_KEY）")
        if result.structured_output is not None:
            return result.structured_output
        try:
            return json.loads(result.result or "")
        except json.JSONDecodeError as e:
            raise LlmError("LLM の答えが JSON ではない") from e

    def _write_log(self, record: dict[str, Any]) -> None:
        if not self.log_path:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except OSError as e:
            log.warning("LLM の記録を書けない (%s): %s", self.log_path, e)


class FakeLlm:
    """テスト用。name ごとに、返す値（dict / モデル）か、(system, prompt) を受け取る関数を登録する。"""

    def __init__(self, answers: dict[str, Any | Callable[[str, str], Any]] | None = None) -> None:
        self.answers = dict(answers or {})
        self.calls: list[dict[str, str]] = []

    async def generate(self, *, name: str, system: str, prompt: str, output: type[T]) -> T:
        self.calls.append({"name": name, "system": system, "prompt": prompt})
        if name not in self.answers:
            raise LlmError(f"FakeLlm に {name!r} の答えが無い")
        answer = self.answers[name]
        if callable(answer):
            answer = answer(system, prompt)
        if isinstance(answer, Exception):
            raise answer
        return output.model_validate(answer)
