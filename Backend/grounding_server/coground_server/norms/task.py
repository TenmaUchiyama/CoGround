"""依頼の記録（TaskRecord）。Plan とは別に持つ。

Plan はシーンが変わるたびに作り直されるが、依頼の対象は依頼したときに決まり、あとで選び直さない。
収納したコップが机から無くなっても、行は残る（「2 点中 1 点完了」の分母が変わらない）。

行（TaskRow）は物体 1 つ。次の 3 つを別々に持つ:
  destination   指定された収納先（収納先を決める義務から。決まらなければ null）
  verdicts      ルールごとの最新の判定（予測か観測かは Verdict.basis）
  exec_state    実行の状態

  exec_state:
    pending            まだ何もしていない
    deferred           保留（禁止の予測、足りない事実、行き先が決まらない、など。reason に理由）
    in_progress        実行中
    placed_unverified  配置動作は成功。配置先の観測を待っている
    done               指定の収納先にあるのを観測した
    misplaced          別の場所にあるのを観測した
    unverified         観測が来なかった
    failed             動作に失敗した

触れずに保留した物体は「違反の予測により保留」であり、実行時の違反ではない
（Verdict.basis = predicted のまま、exec_state = deferred になる）。

判定は上書きせず history に積む。中身が前と同じ判定は積まない（シーンが届くたびに増えないように）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from typing import Any

from .model import MissingFact, NormRule, Verdict

ExecState = Literal[
    "pending", "deferred", "in_progress", "placed_unverified", "done", "misplaced", "unverified", "failed",
]


class TaskRow(BaseModel):
    object_id: str = Field(min_length=1)
    label: str = Field(default="", description="説明で使う呼び名（依頼したときのカテゴリなど）")
    destination: str | None = Field(default=None, description="指定された収納先の領域 ID")
    destination_rule_ids: list[str] = Field(default_factory=list, description="収納先を決めたルール")
    verdicts: dict[str, Verdict] = Field(default_factory=dict, description="ルール ID -> 最新の判定")
    exec_state: ExecState = "pending"
    reason: str = Field(default="", description="保留・失敗などの理由（人が読む）")
    missing: list[MissingFact] = Field(default_factory=list, description="保留を解くのに足りない事実")
    history: list[Verdict] = Field(default_factory=list, description="判定の履歴（古い順）")
    route: dict[str, Any] | None = Field(
        default=None, description="経路の判定で探した条件（計画した時刻、避けた領域、試した回ごとの結果）。まだ経路を計画していなければ null")
    requested_destination: str | None = Field(
        default=None, description="住人がシーケンスの編集（sequence.add）で指定した置き先の領域 ID。"
        "収納先を決めるルールと照合し、合わなければ保留にする（手の指定 plan.place とは違い、ルールを確かめる）")
    added: bool = Field(default=False, description="住人がシーケンスの編集で足した行（依頼したときの対象ではない）")
    overridden_rule_ids: list[str] = Field(
        default_factory=list, description="依頼の間だけのルールが先に立ったので、収納先に使わなかった常設のルール"
        "（例: 「全部 box_1」で、ゴミ箱のルールを使わなかった）")
    region_full: dict[str, bool] = Field(
        default_factory=dict, description="収納先を決めたときに調べた、領域 ID -> その物を置く空きが無いか（条件 region_full）")

    def record(self, verdict: Verdict) -> bool:
        """判定を記録する。前と中身が違えば history に積み、True を返す。

        中身が同じなら何も変えない（判定した時刻も前のまま。関係ない訂正で、ほかの行の記録が動かないように）。
        """
        if verdict.same_as(self.verdicts.get(verdict.rule_id)):
            return False
        self.history.append(verdict)
        self.verdicts[verdict.rule_id] = verdict
        return True

    def set_state(self, state: ExecState, reason: str = "", missing: list[MissingFact] | None = None) -> None:
        self.exec_state, self.reason, self.missing = state, reason, list(missing or [])


class RouteBlock(BaseModel):
    """経路が家庭ルールに反する（または判定できない）ので、その物体を運べない。動作計画・実行中の再計画が入れる。

    ルール・領域・時計が変わるか、動作計画をやり直す（motion.plan）と消える。
    """

    reason: str = Field(description="人が読む理由。例: 「…」（R2）に反しない経路が無い")
    verdicts: list[Verdict] = Field(default_factory=list)
    missing: list[MissingFact] = Field(default_factory=list)
    searched: dict[str, Any] = Field(default_factory=dict, description="探した条件")


class RowChange(BaseModel):
    """訂正の前後で、行のどこが変わったか。"""

    object_id: str
    what: str = Field(description="destination / exec_state / verdict:<ルール ID>")
    before: Any = None
    after: Any = None


CorrectionKind = Literal["attribute", "rule", "zone", "exception"]


class AttributeCorrection(BaseModel):
    """住人による訂正と、それで変わった判定。

    kind:
      attribute  物体の属性（「この皿は割れ物ではない」）。object_id と key（fragile など）
      rule       ルールの Scope（「19 時からにして」）。entity_id がルールの ID、key は "scope"
      zone       領域の範囲。entity_id が領域の ID、key は "shape"
      exception  例外の追加（「私が頼んだときは触ってよい」）。entity_id が元の禁止の ID、key は "exception"、after が足した許可
    """

    id: str = Field(min_length=1)
    t: datetime | None = Field(default=None, description="訂正した時刻（家の時計）")
    kind: CorrectionKind = "attribute"
    object_id: str | None = Field(default=None, description="属性の訂正のとき: 物体の ID")
    entity_id: str | None = Field(default=None, description="訂正した相手（物体・ルール・領域の ID）")
    key: str = Field(description="属性のキー（fragile など）、または scope / shape / exception")
    before: Any = Field(default=None, description="訂正の前の値（不明なら null）")
    after: Any = Field(default=None, description="訂正した値（null なら訂正を取り消した）")
    affected_rule_ids: list[str] = Field(default_factory=list, description="この訂正で評価し直すルール")
    changes: list[RowChange] = Field(default_factory=list, description="変わった行と項目。ここに無いものは変わっていない")


class TaskRecord(BaseModel):
    id: str = Field(min_length=1)
    text: str = Field(description="依頼の言葉。例: 机の上のものを全部片づけて")
    requester: str | None = Field(default=None, description="依頼者の人物 ID（分からなければ null）")
    source_region: str | None = Field(default=None, description="対象を選んだ領域（机など）")
    created_at: datetime | None = Field(default=None, description="依頼した時刻（家の時計）")
    closed_at: datetime | None = Field(default=None, description="依頼を閉じた時刻。閉じると Plan に使わない")
    rows: list[TaskRow] = Field(
        default_factory=list, description="依頼したときに決めた対象。並び順が作業の順序。シーンが変わっても選び直さないが、"
        "住人はシーケンスの編集（sequence.add / remove / reorder）で足す・外す・並べ替えることができる")
    sequence_version: int = Field(default=0, description="住人がシーケンスを編集するたびに上がる")
    removed: list[str] = Field(default_factory=list, description="住人がシーケンスから外した物体（記録）")
    corrections: list[AttributeCorrection] = Field(default_factory=list, description="この依頼の間の訂正（古い順）")
    rules: list[NormRule] = Field(
        default_factory=list, description="この依頼の間だけ効くルール（origin = task。例: 全部 box_1 に入れて）。"
        "依頼を閉じると効かない。収納先は常設のルールより先に立つ")

    def row(self, object_id: str) -> TaskRow | None:
        return next((r for r in self.rows if r.object_id == object_id), None)

    @property
    def object_ids(self) -> list[str]:
        return [r.object_id for r in self.rows]

    def digest(self) -> dict[str, dict[str, Any]]:
        """行ごとの要点（収納先、実行の状態、ルールごとの判定と根拠）。訂正の前後を比べるのに使う。"""
        return {
            r.object_id: {
                "destination": r.destination, "exec_state": r.exec_state,
                **{f"verdict:{rid}": f"{v.value} ({v.basis})" for rid, v in r.verdicts.items()},
            }
            for r in self.rows
        }

    def counts(self) -> dict[str, int]:
        """total は依頼したときの対象の数。done は収納先にあるのを観測した数。"""
        out = {"total": len(self.rows), "done": 0}
        for r in self.rows:
            out[r.exec_state] = out.get(r.exec_state, 0) + 1
        return out
