"""perception でやり取りする JSON の形。

ID は 2 種類あり、混ぜない:
  detection_id  その画像の中だけの仮の番号（1, 2, 3...）。SoM 画像の番号（mark_id）と同じ
  object_id     物体をまたいで続く ID（"obj_001"）。記憶（object_store）の鍵
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Material = Literal["glass", "ceramic", "plastic", "metal", "paper", "wood", "other", "unknown"]
Fragility = Literal["likely_fragile", "not_fragile", "uncertain"]
VlmStatus = Literal["pending", "completed", "failed"]


class Detection(BaseModel):
    """検出器が 1 枚の画像から見つけた物体 1 つ。"""

    model_config = ConfigDict(populate_by_name=True)

    detection_id: int = Field(ge=1)
    cls: str = Field(alias="class", description="検出器の語彙でのクラス（cup など）")
    bbox: list[float] = Field(min_length=4, max_length=4, description="[x1, y1, x2, y2]（画素）")
    confidence: float = Field(ge=0.0, le=1.0)
    mask: list[list[float]] = Field(default_factory=list, description="マスクの輪郭 [[x, y], ...]（画素）。無ければ空")
    embedding: list[float] | None = Field(default=None, description="見た目の特徴量（/segment?embed=1 のときだけ）")


class ImageSize(BaseModel):
    width: int
    height: int


class Segmentation(BaseModel):
    """detector の POST /segment の答え。"""

    image: ImageSize
    detections: list[Detection]
    model: str | None = None
    infer_ms: float | None = None


class AttributeQuestion(BaseModel):
    """VLM に聞く属性 1 つ。いまあるルールが使っている属性から作る（norms/attributes.py の questions）。"""

    name: str = Field(min_length=1, description="属性のキー（fragile など）")
    how_to_tell: str = Field(default="", description="見分け方")
    values: list[str] = Field(default_factory=list, description="答えの選択肢。空なら自由に答える")


class AttributeAnswer(BaseModel):
    """ルールが使う属性についての、VLM の答え 1 つ。"""

    name: str = Field(description="The attribute key that was asked")
    value: str = Field(description='One of the allowed values, or "unknown" if it can\'t be judged from the image')
    evidence: str = Field(default="", description="What in the image the answer is based on, as one short phrase (e.g. material: plastic)")


class MarkAttributes(BaseModel):
    """VLM が番号 1 つについて答える属性。"""

    mark_id: int = Field(description="The number drawn on the object in the marked image")
    category: str = Field(description="What the object is, as a short lowercase noun in snake_case (mug, paper_cup, plastic_bottle)")
    material: Material = Field(description="Main material. unknown if it can't be judged from the image")
    fragility: Fragility = Field(description="likely_fragile: would break if dropped or squeezed (glass, ceramic). "
                                             "not_fragile: clearly robust. uncertain: can't tell")
    appearance: str = Field(description="One short phrase describing how it looks (color, shape), to check the mark matches the object")
    answers: list[AttributeAnswer] = Field(
        default_factory=list, description="One entry per additional attribute that was asked about (empty if none was asked)")


class VlmAnswer(BaseModel):
    objects: list[MarkAttributes]


class ObjectRecord(BaseModel):
    """記憶している物体 1 つ。"""

    object_id: str
    category: str | None = Field(default=None, description="VLM が答えたカテゴリ")
    detected_class: str | None = Field(default=None, description="検出器が最後に出したクラス")
    attributes: dict[str, str] = Field(
        default_factory=dict, description="material / fragility / appearance と、ルールが使う属性（聞いたものだけ。分からなければ unknown）")
    evidence: dict[str, str] = Field(
        default_factory=dict, description="ルールが使う属性ごとの、VLM の判断の根拠（例: fragile -> material: plastic）")
    vlm_status: VlmStatus = "pending"
    attribute_version: int = Field(default=0, description="属性を書き込んだ回数（初回の解析で 1、再解析のたびに +1）")
    vlm_calls: int = Field(default=0, description="この物体のために VLM を呼んだ回数")
    cache_hits: int = Field(default=0, description="保存した属性をそのまま返した回数")
    error: str | None = None
    created_at: float = 0.0
    updated_at: float = Field(default=0.0, description="属性を最後に書き込んだ時刻")
    last_seen_at: float = 0.0
    last_bbox: list[float] | None = None
    last_run_id: str | None = None
    presence: Literal["present", "displaced", "missing"] | None = Field(
        default=None, description="3D で追っている物体だけ: その場にある / あった場所が空いている / 無くなった")
    position: list[float] | None = Field(default=None, description="3D の箱の中心（Unity のワールド座標、m）")
    size: list[float] | None = Field(default=None, description="3D の箱の大きさ（m）")


class AnalyzedObject(BaseModel):
    """analyze の答えの物体 1 つ: その画像での検出（detection_id）と、記憶（object_id）の両方。"""

    model_config = ConfigDict(populate_by_name=True)

    detection_id: int
    object_id: str | None = Field(description="記憶の ID。3D にできなかった検出（unlocated）は null")
    cls: str = Field(alias="class")
    bbox: list[float]
    confidence: float
    category: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    evidence: dict[str, str] = Field(default_factory=dict, description="ルールが使う属性ごとの、VLM の判断の根拠")
    vlm_status: VlmStatus | None = None
    attribute_version: int = 0
    source: Literal["vlm", "memory", "waited", "unlocated"] = Field(
        description="vlm: この依頼で VLM が解析した / memory: 記憶の値を返した / waited: ほかの依頼の解析を待った / "
                    "unlocated: 深度が足りず 3D にできなかった（記憶にも VLM にも回さない）")
    error: str | None = None
    track: Literal["new", "same", "moved"] | None = Field(
        default=None, description="フレーム（3D）のときだけ: 初めて見た / その場にあった / 別の場所に動いていた")
    position: list[float] | None = None
    size: list[float] | None = None


class VlmUsage(BaseModel):
    calls: int = Field(description="この依頼で VLM を呼んだ回数（0 か 1）")
    analyzed: list[str] = Field(default_factory=list, description="VLM に解析させた object_id")
    reused: list[str] = Field(default_factory=list, description="記憶から返した object_id")
    seconds: float | None = None
    error: str | None = None


class FrameSummary(BaseModel):
    """フレーム（3D）のときだけ: 再認識の結果。"""

    timestamp: float
    depth_points: int = Field(description="深度から戻せた点の数")
    depth_coverage: float = Field(description="位置を合わせた深度画像のうち、深度がある画素の割合")
    located: int = Field(description="3D にできた検出の数")
    displaced: list[str] = Field(default_factory=list, description="このフレームで、あった場所が空いていると分かった物体")
    missing: list[str] = Field(default_factory=list, description="このフレームで、無くなったことになった物体")
    merged: dict[str, str] = Field(default_factory=dict, description="同じ物体として 1 つにまとめた（消した ID → 残した ID）")


class AnalyzeResult(BaseModel):
    run_id: str
    image: ImageSize
    objects: list[AnalyzedObject]
    vlm: VlmUsage
    timings_ms: dict[str, float]
    memory_stats: dict[str, Any]
    frame: FrameSummary | None = None
    artifacts: dict[str, str] = Field(default_factory=dict, description="残したファイル（名前 -> URL）。残さない設定なら空")
