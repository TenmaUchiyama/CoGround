"""属性の定義を、ルールバンクから集める（設計ガイド §3）。

VLM は、聞かれた属性しか答えない。何を聞くかは、いまあるルールの対象条件が使っている属性で決まる:

    ルール「割れ物には触らない」（target.where = fragile）
      -> 属性の定義 fragile（見分け方: 落とすと割れる素材か / 答え: true・false / 画像で判断できる）
      -> VLM への質問に fragile が入る

ルールを消せば、その属性は聞かなくなる。画像から判断できない属性（visual = false。「パパの物」など）は
VLM に聞かず、住人が登録する（task.correct）。
"""

from __future__ import annotations

from .. import taxonomy
from .model import AttributeDef, NormRule

# 物体の種類そのもの（属性ではない）。VLM は category を必ず答えるので、質問にはしない
STRUCTURAL = ("category", "group", "role")


def _text(value: object) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


def attribute_defs(rules: list[NormRule]) -> list[AttributeDef]:
    """いまのルールが使っている属性の定義（名前ごとに 1 つ。使っているルールの ID を付ける）。"""
    out: dict[str, AttributeDef] = {}
    for rule in rules:
        where = rule.target.where
        if rule.target.kind != "object" or where is None or where.attribute in STRUCTURAL:
            continue
        name = where.attribute
        declared = next((a for a in rule.attributes if a.name == name), None)
        current = out.get(name)
        if current is None:
            current = out[name] = AttributeDef(name=name, how_to_tell=taxonomy.ATTRIBUTES.get(name, ""))
        if declared is not None:
            current.how_to_tell = declared.how_to_tell or current.how_to_tell
            current.visual = current.visual and declared.visual
            for v in declared.values:
                if v not in current.values:
                    current.values.append(v)
        if isinstance(where.equals, bool):
            wanted = ["true", "false"]
        else:
            wanted = [_text(where.equals)]
        for v in wanted:
            if v not in current.values:
                current.values.append(v)
        current.rule_ids.append(rule.id)
    return list(out.values())


def questions(rules: list[NormRule]) -> list[AttributeDef]:
    """VLM に聞く属性（画像から判断できるものだけ）。"""
    return [a for a in attribute_defs(rules) if a.visual]
