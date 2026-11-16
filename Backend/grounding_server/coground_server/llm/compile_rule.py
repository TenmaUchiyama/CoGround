"""自然言語の指示 → Rule（「属性 = 値」の物を、ある領域へ）。

LLM には、いまのシーンにある領域・物体の属性と、カテゴリ表・属性の語彙を見せて、その中から選ばせる。
LLM が返した行き先がシーンに無ければ、ルールにせず unresolved に入れる（サーバー側で確かめる）。
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from .. import taxonomy
from ..models import AttributeValue, Rule, RuleCondition, SceneSnapshot
from .client import LlmClient

SYSTEM = """\
あなたは、片付けロボットへの指示を「ルール」に変換する係です。

ルールは「条件に合う物を、行き先の領域に置く」という形です。
- 条件は「attribute = equals」の 1 つだけです。attribute には、物体の属性のキーのほか、category / group / role も使えます。
- target_region は、与えられた「領域」の id の中から選びます。一覧に無い id を作ってはいけません。
- 条件は、指示が指している物すべてに当てはまり、指していない物には当てはまらない、いちばん素直なものを選びます。
  例: 「食器」は group = dish、「割れ物」は fragile = true、「コップ」は category = cup。
- equals の型を合わせます（真偽値は true / false、文字列は語彙にある値）。
- 1 つの指示に行き先が複数あれば、ルールを分けます（例: 分別ごとに別のごみ箱）。
- text には、そのルールを人が読める短い日本語の文で書きます（例: 割れ物は棚の下段に置く）。
- ルールにできない部分（行き先の領域が一覧に無い、条件を 1 つの「属性 = 値」で書けない、片付けの指示ではない）は、
  ルールを作らず、その理由を unresolved に日本語で書きます。推測で埋めてはいけません。
"""


class CompiledRule(BaseModel):
    text: str = Field(description="人が読む短い文。例: 割れ物は棚の下段に置く")
    attribute: str = Field(description="属性のキー、または category / group / role")
    equals: AttributeValue
    target_region: str = Field(description="行き先の領域の id")


class CompiledRules(BaseModel):
    rules: list[CompiledRule] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list, description="ルールにできなかった部分と、その理由")


def build_prompt(text: str, scene: SceneSnapshot) -> str:
    owners = {o.id: o for o in scene.objects}
    regions = []
    for r in scene.regions:
        entry: dict[str, object] = {"id": r.id, "label": r.label}
        owner = owners.get(r.object_id or "")
        if owner is not None:
            entry["category"] = owner.category
            if owner.attributes:
                entry["attributes"] = {k: a.value for k, a in owner.attributes.items()}
        regions.append(entry)
    items = [
        {"id": o.id, "category": o.category, "group": o.group,
         "attributes": {k: a.value for k, a in o.attributes.items()}, "region_id": o.region_id}
        for o in scene.objects if o.role == "item"
    ]
    categories = {c: {"role": role, "group": group} for c, (role, group) in taxonomy.CATEGORIES.items()}
    return "\n\n".join([
        "# 領域（行き先に使える id）\n" + _json(regions),
        "# いまある物体\n" + _json(items),
        "# カテゴリ表（category -> role, group）\n" + _json(categories),
        "# 属性の語彙\n" + _json(taxonomy.ATTRIBUTES),
        "# 指示\n" + text,
    ])


async def compile_rules(llm: LlmClient, text: str, scene: SceneSnapshot, existing_ids: set[str]) -> tuple[list[Rule], list[str]]:
    """指示を Rule のリストにする。戻り値は (ルール, ルールにできなかった部分)。ID は rule_N で、existing_ids と重ならない。"""
    compiled = await llm.generate(name="compile_rule", system=SYSTEM, prompt=build_prompt(text, scene), output=CompiledRules)

    region_ids = {r.id for r in scene.regions}
    used = set(existing_ids)
    rules: list[Rule] = []
    unresolved = list(compiled.unresolved)
    n = 0
    for c in compiled.rules:
        if c.target_region not in region_ids:
            unresolved.append(f"{c.text}: 行き先の領域 {c.target_region!r} がシーンに無い")
            continue
        while True:
            n += 1
            if f"rule_{n}" not in used:
                break
        used.add(f"rule_{n}")
        rules.append(Rule(id=f"rule_{n}", text=c.text, source="speech", target_region=c.target_region,
                          condition=RuleCondition(attribute=c.attribute, equals=c.equals)))
    return rules, unresolved


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)
