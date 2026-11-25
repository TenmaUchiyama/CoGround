"""自然言語 → ルール。

  compile_norms   住人の言葉 → ルール（NormRule: 原文 + 規範・条件・対象・内容）。norms.compile
                  内容と条件は語彙の登録簿（norms/vocabulary.py）から選ばせる。語彙に無いものは unresolved（未対応）に入れて返す
                  Where to put things is also a rule of this form (obligation + placed_in), so there is only this one entry point.
  interpret_task  依頼の言葉 → 対象の物体。task.request の interpret

LLM には、いまのシーンにある領域・物体の属性と、カテゴリ表・属性の語彙を見せて、その中から選ばせる。
LLM が返した行き先がシーンに無ければ、ルールにせず unresolved に入れる（サーバー側で確かめる）。
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from .. import taxonomy
from ..models import RuleCondition, SceneSnapshot
from .client import LlmClient

def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


# ---------------------------------------------------------------- 自然言語 → 家庭ルール（NormRule）

NORM_HEAD = """\
You convert a resident's words to a household robot into "household rules".

A household rule has four slots besides the resident's own words: the norm, the conditions (scope), the target and the content.
One household rule is the following JSON (if one sentence from the resident contains several things, split it into multiple rules).
{
  "original_text": the part of the resident's words that corresponds to this rule (verbatim, not paraphrased),
  "norm": "obligation" (must do) | "prohibition" (must not do) | "permission" (may do),
  "scope": {
    "from": "HH:MM" or null (time it starts applying), "until": "HH:MM" or null (time it stops applying),
    "requester": "author" ("only when I instructed it") or null,
    "when": a condition (below) or null (applies only in that state)
  },
  "target": {
    "kind": "object" (an object) | "zone" (a zone) | "robot" (the robot itself),
    "id": id of an individual object or zone, or null,
    "where": {"attribute": attribute key or category / group / role, "equals": value} or null,
    "fallback": true only for "everything else" (see below), otherwise false
  },
  "requirement": {"predicate": name of a content below, "args": {...}},
  "attribute": when target.where uses an attribute (not category / group / role), how to recognise it:
     {"name": the same key as target.where.attribute, "how_to_tell": one sentence on how to judge it from a photo,
      "values": the possible answers as strings (e.g. ["true", "false"]),
      "visual": false if it can't be judged from an image (who owns it, its price, memories), otherwise true}, else null,
  "reason": the reason the resident gave, or null (not used for verdicts),
  "exception_of": for a permission, the id of the original prohibition it's an exception to, or null,
  "pending_refs": [{"ref": "zone_ref_1", "kind": "zone", "phrase": "around here in the living room"}]
}

Contents (requirement.predicate). These are the only things a rule can require or forbid:
"""

NORM_CONDITIONS = """\

Conditions (scope.when). One condition is {"predicate": name, "args": {...}}.
  NOT: add "negate": true                       e.g. {"predicate": "region_full", "args": {"region": "box_white"}, "negate": true}
  AND: {"all": [condition, condition, ...]}     ("negate": true on it negates the whole AND)
"""

NORM_RULES = """\

Rules:
- Never invent an id that isn't in the given lists.
- For zones whose extent can't be determined from words alone, such as "around here" or "here", set target.id to a placeholder name like "zone_ref_1",
  and put that name and the part of the resident's words that refers to the area in pending_refs. Never guess by picking from the listed zones.
- Times use 24-hour HH:MM ("6 in the evening" is 18:00). If the expiry time (until) isn't stated, leave it null.
  Never fill it in by guessing.
- Choose the most natural condition, e.g. "fragile items" is fragile = true, "plates" is category = plate, "dishes" is group = dish.
  If the current objects have attributes, prefer attributes over the category table's group
  (e.g. for "trash", if objects have a trash attribute use trash = true; group = trash may include things that shouldn't be thrown away).
- Attribute names: if the "Attribute vocabulary" already has a key with the same meaning ("breakable" and "fragile"), reuse that key.
  Only make a new key (short lowercase snake_case) when nothing there fits.
- If one sentence has multiple destinations, split it into separate placed_in obligations (e.g. a different trash bin per sorting category).
- "Put X in A; if A is full, put it in B" is two placed_in obligations with the same target: one to A with scope.when = region_full(A) negated,
  one to B with scope.when = region_full(A).
- When the words refer to everything not covered by other rules, such as "everything else", "the rest" or "other things",
  make a placed_in obligation with target.where = null and target.fallback = true (an "otherwise" rule).
  It's used only for objects that matched no other placed_in obligation.
- A permission ("you may touch it when I ask") points to a prohibition in the "current rules" list via exception_of, and its requirement is the same as the original prohibition's.
- For parts that can't be made into rules (destinations not in the lists, something that none of the contents and conditions above can express
  such as "quietly" or "carefully", an order or a count, words that aren't rules), don't create a rule and don't pick the nearest content instead;
  write the part and the reason in English in unresolved.
"""


def norm_system() -> str:
    """ルール登録のプロンプト。内容と条件の一覧は、語彙の登録簿（norms/vocabulary.py）から作る。"""
    from ..norms import vocabulary

    return NORM_HEAD + vocabulary.describe("content") + "\n" + NORM_CONDITIONS + vocabulary.describe("condition") + "\n" + NORM_RULES

NORM_SYSTEM = norm_system()


class CompiledTarget(BaseModel):
    kind: str = "object"
    id: str | None = None
    where: RuleCondition | None = None
    fallback: bool = False


class CompiledScope(BaseModel):
    model_config = {"populate_by_name": True}

    from_: str | None = Field(default=None, alias="from")
    until: str | None = None
    requester: str | None = None
    when: dict | None = None  # type: ignore[type-arg]


class CompiledRequirement(BaseModel):
    window: str | None = None  # 省略すると、内容が決めている時点になる
    predicate: str
    args: dict = Field(default_factory=dict)  # type: ignore[type-arg]
    transition: dict | None = None  # type: ignore[type-arg]


class CompiledAttribute(BaseModel):
    name: str
    how_to_tell: str = ""
    values: list[str] = Field(default_factory=list)
    visual: bool = True


class CompiledRef(BaseModel):
    ref: str
    kind: str = "zone"
    phrase: str = ""


class CompiledNorm(BaseModel):
    original_text: str
    norm: str
    scope: CompiledScope = Field(default_factory=CompiledScope)
    target: CompiledTarget = Field(default_factory=CompiledTarget)
    requirement: CompiledRequirement
    attribute: CompiledAttribute | None = None
    reason: str | None = None
    exception_of: str | None = None
    pending_refs: list[CompiledRef] = Field(default_factory=list)


class CompiledNorms(BaseModel):
    rules: list[CompiledNorm] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list, description="ルールにできなかった部分と、その理由")


def build_norm_prompt(text: str, scene: SceneSnapshot, zones: list[dict[str, str]], existing: list[dict[str, str]],
                      attributes: dict[str, str] | None = None) -> str:
    """attributes: いまのルールが使っている属性（名前 -> 見分け方）。同じ意味の属性に、同じ名前を使わせる。"""
    regions = [{"id": r.id, "label": r.label} for r in scene.regions]
    items = [
        {"id": o.id, "category": o.category, "group": o.group,
         "attributes": {k: a.value for k, a in o.attributes.items()}, "region_id": o.region_id}
        for o in scene.objects if o.role == "item"
    ]
    categories = {c: {"role": role, "group": group} for c, (role, group) in taxonomy.CATEGORIES.items()}
    return "\n\n".join([
        "# Zones (usable as placed_in destinations and zone ids)\n" + _json(regions),
        "# Zones defined by the resident (usable as zone ids)\n" + _json(zones),
        "# Current objects\n" + _json(items),
        "# Current rules (usable for exception_of)\n" + _json(existing),
        "# Category table (category -> role, group)\n" + _json(categories),
        "# Attribute vocabulary\n" + _json({**taxonomy.ATTRIBUTES, **(attributes or {})}),
        "# Resident's words\n" + text,
    ])


async def compile_norms(
    llm: LlmClient, text: str, scene: SceneSnapshot, *, zone_ids: dict[str, str], existing, author: str | None,
    new_id,
):  # type: ignore[no-untyped-def]
    """住人の言葉を家庭ルールにする。戻り値は (確定したルール, 登録の途中のルール, ルールにできなかった部分)。

    zone_ids: 領域 ID -> 呼び名（シーンの領域と、住人が決めた領域）。existing: いまのルール（NormRule）。
    new_id(): 新しいルールの ID を返す関数。
    範囲が言葉だけでは決まらない（pending_refs）、解除時刻が言われていない（scope.until）ルールは、
    勝手に補わず「登録の途中」にする（rules.confirm で確定する）。
    """
    from pydantic import ValidationError

    from ..norms import vocabulary
    from ..norms.attributes import STRUCTURAL, attribute_defs
    from ..norms.model import NormRule, PendingRef, PendingRule

    known_attributes = {a.name: a.how_to_tell for a in attribute_defs(list(existing))}
    prompt = build_norm_prompt(text, scene, [{"id": i, "label": label} for i, label in zone_ids.items()],
                               [{"id": n.id, "norm": n.norm, "text": n.original_text} for n in existing], known_attributes)
    compiled = await llm.generate(name="compile_norm", system=norm_system(), prompt=prompt, output=CompiledNorms)

    region_ids = {r.id for r in scene.regions}
    object_ids = {o.id for o in scene.objects}
    prohibitions = {n.id for n in existing if n.norm == "prohibition"}
    rules: list[NormRule] = []
    pending: list[PendingRule] = []
    unresolved = list(compiled.unresolved)
    taken: set[str] = set()

    def fresh() -> str:
        rid = new_id(taken)
        taken.add(rid)
        return rid

    for c in compiled.rules:
        label = c.original_text or text
        refs = {r.ref: r for r in c.pending_refs}
        scope = c.scope.model_dump(by_alias=True)
        notes: list[str] = []
        open_items: list[str] = []
        if scope.get("requester") in ("author", "me", "I"):
            if author is None:
                unresolved.append(f"{label}: unknown who \"I\" is (pass author)")
                continue
            scope["requester"] = author
        try:
            rule = NormRule.model_validate({
                "id": fresh(), "author": author, "original_text": c.original_text, "norm": c.norm, "scope": scope,
                "target": c.target.model_dump(), "requirement": c.requirement.model_dump(), "reason": c.reason,
                "exception_of": c.exception_of,
                "attributes": [c.attribute.model_dump()] if (
                    c.attribute is not None and c.target.where is not None and c.attribute.name == c.target.where.attribute
                    and c.attribute.name not in STRUCTURAL) else [],
            })
        except ValidationError as e:
            unresolved.append(f"{label}: can't be put into rule form ({e.errors()[0].get('msg', '')})")
            continue
        # 語彙に無い内容・条件は、近いもので代用せず「未対応」として返す
        problems = [vocabulary.check("content", rule.requirement.predicate, rule.requirement.args, rule.target.kind)]
        leaves = rule.scope.when.leaves() if rule.scope.when is not None else []
        problems += [vocabulary.check("condition", leaf.predicate or "", leaf.args) for leaf in leaves]
        for leaf in leaves:
            if leaf.predicate == "region_full" and leaf.args.get("region") not in region_ids:
                problems.append(f"zone {leaf.args.get('region')!r} (region_full) is not in the scene")
            if leaf.predicate == "base_in_zone" and leaf.args.get("zone") not in {*region_ids, *zone_ids}:
                problems.append(f"zone {leaf.args.get('zone')!r} (base_in_zone) is not known")
        problems = [x for x in problems if x]
        if problems:
            unresolved.append(f"{label}: {'; '.join(problems)}")
            continue
        if rule.requirement.predicate == "placed_in" and rule.requirement.args.get("region") not in region_ids:
            unresolved.append(f"{label}: destination zone {rule.requirement.args.get('region')!r} is not in the scene")
            continue
        if rule.target.fallback and (rule.destination is None or rule.target.kind != "object"
                                     or rule.target.id is not None or rule.target.where is not None):
            unresolved.append(f"{label}: an \"otherwise\" rule must be a placed_in obligation with no condition")
            continue
        if rule.exception_of is not None and rule.exception_of not in prohibitions:
            unresolved.append(f"{label}: no original prohibition {rule.exception_of!r} to make an exception to")
            continue
        if rule.target.kind == "object" and rule.target.id is not None and rule.target.id not in object_ids:
            unresolved.append(f"{label}: object {rule.target.id!r} is not in the scene")
            continue
        refs_needed: list[PendingRef] = []
        if rule.target.kind == "zone":
            if rule.target.id in refs or rule.target.id is None or rule.target.id not in zone_ids:
                # 範囲が言葉だけでは決まらない（LLM が一覧に無い id を作ったときも、決まっていないものとして扱う）
                ref = refs.get(rule.target.id or "") or CompiledRef(ref=rule.target.id or "zone_ref_1")
                if rule.target.id is None:
                    rule = rule.model_copy(update={"target": rule.target.model_copy(update={"id": ref.ref})})
                refs_needed.append(PendingRef(ref=ref.ref, kind="zone", phrase=ref.phrase))
                notes.append(f"Define the region of \"{ref.phrase or label}\" (zones.define)")
        if rule.scope.from_ is not None and rule.scope.until is None:
            open_items.append("scope.until")
            notes.append(f"Confirm until when it applies from {rule.scope.from_} (expiry time)")
        if refs_needed or open_items:
            pending.append(PendingRule(rule=rule, pending_refs=refs_needed, unresolved=open_items, notes=notes))
        else:
            rules.append(rule)
    return rules, pending, unresolved


# ---------------------------------------------------------------- 依頼の解釈

TASK_SYSTEM = """\
You decide "which objects to tidy" from the words of a request to a tidying robot.

- From the ids of the given "current objects", choose every object the request refers to and put them in object_ids.
  Never invent an id that isn't in the list.
- When it refers to everything in some place, like "everything on the desk", also put that place's zone id in source_region.
- Deciding whether to tidy something is the rules' job. Include fragile or dirty items too if the request refers to them.
- When the request says where to put things ("put everything in box 1", "the cups go on the shelf"), add one entry to destinations
  per destination: region is the zone id from "Zones", where is the condition for which of the chosen objects go there
  (null = all of them; otherwise {"attribute", "equals"} with category / group / an attribute key, e.g. category = cup),
  and text is the part of the request that says it, in its original words.
  These apply only during this request and take priority over the household rules' storage locations.
  If the request doesn't say where to put things, leave destinations empty (the rules decide).
  If the destination isn't in "Zones", don't pick the nearest one; write it in unresolved.
- For parts where you can't decide which objects are meant, don't guess; write the reason in English in unresolved.
"""


class TaskDestination(BaseModel):
    """依頼の言葉が言った置き先（この依頼の間だけ。常設のルールより先に立つ）。"""

    region: str = Field(min_length=1, description="置き先の領域 ID")
    where: RuleCondition | None = Field(default=None, description="対象のうち、どれをそこへ置くか（null なら全部）")
    text: str = Field(default="", description="依頼の言葉のうち、置き先を言った部分")


class InterpretedTask(BaseModel):
    object_ids: list[str] = Field(default_factory=list)
    source_region: str | None = None
    destinations: list[TaskDestination] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)


async def interpret_task(llm: LlmClient, text: str, scene: SceneSnapshot) -> InterpretedTask:
    """依頼の言葉から、対象の物体を決める。シーンに無い物体・運ぶ物でない物体は落として unresolved に入れる。"""
    regions = [{"id": r.id, "label": r.label} for r in scene.regions]
    items = [{"id": o.id, "category": o.category, "group": o.group, "region_id": o.region_id,
              "attributes": {k: a.value for k, a in o.attributes.items()}}
             for o in scene.objects if o.role == "item"]
    prompt = "\n\n".join(["# Zones\n" + _json(regions), "# Current objects\n" + _json(items), "# Request\n" + text])
    answer = await llm.generate(name="interpret_task", system=TASK_SYSTEM, prompt=prompt, output=InterpretedTask)
    known = {o["id"] for o in items}
    unknown = [i for i in answer.object_ids if i not in known]
    object_ids = list(dict.fromkeys(i for i in answer.object_ids if i in known))
    unresolved = [*answer.unresolved, *(f"Object {i!r} is not in the scene (not a carryable object)" for i in unknown)]
    region_ids = {r["id"] for r in regions}
    source = answer.source_region if answer.source_region in region_ids else None
    destinations = []
    for dest in answer.destinations:
        if dest.region in region_ids:
            destinations.append(dest)
        else:
            unresolved.append(f"Destination {dest.region!r} is not in the scene")
    return InterpretedTask(object_ids=object_ids, source_region=source, destinations=destinations, unresolved=unresolved)
