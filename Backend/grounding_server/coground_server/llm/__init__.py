"""LLM の呼び出し。ほかのコードは、ここの関数（入力 → Pydantic モデル）だけを使う。

  client.py        LLM を 1 回呼ぶ口（LlmClient）。本物は API キーで Messages API（AnthropicApiLlm）か
                   Claude Agent SDK（AgentSdkLlm）。make_llm が環境変数で選ぶ。テストでは FakeLlm
  compile_rule.py  自然言語 → Rule / 家庭ルール（NormRule）、依頼の言葉 → 対象の物体

ルールの照合と計画（planner.py）は LLM を使わない。
"""

from .client import AgentSdkLlm, AnthropicApiLlm, FakeLlm, LlmClient, LlmError, make_llm

__all__ = ["AgentSdkLlm", "AnthropicApiLlm", "FakeLlm", "LlmClient", "LlmError", "make_llm"]
