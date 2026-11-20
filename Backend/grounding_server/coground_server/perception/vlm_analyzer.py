"""番号つき画像（Set-of-Mark）を VLM に見せて、番号ごとの属性を受け取る。

VLM は 1 回の依頼につき 1 回だけ呼ぶ（解析したい番号をまとめて聞く）。元の画像と番号つき画像の 2 枚を渡す
（番号や塗りで隠れた部分を、元の画像で見られるように）。

どの物体にも聞く項目（category / material / fragility / appearance）のほかに、いまあるルールが使っている属性を聞く
（questions。「割れ物には触らない」というルールがあれば、割れ物かどうかと、その根拠を聞く）。ルールが無い属性は聞かない。

呼び出しは llm/client.py の口を通る（API キーか Claude Agent SDK。記録は COGROUND_LLM_LOG の llm.jsonl に
name = "analyze_objects" で残る。かかった秒もそこにある）。
"""

from __future__ import annotations

import json
from typing import Callable, Sequence

from ..llm import LlmClient
from .schema import AttributeQuestion, Detection, VlmAnswer

SYSTEM = """\
You look at a photo of household objects for a home robot and report each marked object's attributes.

You get two images of the same scene:
  1. the original photo
  2. the same photo with objects outlined and tagged with a number (the mark)

For every mark you are asked about, answer:
  mark_id     the number on the object
  category    what the object is: a short lowercase noun in snake_case (mug, glass, paper_cup, plastic_bottle, can, bowl)
  material    glass | ceramic | plastic | metal | paper | wood | other | unknown
  fragility   likely_fragile (would break if dropped or squeezed: glass, ceramic, thin porcelain)
              not_fragile    (clearly robust: metal, thick plastic, paper)
              uncertain      (can't tell from the image)
  appearance  one short phrase on how it looks (color, shape)

Rules:
- Judge from what is visible in the images. The detector's class is only a hint and may be wrong.
- If the material can't be judged from the image, answer "unknown" and fragility "uncertain". Do not guess.
- Answer exactly one entry per requested mark, and no entry for any other mark.
- Use the original photo to see parts that the outline or the number tag covers.
"""

# VLM に送る画像の長い辺（これより大きい画像は縮める）
MAX_IMAGE_SIDE = 1568


def build_questions(questions: Sequence[AttributeQuestion]) -> str:
    """ルールが使っている属性を聞く部分のプロンプト。"""
    lines = [
        "The household rules also depend on the following attributes. For every mark, add one entry per attribute to \"answers\":",
        "{\"name\": the attribute key, \"value\": one of the allowed values, \"evidence\": what you saw that the answer is based on}.",
        "If it can't be judged from the image, answer \"unknown\". Do not guess.",
    ]
    for q in questions:
        allowed = " | ".join([*q.values, "unknown"]) if q.values else "a short value, or unknown"
        lines.append(f"- {q.name}: {q.how_to_tell or 'judge it from the image'} (allowed values: {allowed})")
    return "\n".join(lines)


class VlmAnalyzer:
    def __init__(self, get_llm: Callable[[], LlmClient]) -> None:
        # 呼ぶたびに取り直す（Services.llm を差し替えたら、こちらも替わるように）
        self.get_llm = get_llm

    async def analyze(self, original_jpeg: bytes, som_jpeg: bytes, targets: Sequence[Detection],
                      questions: Sequence[AttributeQuestion] = ()) -> VlmAnswer:
        """targets（解析したい検出）の属性を聞く。答えから、頼んでいない番号・属性と重複は除く。

        questions は、いまあるルールが使っている属性。あれば、番号ごとに answers で答えさせる。"""
        marks = [{"mark_id": d.detection_id, "detector_class": d.cls} for d in targets]
        prompt = "Report the attributes of these marks:\n" + json.dumps(marks, ensure_ascii=False)
        if questions:
            prompt += "\n\n" + build_questions(questions)
        answer = await self.get_llm().generate(name="analyze_objects", system=SYSTEM, prompt=prompt, output=VlmAnswer,
                                         images=[original_jpeg, som_jpeg])
        wanted = {d.detection_id for d in targets}
        seen: set[int] = set()
        objects = []
        for obj in answer.objects:
            if obj.mark_id in wanted and obj.mark_id not in seen:
                seen.add(obj.mark_id)
                asked = {q.name for q in questions}
                answers = {a.name: a for a in reversed(obj.answers) if a.name in asked}
                objects.append(obj.model_copy(update={"answers": [answers[q.name] for q in questions if q.name in answers]}))
        return VlmAnswer(objects=objects)
