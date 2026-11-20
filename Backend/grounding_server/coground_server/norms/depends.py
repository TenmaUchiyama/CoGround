"""スキルが変えうる項目 Changes(a) と、ルールが読む項目 DependsOn(R)（設計ガイド §5）。

    Candidates(a) = { R | Changes(a) ∩ DependsOn(R) ≠ ∅ }

項目のキー:
  attr:<名前>     物体の属性（attr:fragile など。category / group / role も同じ形）
  contact         ロボットが触れている物体
  holding         持っている物体
  object_region   物体がある領域
  base_pose       台車の位置
  base_speed      台車の速度
  zone_shape      領域の形
  person_pose     人の位置
  region_capacity 領域に置く空きがあるか
  clock           家の時計
  requester       依頼者

取りこぼしを確かめるために、全件評価（すべてのルールを評価する）と結果を比べられるようにしておく。
"""

from __future__ import annotations

from .model import NormRule
from .vocabulary import READS

SKILL_CHANGES: dict[str, frozenset[str]] = {
    "navigate": frozenset({"base_pose", "base_speed"}),
    "pick": frozenset({"contact", "holding"}),
    "place": frozenset({"contact", "holding", "object_region"}),
}

# 述語が読む項目は、語彙の登録簿（vocabulary.py）が持つ
PREDICATE_DEPENDS: dict[str, frozenset[str]] = READS


def attribute_key(name: str) -> str:
    return f"attr:{name}"


def depends_on(rule: NormRule) -> frozenset[str]:
    """ルールの判定が読む項目。"""
    keys = set(PREDICATE_DEPENDS.get(rule.requirement.predicate, frozenset()))
    if rule.target.where is not None:
        keys.add(attribute_key(rule.target.where.attribute))
    if rule.scope.when is not None:
        for leaf in rule.scope.when.leaves():
            keys |= PREDICATE_DEPENDS.get(leaf.predicate or "", frozenset())
    if rule.scope.uses_clock:
        keys.add("clock")
    if rule.scope.requester is not None:
        keys.add("requester")
    return frozenset(keys)


def candidates(skill: str, rules: list[NormRule]) -> list[NormRule]:
    """そのスキルを実行すると判定が変わりうるルール。

    計画・監視はこれでルールを絞らない（すべてのルールを、内容が決めている時点で評価する）。
    全件評価との比較のために残してある。"""
    changes = SKILL_CHANGES.get(skill, frozenset())
    return [r for r in rules if changes & depends_on(r)]


def affected_by(key: str, rules: list[NormRule]) -> list[NormRule]:
    """その項目（訂正した属性など）を読むルール。例外（許可）が読むなら、元の禁止も含める。"""
    direct = {r.id for r in rules if key in depends_on(r)}
    via_exception = {r.exception_of for r in rules if r.id in direct and r.exception_of is not None}
    return [r for r in rules if r.id in direct | via_exception]
