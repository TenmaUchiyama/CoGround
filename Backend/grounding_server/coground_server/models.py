"""サーバーが扱うデータの型（Scene / Rule / 入力 / Plan / Correction / Scenario / TrialLog）。

中心は Plan。可視化（Before / After のトグル、シーケンスバー + Ghost Robot）は同じ Plan を別の形で描く。

約束事:
- 座標はすべて Unity のワールド座標（メートル、左手系、Y 上）。ベクトルは [x, y, z]、回転は [x, y, z, w]。
  ROS（world フレーム、右手系、Z 上）への変換は ROS に渡す側で行う（Robot 側の型は
  docker/fetch_sim/ros_pkgs/coground_control/scripts/plan_types.py）。
- 物体 ID は Unity が決め、MoveIt の collision object 名（unity/<id>）と揃える。
- 物体はシミュレーション（Unity 上の仮想物体）と検出で同じ型。違うのは observation.source と属性の source だけ。
- 時刻 t は秒（float）。Unity の時計で、トライアル開始を 0 とする。
- JSON のキーはフィールド名のまま。Step の移動元だけ Python の予約語と重なるので、
  Python では `from_`、JSON では "from"。
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import taxonomy
from .taxonomy import ObjectGroup, ObjectRole

Vec3 = tuple[float, float, float]
Quat = tuple[float, float, float, float]  # x, y, z, w

AttributeValue = Union[bool, int, float, str]


class Pose(BaseModel):
    position: Vec3 = Field(description="物体（bbox）の中心")
    rotation: Quat = (0.0, 0.0, 0.0, 1.0)


# ---------------------------------------------------------------- 1. Scene（いまの状態）


ObjectSource = Literal["simulation", "detection", "manual"]
"""simulation: Unity 上に置いた仮想物体（真値） / detection: 検出器 / manual: 実験者が手で登録"""

AttributeSource = Literal["ground_truth", "detector", "vlm", "user"]

TrackingState = Literal["tracked", "occluded", "lost"]
"""tracked: いま見えている / occluded: 見えていないが最後の位置で残している / lost: 見失った"""


class Attribute(BaseModel):
    """物体の属性 1 つ。語彙は taxonomy.ATTRIBUTES。"""

    value: AttributeValue
    source: AttributeSource = "ground_truth"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    observed_at: float | None = Field(default=None, description="その値を得た時刻（秒、captured_at と同じ時計）")

    @model_validator(mode="before")
    @classmethod
    def _shorthand(cls, data: Any) -> Any:
        # {"fragile": true} のように値だけ書いたら、真値として扱う
        if isinstance(data, (bool, int, float, str)):
            return {"value": data}
        return data


class Observation(BaseModel):
    """その物体をどう得たか。シミュレーションと検出で、ここだけが違う。"""

    source: ObjectSource = "simulation"
    detector_label: str | None = Field(default=None, description="検出器が出した生のラベル（COCO の cup など）")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="検出の確信度")
    tracking: TrackingState = "tracked"
    last_seen: float | None = Field(default=None, description="最後に見えた時刻（秒、captured_at と同じ時計）")
    image_id: str | None = Field(default=None, description="切り出し画像の ID（後で REST で受け取る予定）")


class RegionBox(BaseModel):
    """向きのある直方体。高さのある領域（「棚の下段」、シンクの中など）。"""

    center: Vec3
    size: Vec3 = Field(description="大きさ（ローカル軸）")
    rotation: Quat = (0.0, 0.0, 0.0, 1.0)

    def contains(self, p: Vec3) -> bool:
        d = (p[0] - self.center[0], p[1] - self.center[1], p[2] - self.center[2])
        local = _rotate_inverse(self.rotation, d)
        return all(abs(local[i]) <= self.size[i] / 2 for i in range(3))

    @property
    def volume(self) -> float:
        return self.size[0] * self.size[1] * self.size[2]


class SceneObject(BaseModel):
    id: str = Field(min_length=1, description="Unity が決める物体 ID")
    category: str = Field(min_length=1, description="正規化したカテゴリ（taxonomy.CATEGORIES。未知の名前も可）")
    role: ObjectRole | None = Field(default=None, description="item / receptacle / surface。省略するとカテゴリ表から埋める")
    group: ObjectGroup | None = Field(default=None, description="dish / cutlery / trash など。省略するとカテゴリ表から埋める")
    position: Vec3 = Field(description="bbox 中心（Unity ワールド座標）")
    rotation: Quat = (0.0, 0.0, 0.0, 1.0)
    size: Vec3 | None = Field(default=None, description="bbox の大きさ（ローカル軸）")
    attributes: dict[str, Attribute] = Field(
        default_factory=dict,
        description='ルール照合に使う属性。例: {"fragile": true}（値だけなら真値）、'
        '{"fragile": {"value": true, "source": "vlm", "confidence": 0.7}}',
    )
    region_id: str | None = Field(
        default=None, description="いまどの領域にあるか。省略すると、中心を含むいちばん小さい box の領域から求める"
    )
    place_zone: RegionBox | None = Field(
        default=None,
        description="receptacle・surface のみ: 物を置ける / 入れられる範囲。この物体と同じ ID の領域になる",
    )
    approach_poses: list[Pose] = Field(
        default_factory=list,
        description="receptacle・surface のみ: ロボット（台車の base_link）が止まって作業する位置と向き（Unity ワールド座標。"
        "向きは Unity の +Z が台車の正面）。動作計画は、ここに置く・ここから取るとき、まずこの位置を試す",
    )
    observation: Observation = Field(default_factory=Observation)
    extra: dict[str, Any] = Field(default_factory=dict, description="試験的な追加情報")

    @model_validator(mode="after")
    def _fill_from_taxonomy(self) -> SceneObject:
        role, group = taxonomy.lookup(self.category)
        if self.role is None:
            self.role = role
        if self.group is None:
            self.group = group
        return self

    @property
    def pose(self) -> Pose:
        return Pose(position=self.position, rotation=self.rotation)

    def value(self, key: str) -> AttributeValue | None:
        """ルール照合で読む値。category / group / role は物体の欄、それ以外は attributes。"""
        if key in ("category", "group", "role"):
            return getattr(self, key)
        attr = self.attributes.get(key)
        return attr.value if attr is not None else None


class SceneRegion(BaseModel):
    """領域。polygon（床面）か box（高さあり）のどちらか、または両方を持つ。

    box に統一するかは未決なので、いまは両方を受け付ける。
    receptacle・surface の物体の place_zone からも作られる（id はその物体の ID、object_id も同じ）。
    """

    id: str = Field(min_length=1)
    label: str = Field(description="living_center, sink, shelf_lower など")
    polygon: list[Vec3] | None = Field(
        default=None, min_length=3, description="床面のポリゴン（Unity ワールド座標）"
    )
    box: RegionBox | None = None
    object_id: str | None = Field(default=None, description="この領域を持つ物体（シンク、ごみ箱、机など）")

    @model_validator(mode="after")
    def _has_shape(self) -> SceneRegion:
        if self.polygon is None and self.box is None:
            raise ValueError(f"Zone {self.id!r} has neither polygon nor box")
        return self


PersonKind = Literal["child", "adult", "unknown"]


class Person(BaseModel):
    """人の位置（家庭ルールの「子供の近くでは台車を止める」などに使う）。people.update で届く。"""

    id: str = Field(min_length=1)
    kind: PersonKind = Field(default="unknown", description="child / adult / unknown（子供かどうか分からない）")
    position: Vec3 = Field(description="Unity ワールド座標（高さは使わない）")
    observed_at: float | None = Field(default=None, description="その位置を得た時刻（秒、captured_at と同じ時計）")


class SceneSnapshot(BaseModel):
    """シーン全体。検証のときに、次の 2 つを埋める（Unity は送らなくてよい）。

    - place_zone を持つ物体から領域を作る（すでに object_id が同じ領域があれば作らない）
    - region_id が無い物体に、中心を含むいちばん小さい box の領域を入れる
      （机の上のシンクに入っている皿なら、机ではなくシンク）
    """

    frame: Literal["unity_world"] = "unity_world"
    captured_at: float | None = Field(default=None, description="Unity 側の時刻（秒）")
    objects: list[SceneObject] = Field(default_factory=list)
    regions: list[SceneRegion] = Field(default_factory=list)
    people: list[Person] | None = Field(
        default=None, description="人の位置。null なら、このシーンは人について何も言っていない（前に届いた値のまま。"
        "ふつうは people.update で別に送る）。空のリストは「見えている範囲に誰もいない」")

    @model_validator(mode="after")
    def _check_and_fill(self) -> SceneSnapshot:
        owned = {r.object_id for r in self.regions if r.object_id}
        for o in self.objects:
            if o.place_zone is not None and o.id not in owned:
                self.regions.append(SceneRegion(id=o.id, label=o.category, box=o.place_zone, object_id=o.id))

        object_ids = [o.id for o in self.objects]
        region_ids = [r.id for r in self.regions]
        dup = sorted({i for i in object_ids if object_ids.count(i) > 1} | {i for i in region_ids if region_ids.count(i) > 1})
        # 物体の place_zone から作った領域だけは、物体と同じ ID でよい
        dup += sorted({r.id for r in self.regions if r.id in object_ids and r.object_id != r.id})
        if dup:
            raise ValueError(f"Duplicate IDs: {dup}")
        unknown_owner = sorted({r.object_id for r in self.regions if r.object_id} - set(object_ids))
        if unknown_owner:
            raise ValueError(f"regions object_id not in objects: {unknown_owner}")

        boxed = [r for r in self.regions if r.box is not None]
        for o in self.objects:
            if o.region_id is None:
                inside = [r for r in boxed if r.object_id != o.id and r.box.contains(o.position)]  # type: ignore[union-attr]
                if inside:
                    o.region_id = min(inside, key=lambda r: r.box.volume).id  # type: ignore[union-attr]

        unknown = sorted({o.region_id for o in self.objects if o.region_id} - set(region_ids))
        if unknown:
            raise ValueError(f"objects region_id not in regions: {unknown}")
        return self


def _rotate_inverse(q: Quat, v: Vec3) -> Vec3:
    """v を q の逆回転で回す（ワールド -> ローカル）。q は単位四元数とみなす。"""
    x, y, z, w = -q[0], -q[1], -q[2], q[3]
    # v' = v + 2w(u x v) + 2u x (u x v)
    cx, cy, cz = y * v[2] - z * v[1], z * v[0] - x * v[2], x * v[1] - y * v[0]
    ccx, ccy, ccz = y * cz - z * cy, z * cx - x * cz, x * cy - y * cx
    return (v[0] + 2 * (w * cx + ccx), v[1] + 2 * (w * cy + ccy), v[2] + 2 * (w * cz + ccz))


# ---------------------------------------------------------------- 2. Rule


class RuleCondition(BaseModel):
    """「属性 = 値」だけ。ASP（clingo）などの本格的な表現は後で足す。

    attribute には attributes のキーのほか、category / group / role も書ける
    （例: {"attribute": "group", "equals": "dish"} = 食器すべて）。
    """

    attribute: str = Field(min_length=1)
    equals: AttributeValue

    def matches(self, obj: SceneObject) -> bool:
        v = obj.value(self.attribute)
        return v is not None and v == self.equals


RuleSource = Literal["speech", "demo", "script"]


class Rule(BaseModel):
    """条件に合う物を、行き先の領域に置く。

    condition が null のルールは「それ以外」（例: それ以外は箱にしまう）。
    条件のあるルールのどれにも合わなかった物（role = item）にだけ使う。
    """

    id: str = Field(min_length=1)
    text: str = Field(description="可視化で見せる文。例: 割れ物は棚の下段に置く")
    condition: RuleCondition | None = Field(default=None, description="null なら「それ以外」")
    target_region: str = Field(min_length=1, description="行き先の領域の ID")
    source: RuleSource = "script"

    @property
    def is_fallback(self) -> bool:
        return self.condition is None


# ---------------------------------------------------------------- 3. 入力（タスク実行）


class Utterance(BaseModel):
    t_start: float
    t_end: float
    text: str

    @model_validator(mode="after")
    def _order(self) -> Utterance:
        if self.t_end < self.t_start:
            raise ValueError("t_end is before t_start")
        return self


class InteractionEvent(BaseModel):
    """実演（ユーザーが物体をつかむ / 離す）。音声指示だけなら使わない。"""

    t: float
    type: Literal["grasp", "release"]
    object_id: str = Field(min_length=1)
    pose: Pose = Field(description="そのときの物体の姿勢")


# ---------------------------------------------------------------- 4. Plan（処理の出力、可視化の対象）


class Placement(BaseModel):
    region_id: str | None = Field(default=None, description="領域の外なら null")
    pose: Pose


# 家庭ルールの判定（ルールの型と評価は norms/。Step が持つので、型だけここに置く）

VerdictValue = Literal["violated", "compliant", "not_applicable", "undetermined"]
"""violated: 違反の証拠がある / compliant: 評価範囲で適合を確認 / not_applicable: 適用対象が無い /
undetermined: 足りない観測によって結論が変わる"""

Basis = Literal["predicted", "observed"]
"""predicted: 計画の予測状態列に対する判定 / observed: 観測した状態に対する判定"""


class MissingFact(BaseModel):
    """未確定のとき、何が分かれば結論が出るか。"""

    entity_id: str | None = Field(default=None, description="物体・領域・人物の ID。時計などは null")
    key: str = Field(description="attr:fragile / object_region / clock / requester など（norms/depends.py のキー）")


class Verdict(BaseModel):
    rule_id: str
    value: VerdictValue
    basis: Basis
    entity_id: str | None = Field(default=None, description="判定した対象（物体や領域）の ID")
    t: datetime | None = Field(default=None, description="違反した時刻（家の時計）。違反以外は null")
    missing: list[MissingFact] = Field(default_factory=list)
    detail: str = ""
    evaluated_at: datetime | None = Field(default=None, description="判定した時刻（家の時計）")

    def same_as(self, other: Verdict | None) -> bool:
        """判定の中身が同じか（時刻の違いは見ない）。履歴に同じものを積まないために使う。"""
        if other is None:
            return False
        skip = {"evaluated_at", "t"}
        return self.model_dump(exclude=skip) == other.model_dump(exclude=skip)

    def timeless(self) -> Verdict:
        """時刻を落とした写し（Step に入れる。時刻だけ違う判定で Plan を作り直さないため）。"""
        return self.model_copy(update={"evaluated_at": None, "t": None})


StepStatus = Literal["ok", "ambiguous", "unmatched", "infeasible", "deferred"]


class Step(BaseModel):
    """物体 1 つの Pick & Place。

    status:
      ok          計画できた
      ambiguous   合うルールが複数あって決められない（候補は candidate_rule_ids）
      unmatched   合うルールが無い（to と rule_id は null）
      infeasible  MoveIt で計画できない
      deferred    家庭ルールにより保留（禁止に反する、判定する情報が足りない、収納先が決まらない）。
                  理由は message、判定は verdicts。依頼（task.request）から作った Plan だけに出る
    """

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    id: str = Field(min_length=1, description='Plan の中で一意。例: "s1"')
    index: int = Field(ge=0, description="実行順（0 始まり）")
    object_id: str = Field(min_length=1)
    from_: Placement = Field(alias="from", description="動かす前")
    to: Placement | None = Field(default=None, description="動かした後（行き先が決まらなければ null）")
    rule_id: str | None = Field(default=None, description="なぜそうするか")
    candidate_rule_ids: list[str] = Field(default_factory=list, description="ambiguous のときの候補")
    status: StepStatus = "ok"
    locked: bool = Field(default=False, description="ユーザーが修正して固定したか")
    trajectory_id: str | None = Field(
        default=None, description="軌道の ID。軌道そのものは ROS / Unity 側が持つ"
    )
    message: str | None = Field(default=None, description="infeasible の理由など、人が読む補足")
    verdicts: list[Verdict] = Field(default_factory=list, description="この step に関係する家庭ルールの判定（時刻は入れない）")

    @model_validator(mode="after")
    def _consistent(self) -> Step:
        if self.status in ("ok", "infeasible") and self.to is None:
            raise ValueError(f"step {self.id!r}: status is {self.status} but to is missing")
        return self


class Plan(BaseModel):
    """各 step 後のシーンと軌道の中身は入れない。

    - 各 step 後のシーン: 最初のシーンに step を順に当てれば計算できる（Unity 側で作る）
    - 軌道の中身: 大きいので MoveIt から Unity へ ROS-TCP で届ける。Plan は trajectory_id だけを持つ
    """

    id: str = Field(min_length=1)
    version: int = Field(default=1, ge=1, description="修正のたびに上げる")
    base_scene_version: int = Field(ge=0, description="どの state.version のシーンから作った計画か")
    steps: list[Step] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_steps(self) -> Plan:
        ids = [s.id for s in self.steps]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            raise ValueError(f"Duplicate step IDs: {dup}")
        if [s.index for s in self.steps] != list(range(len(self.steps))):
            raise ValueError("steps must be in index order (consecutive from 0)")
        return self

    def step(self, step_id: str) -> Step | None:
        return next((s for s in self.steps if s.id == step_id), None)


# ---------------------------------------------------------------- 5. Correction（修正）

CorrectionType = Literal["move", "reject", "reorder"]


class Correction(BaseModel):
    """UI から構造化されて届く修正。その 1 回だけに効く（インスタンス修正）。

    move     その物体を new_pose に置く（該当 step を locked にして、置き位置・順序・動作計画をやり直す）
    reject   その step をやめる（物体を動かさない）
    reorder  その step を new_index 番目にする
    """

    id: str = Field(min_length=1, description="Unity が決める（TrialLog から参照する）")
    plan_id: str = Field(min_length=1)
    plan_version: int = Field(ge=1, description="どの版の Plan に対する修正か")
    step_id: str = Field(min_length=1)
    object_id: str = Field(min_length=1)
    type: CorrectionType
    new_pose: Pose | None = Field(default=None, description="move のとき")
    new_region_id: str | None = Field(default=None, description="move のとき。UI が分かっていれば")
    new_index: int | None = Field(default=None, ge=0, description="reorder のとき")
    t: float

    @model_validator(mode="after")
    def _payload(self) -> Correction:
        if self.type == "move" and self.new_pose is None:
            raise ValueError("move requires new_pose")
        if self.type == "reorder" and self.new_index is None:
            raise ValueError("reorder requires new_index")
        return self


# ---------------------------------------------------------------- 6. Scenario（実験用の台本）

InjectedErrorType = Literal["wrong_object", "wrong_place", "over_generalize"]


class InjectedError(BaseModel):
    step_id: str = Field(min_length=1, description="presented_plan の step")
    type: InjectedErrorType


class Scenario(BaseModel):
    """ルール照合と目標の決定を差し替える台本。サーバーのファイルに置き、起動時に読み込む。

    ground_truth_plan と presented_plan の差が、ユーザーが見つけるべき誤りになる。
    """

    id: str = Field(min_length=1)
    initial_scene: SceneSnapshot
    rules: list[Rule] = Field(default_factory=list)
    ground_truth_plan: Plan = Field(description="正しい計画")
    presented_plan: Plan = Field(description="ユーザーに見せる計画（誤りを仕込む）")
    injected_errors: list[InjectedError] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_refs(self) -> Scenario:
        problems: list[str] = []
        object_ids = {o.id for o in self.initial_scene.objects}
        region_ids = {r.id for r in self.initial_scene.regions}
        rule_ids = [r.id for r in self.rules]
        dup = sorted({i for i in rule_ids if rule_ids.count(i) > 1})
        if dup:
            problems.append(f"Duplicate rule IDs: {dup}")
        for rule in self.rules:
            if rule.target_region not in region_ids:
                problems.append(f"{rule.id}: target_region {rule.target_region!r} doesn't exist")
        for name, plan in (("ground_truth_plan", self.ground_truth_plan), ("presented_plan", self.presented_plan)):
            for step in plan.steps:
                where = f"{name}.{step.id}"
                if step.object_id not in object_ids:
                    problems.append(f"{where}: object_id {step.object_id!r} doesn't exist")
                for rid in [step.rule_id, *step.candidate_rule_ids]:
                    if rid is not None and rid not in rule_ids:
                        problems.append(f"{where}: rule_id {rid!r} doesn't exist")
                for place in (step.from_, step.to):
                    if place is not None and place.region_id is not None and place.region_id not in region_ids:
                        problems.append(f"{where}: region_id {place.region_id!r} doesn't exist")
        presented = {s.id for s in self.presented_plan.steps}
        for err in self.injected_errors:
            if err.step_id not in presented:
                problems.append(f"injected_errors: step_id {err.step_id!r} not in presented_plan")
        if problems:
            raise ValueError("; ".join(problems))
        return self


# ---------------------------------------------------------------- 7. TrialLog（計測）

Condition = Literal["toggle", "sequence_ghost"]


class _TrialEvent(BaseModel):
    t: float


class ViewToggleEvent(_TrialEvent):
    type: Literal["view_toggle"]
    view: Literal["before", "after"] | None = Field(default=None, description="切り替えた後の表示")


class StepSelectEvent(_TrialEvent):
    type: Literal["step_select"]
    step_id: str = Field(min_length=1)


class CorrectionEvent(_TrialEvent):
    type: Literal["correction"]
    correction_id: str = Field(min_length=1)


class ApproveEvent(_TrialEvent):
    type: Literal["approve"]
    plan_version: int | None = Field(default=None, ge=1, description="承認した Plan の版")


TrialEvent = Annotated[
    Union[ViewToggleEvent, StepSelectEvent, CorrectionEvent, ApproveEvent],
    Field(discriminator="type"),
]


class TrialLog(BaseModel):
    """誤りの発見率、修正の正確さ、承認までの時間、可視化の使われ方を後から出すためのデータ。

    events は Unity から WebSocket の event で 1 件ずつ届き、サーバーがファイルに書く。
    修正の正確さを後から出せるように、届いた Correction の中身も corrections に残す。
    """

    participant_id: str = Field(min_length=1)
    condition: Condition
    scenario_id: str = Field(min_length=1)
    started_at: str | None = Field(default=None, description="t = 0 の時刻（ISO 8601、サーバーの時計）")
    events: list[TrialEvent] = Field(default_factory=list)
    corrections: list[Correction] = Field(default_factory=list)
