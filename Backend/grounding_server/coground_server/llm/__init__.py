"""LLM の呼び出し。ほかのコードは、ここの関数（入力 → Pydantic モデル）だけを使う。

  client.py        LLM を 1 回呼ぶ口（LlmClient）。本物は Claude Agent SDK、テストでは FakeLlm
  compile_rule.py  自然言語 → Rule

ルールの照合と計画（planner.py）は LLM を使わない。
"""

from .client import AgentSdkLlm, FakeLlm, LlmClient, LlmError

__all__ = ["AgentSdkLlm", "FakeLlm", "LlmClient", "LlmError"]
