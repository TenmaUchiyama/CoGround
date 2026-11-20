"""家庭ルール（Documents/CoGround_Home_Rules.md）: ルールの型、判定、依頼の記録。

  model.py       NormRule = 原文 + 規範・条件（Scope）・対象・内容 と Verdict（判定）
  vocabulary.py  語彙の登録簿: ルールに書ける内容と条件を 1 件ずつ（読む状態、判定、調べる時点、応答、説明）
  predicates.py  述語の関数（ある時点の状態 -> True / False / 不明）
  attributes.py  ルールが使っている属性の定義を集める（VLM への質問のもと）
  evaluate.py    ルールを状態列に当てて判定する（計画の予測と実行の観測で同じ関数）
  depends.py     ルールが読む項目（訂正したとき、どのルールに関係するかを示す）
  clock.py       家の時計（差し替えられる）
  task.py        依頼の記録（Plan とは別に持つ）、訂正の記録、経路による保留
  planner.py     依頼の行から Plan の step を作る
  geometry.py    床の上の幾何（領域への重なり、領域を避ける折れ線）
  monitors.py    台車の動きに対する判定（R2: 領域への進入の禁止、R4: 子供が近くにいる間は止める）と、実行中に見張る条件
  report.py      依頼の結果を住人に伝える形にする

実行中の監視（hold と再計画）そのものは、coground_server/monitor.py。
"""

from .attributes import attribute_defs, questions
from .clock import HomeClock
from .depends import affected_by, candidates, depends_on
from .evaluate import contact_trace, evaluate, placement_trace
from .model import AttributeDef, Condition, MissingFact, NormRule, Requirement, Scope, Target, Transition, Verdict
from .predicates import WorldSample
from .task import TaskRecord, TaskRow

__all__ = [
    "AttributeDef", "Condition", "attribute_defs", "questions",
    "HomeClock", "MissingFact", "NormRule", "Requirement", "Scope", "Target", "TaskRecord", "TaskRow",
    "Transition", "Verdict", "WorldSample", "affected_by", "candidates", "contact_trace", "depends_on",
    "evaluate", "placement_trace",
]
