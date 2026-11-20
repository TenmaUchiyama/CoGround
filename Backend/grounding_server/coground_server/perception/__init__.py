"""物体の認識 → 属性の理解 → 記憶（Milestone 1: 画像から属性を取得・保存する）。

  画像 ──> segment_client（detector コンテナの YOLOE-seg）──> 物体ごとの矩形・マスク（detection_id は画像の中だけの番号）
       ──> object_store（記憶）に object_id で問い合わせる
             すでに属性がある      → 保存した値を返す（VLM は呼ばない）
             ほかの依頼が解析中    → その結果を待つ（VLM は呼ばない）
             新しい / 失敗していた → som（番号を重ねた画像）を作り、vlm_analyzer が VLM を 1 回だけ呼んで、結果を記憶に入れる

  schema.py          やり取りする JSON の形（Detection / ObjectRecord / AnalyzeResult）
  segment_client.py  detector の POST /segment を呼ぶ
  som.py             Set-of-Mark 画像（番号つき）と、確認用の分割結果の画像を描く
  vlm_analyzer.py    番号つき画像を VLM に見せて、番号ごとの属性（category / material / fragility）を受け取る
  object_store.py    Object Memory。object_id ごとの属性・vlm_status（pending / completed / failed）・attribute_version
  pipeline.py        上をつなぐ（Perception.analyze）。入力・途中の画像・JSON・時間を run ごとに残す
  api.py             REST（/perception/...）と確認用の画面（/perception/ui）

  association.py     再認識と変化の判定（3D の箱 + 見た目）。Embodied VideoAgent（ICCV 2025）の方式
  frame.py           Quest のフレーム（RGB + 深度 + カメラ）→ RGB に合わせた深度とカメラ

入口は 2 つ（pipeline.py）: analyze（画像 1 枚。object_id は固定）と analyze_frame（Quest のフレーム。object_id は再認識で決める）。
"""

from .object_store import ObjectMemory
from .pipeline import Perception, PerceptionError
from .schema import AnalyzeResult, Detection, ObjectRecord, Segmentation

__all__ = ["AnalyzeResult", "Detection", "ObjectMemory", "ObjectRecord", "Perception", "PerceptionError", "Segmentation"]
