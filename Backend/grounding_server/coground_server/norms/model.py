"""家庭ルールの型（Documents/CoGround_Home_Rules.md の §3・§4・§6）。

ルール 1 つの意味は R = (N, S, T, C)、C = (W, φ):
  N  norm         義務 / 禁止 / 許可
  S  scope        どの状況で効くか（時刻、依頼者）
  T  target       どの物体・領域に関係するか
  W  window       計画や実行のどこを調べるか（内容ごとに決まっている。vocabulary.py）
  φ  predicate    どの状態・変化を要求または禁止するか（内容。vocabulary.py の CONTENTS）

住人から見た枠は 原文 + 規範・条件・対象・内容 の 4 つ。W と状態の変化（transition）は内容の性質として
vocabulary.py が持つ（「領域に入る」と「領域の中にいる」は別の内容）。

判定に使う値は 3 値（True / False / None = 不明）。不明は「観測が足りない」を表し、False とは区別する。
時刻は家の時計（clock.py の HomeClock）の datetime。
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..models import (
    AttributeValue, Basis, MissingFact, Rule, RuleCondition, RuleSource, SceneObject, Verdict, VerdictValue,
)

Tri = bool | None
"""True / False / None（不明）"""

Norm = Literal["obligation", "prohibition", "permission"]

Window = Literal["whole", "at_contact", "during_base_motion", "at_place_complete"]
"""whole: 状態列の全体 / at_contact: 物体に触れる時点 / during_base_motion: 台車が動く区間 /
at_place_complete: 配置が終わった時点"""

Phase = Literal["contact", "base_motion", "place_complete", "other"]
"""状態（WorldSample）がどの区間のものか。window がここから評価する時点を選ぶ。"""

WINDOW_PHASES: dict[str, tuple[str, ...]] = {
    "whole": ("contact", "base_motion", "place_complete", "other"),
    "at_contact": ("contact",),
    "during_base_motion": ("base_motion",),
    "at_place_complete": ("place_complete",),
}


def and3(*values: Tri) -> Tri:
    """3 値の AND（Kleene）。False が 1 つでもあれば False、そうでなく不明があれば不明。"""
    if any(v is False for v in values):
        return False
    return None if any(v is None for v in values) else True


def or3(*values: Tri) -> Tri:
    """3 値の OR（Kleene）。True が 1 つでもあれば True、そうでなく不明があれば不明。"""
    if any(v is True for v in values):
        return True
    return None if any(v is None for v in values) else False


def not3(value: Tri) -> Tri:
    return None if value is None else not value


def _parse_hhmm(text: str) -> time:
    try:
        h, m = text.split(":")
        return time(int(h), int(m))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Write times as HH:MM: {text!r}") from e


class Condition(BaseModel):
    """状態についての条件。Scope.when に書く。

    predicate + args  条件 1 つ（vocabulary.py の CONDITIONS の名前）。例: 子供が 5 m 以内 = near_child, {"distance": 5.0}
    all               AND（すべての条件が成り立つ）
    negate = true     NOT（上の結果を反転する。「満杯でないとき」）
    predicate と all は、どちらか一方だけを書く。
    """

    predicate: str | None = Field(default=None, min_length=1)
    args: dict[str, Any] = Field(default_factory=dict)
    all: list[Condition] = Field(default_factory=list, description="AND でつなぐ条件")
    negate: bool = Field(default=False, description="NOT")

    @model_validator(mode="after")
    def _check_shape(self) -> Condition:
        if (self.predicate is None) == (not self.all):
            raise ValueError("A condition needs either a predicate or a non-empty all list (not both)")
        return self

    def leaves(self) -> list[Condition]:
        """述語を持つ条件（AND の中身を平らにしたもの）。"""
        if self.predicate is not None:
            return [self]
        return [leaf for c in self.all for leaf in c.leaves()]


class Scope(BaseModel):
    """S: どの状況で効くか。何も書かなければ常に効く。

    from / until は家の時計の時刻（HH:MM）。from だけなら「その時刻以降（その日のうち）」。
    解除時刻が未指定のときに勝手に補わない（日をまたぐ運用は、登録時に until を確認する）。
    from > until なら日をまたぐ（22:00 から 6:00 など）。
    requester は依頼者の人物 ID（「私が指示したときだけ」）。依頼者が分からなければ不明になる。
    when は、そのときの状態についての条件（「子供が 5 m 以内にいるとき」）。述語で書き、evaluate.py が状態から判定する
    （active() は時刻と依頼者だけを見る）。
    """

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    clock: Literal["home_local"] = "home_local"
    from_: str | None = Field(default=None, alias="from", description="効き始める時刻（HH:MM）")
    until: str | None = Field(default=None, description="効かなくなる時刻（HH:MM）。null なら未指定")
    requester: str | None = Field(default=None, description="この人物が依頼したときだけ効く")
    when: Condition | None = Field(default=None, description="この状態のときだけ効く（述語）")

    @model_validator(mode="after")
    def _check_times(self) -> Scope:
        for value in (self.from_, self.until):
            if value is not None:
                _parse_hhmm(value)
        return self

    @property
    def uses_clock(self) -> bool:
        return self.from_ is not None or self.until is not None

    def active(self, t: datetime | None, requester: str | None = None) -> Tri:
        return and3(self._time_active(t), self._requester_active(requester))

    def _time_active(self, t: datetime | None) -> Tri:
        if not self.uses_clock:
            return True
        if t is None:
            return None
        now = t.time()
        start = _parse_hhmm(self.from_) if self.from_ is not None else None
        end = _parse_hhmm(self.until) if self.until is not None else None
        if start is not None and end is not None:
            return start <= now < end if start <= end else (now >= start or now < end)
        if start is not None:
            return now >= start
        assert end is not None
        return now < end

    def _requester_active(self, requester: str | None) -> Tri:
        if self.requester is None:
            return True
        return None if requester is None else requester == self.requester


class Target(BaseModel):
    """T: どの物体・領域に関係するか。

    kind = object  物体。id（個体）か where（属性 = 値）で選ぶ。どちらも無ければ、すべての物体
    kind = zone    領域（id で指定）。台車の進入禁止など、物体を選ばないルール
    kind = robot   ロボット自身（近接時の停止など）

    where の属性に値が無い物体は「不明」になる（割れ物かどうか分からない皿）。
    unknown_as = "false" にすると、値が無ければ合わないとみなす（旧 Rule の動作）。
    fallback = True は「それ以外」（ほかの義務のどれにも合わなかった物体にだけ使う。旧 Rule の condition = null）。
    """

    kind: Literal["object", "zone", "robot"] = "object"
    id: str | None = None
    where: RuleCondition | None = None
    unknown_as: Literal["unknown", "false"] = "unknown"
    fallback: bool = False

    def matches(self, obj: SceneObject | None) -> Tri:
        """物体 obj がこの対象条件に合うか。kind が object 以外は、物体によらず True。"""
        if self.kind != "object":
            return True
        if obj is None:
            return None
        if self.id is not None and obj.id != self.id:
            return False
        if self.where is None:
            return True
        value = obj.value(self.where.attribute)
        if value is None:
            return None if self.unknown_as == "unknown" else False
        return value == self.where.equals


class Transition(BaseModel):
    """述語の変化（イベント）。from = false, to = true なら立ち上がり（領域の外から内へ）。"""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    from_: bool = Field(alias="from")
    to: bool


class Requirement(BaseModel):
    """C = (W, φ): どこを調べ、何を要求または禁止するか。predicate は predicates.py の名前。"""

    window: Window = Field(default="whole", description="省略すると、内容（vocabulary.py）が決めている時点になる")
    predicate: str = Field(min_length=1)
    args: dict[str, Any] = Field(default_factory=dict, description='述語の引数。例: {"region": "shelf_upper"}')
    transition: Transition | None = Field(default=None, description="状態ではなく変化を見るとき")

    @model_validator(mode="before")
    @classmethod
    def _default_window(cls, data: Any) -> Any:
        # W は内容の性質。書かれていなければ、内容の登録（vocabulary.py）から決める
        if isinstance(data, dict) and data.get("window") is None:
            from .vocabulary import default_window
            data = {**data, "window": default_window(data.get("predicate"))}
        return data


class AttributeDef(BaseModel):
    """ルールの対象条件が使う属性の定義。ルールを登録するときに作り、ルールと一緒に持つ（attributes.py が集める）。

    VLM への質問はこの定義から作る（「割れ物」というルールが無ければ、割れ物かどうかは聞かない）。
    """

    name: str = Field(min_length=1, description="属性のキー（fragile など）。同じ意味なら、前からある名前を使う")
    how_to_tell: str = Field(default="", description="見分け方（VLM に見せる 1 文）")
    values: list[str] = Field(default_factory=list, description='答えの選択肢。例: ["true", "false"]')
    visual: bool = Field(default=True, description="画像から判断できるか。できない属性（持ち主など）は VLM に聞かず、住人が登録する")
    rule_ids: list[str] = Field(default_factory=list, description="この属性を使っているルール（集めたときに入る）")


class NormRule(BaseModel):
    id: str = Field(min_length=1)
    author: str | None = Field(default=None, description="登録者の人物 ID（「私」の参照先）")
    original_text: str = Field(description="住人の言葉そのまま。説明で見せる")
    norm: Norm
    scope: Scope = Field(default_factory=Scope)
    target: Target = Field(default_factory=Target)
    requirement: Requirement
    reason: str | None = Field(default=None, description="説明用の理由（判定には使わない）")
    exception_of: str | None = Field(default=None, description="許可のとき: 例外にする元の禁止の ID")
    origin: Literal["norm", "tidy"] = Field(
        default="norm",
        description="どの口で登録したか。norm: norms.set など / tidy: 片付けルール（rules.set。属性 = 値 → 行き先）。"
        "どちらも同じ家庭ルールとして判定する。rules.set は tidy だけを、norms.set は norm だけを置き換える")
    source: RuleSource = Field(default="script", description="speech / demo / script")
    attributes: list[AttributeDef] = Field(
        default_factory=list, description="対象の条件に使う属性の定義（見分け方など）。登録のときに入れる")

    @model_validator(mode="after")
    def _check_exception(self) -> NormRule:
        if self.exception_of is not None and self.norm != "permission":
            raise ValueError(f"{self.id}: exception_of can only be set on a permission")
        return self

    @classmethod
    def from_legacy(cls, rule: Rule) -> NormRule:
        """片付けルール（条件に合う物を領域に置く）を、配置完了時の義務にする。"""
        return cls(
            id=rule.id,
            original_text=rule.text,
            norm="obligation",
            target=Target(kind="object", where=rule.condition, unknown_as="false", fallback=rule.is_fallback),
            requirement=Requirement(window="at_place_complete", predicate="placed_in",
                                    args={"region": rule.target_region}),
            origin="tidy",
            source=rule.source,
        )

    def to_legacy(self) -> Rule | None:
        """片付けルールの形（属性 = 値 → 行き先）に戻す。その形で書けなければ None（Scope を訂正した、など）。"""
        region = self.destination
        t = self.target
        if (region is None or self.requirement.window != "at_place_complete" or self.requirement.transition is not None
                or t.kind != "object" or t.id is not None or t.unknown_as != "false" or self.scope != Scope()
                or (t.where is None) != t.fallback):
            return None
        return Rule(id=self.id, text=self.original_text, condition=t.where, target_region=region, source=self.source)

    @property
    def destination(self) -> str | None:
        """収納先を決める義務なら、その領域の ID。"""
        if self.norm == "obligation" and self.requirement.predicate == "placed_in":
            region = self.requirement.args.get("region")
            return region if isinstance(region, str) else None
        return None


class PendingRef(BaseModel):
    """言葉だけでは決まらない参照（「このあたり」）。Quest などで範囲が届くまで、ルールは確定しない。"""

    ref: str = Field(min_length=1, description="ルールの中で使っている仮の ID。例: zone_ref_1")
    kind: Literal["zone"] = "zone"
    phrase: str = Field(default="", description="住人の言葉のうち、この参照にあたる部分。例: リビングのこのあたり")


class PendingRule(BaseModel):
    """登録の途中のルール。判定には使わない。rules.confirm で、参照と未解決の項目を埋めて確定する。

    unresolved の項目:
      scope.until  解除時刻が言われていない（「18 時以降」）。勝手に補わず、確かめる
    """

    rule: NormRule
    pending_refs: list[PendingRef] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list, description="確かめる内容（人が読む）")


# ---------------------------------------------------------------- 判定

__all__ = [
    "AttributeDef", "AttributeValue", "Basis", "Condition", "MissingFact", "Norm", "NormRule", "PendingRef", "PendingRule", "Phase", "Requirement", "Scope", "Target",
    "Transition", "Tri", "Verdict", "VerdictValue", "WINDOW_PHASES", "Window", "and3", "not3", "or3",
]
