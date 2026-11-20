"""検出結果を画像に重ねる。

  draw_marks    Set-of-Mark 画像: 物体ごとに輪郭と番号（detection_id）を重ねる。VLM に見せる
  draw_overlay  確認用: マスク・矩形・「番号 クラス 確信度」を重ねる（segmentation_overlay.jpg）
"""

from __future__ import annotations

import io
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

from .schema import Detection

# 隣どうしで見分けやすい色（番号の順に使う）
PALETTE = [(230, 57, 70), (29, 122, 204), (42, 157, 143), (244, 162, 97), (155, 89, 182),
           (233, 196, 36), (20, 160, 220), (214, 80, 150), (120, 180, 60), (255, 127, 14)]


def load_image(jpeg: bytes) -> Image.Image:
    with Image.open(io.BytesIO(jpeg)) as source:
        return source.convert("RGB")


def to_jpeg(image: Image.Image, max_side: int | None = None, quality: int = 90) -> bytes:
    """JPEG にする。max_side を渡すと、長い辺がそれを超えるときだけ縮める。"""
    if max_side and max(image.size) > max_side:
        scale = max_side / max(image.size)
        image = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, "JPEG", quality=quality)
    return buffer.getvalue()


def _font(image: Image.Image, scale: float = 1.0) -> ImageFont.ImageFont:
    return ImageFont.load_default(size=max(14, round(min(image.size) / 26 * scale)))


def _polygon(d: Detection) -> list[tuple[float, float]]:
    """マスクの輪郭。無ければ矩形の四隅。"""
    if len(d.mask) >= 3:
        return [(x, y) for x, y in d.mask]
    x1, y1, x2, y2 = d.bbox
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def mark_position(d: Detection) -> tuple[float, float]:
    """番号を置く点: マスクの重心。重心がマスクの外（C 字形など）なら、輪郭の上でいちばん近い点。"""
    points = _polygon(d)
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(area) < 1e-6:
        x1, y1, x2, y2 = d.bbox
        return (x1 + x2) / 2, (y1 + y2) / 2
    cx, cy = cx / (3 * area), cy / (3 * area)
    if _inside(cx, cy, points):
        return cx, cy
    return min(points, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)


def _inside(x: float, y: float, points: Sequence[tuple[float, float]]) -> bool:
    inside = False
    for (x0, y0), (x1, y1) in zip(points, list(points[1:]) + list(points[:1])):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            inside = not inside
    return inside


def _shade(image: Image.Image, detections: Sequence[Detection], alpha: int) -> Image.Image:
    """マスクを半透明の色で塗り、輪郭を引く。"""
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    width = max(2, round(min(image.size) / 300))
    for d in detections:
        color = PALETTE[(d.detection_id - 1) % len(PALETTE)]
        points = _polygon(d)
        draw.polygon(points, fill=(*color, alpha))
        draw.line(points + points[:1], fill=(*color, 255), width=width, joint="curve")
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


Box = tuple[float, float, float, float]


def _tag_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[float, float, int]:
    """札の（幅, 高さ, 余白）。"""
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    pad = max(3, (bottom - top) // 4)
    return right - left + 2 * pad, bottom - top + 2 * pad, pad


def _draw_tag(draw: ImageDraw.ImageDraw, text: str, box: Box, font: ImageFont.ImageFont,
              fill: tuple[int, int, int], outline: tuple[int, int, int]) -> None:
    """文字を、背景つきの札として box に描く。"""
    left, top, _, _ = draw.textbbox((0, 0), text, font=font)
    w, h, pad = _tag_size(draw, text, font)
    draw.rectangle(box, fill=fill, outline=outline, width=max(2, pad // 2))
    draw.text((box[0] + pad - left, box[1] + pad - top), text, fill=(255, 255, 255), font=font)


def _clamp(x: float, y: float, w: float, h: float, image: Image.Image) -> Box:
    x = min(max(0, x), max(0, image.width - w))
    y = min(max(0, y), max(0, image.height - h))
    return x, y, x + w, y + h


def _overlaps(a: Box, b: Box) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _mark_box(d: Detection, w: float, h: float, image: Image.Image, taken: Sequence[Box]) -> Box:
    """番号の札を置く場所。物体が札より十分大きければ物体の上（重心）。小さい物体は、札で隠れないように
    すぐ外（上 → 下 → 左 → 右のうち、画像に収まり、ほかの札と重ならない最初の場所）。"""
    x1, y1, x2, y2 = d.bbox
    cx, cy = mark_position(d)
    gap = max(2, h / 6)
    candidates = []
    if w <= (x2 - x1) * 0.5 and h <= (y2 - y1) * 0.5:
        candidates.append((cx - w / 2, cy - h / 2))
    # 外に置くときは、物体に沿う向きには画像の中へずらす（端の物体でも置けるように）
    ax = min(max(0, (x1 + x2) / 2 - w / 2), max(0, image.width - w))
    ay = min(max(0, (y1 + y2) / 2 - h / 2), max(0, image.height - h))
    candidates += [(ax, y1 - h - gap), (ax, y2 + gap), (x1 - w - gap, ay), (x2 + gap, ay)]
    for x, y in candidates:
        box = (x, y, x + w, y + h)
        if x >= 0 and y >= 0 and x + w <= image.width and y + h <= image.height and not any(_overlaps(box, t) for t in taken):
            return box
    return _clamp(*candidates[0], w, h, image)


def draw_marks(image: Image.Image, detections: Sequence[Detection]) -> Image.Image:
    """Set-of-Mark 画像。物体は薄く塗るだけにして（材質が見えるように）、番号を物体の上か、小さい物体ならすぐ外に置く。
    札の枠は、その物体の輪郭と同じ色。"""
    out = _shade(image, detections, alpha=40)
    draw = ImageDraw.Draw(out)
    font = _font(out, 0.7)
    taken: list[Box] = []
    for d in detections:
        text = str(d.detection_id)
        w, h, _ = _tag_size(draw, text, font)
        box = _mark_box(d, w, h, out, taken)
        taken.append(box)
        _draw_tag(draw, text, box, font, fill=(0, 0, 0), outline=PALETTE[(d.detection_id - 1) % len(PALETTE)])
    return out


def draw_overlay(image: Image.Image, detections: Sequence[Detection]) -> Image.Image:
    """確認用の分割結果。マスク・矩形・「番号 クラス 確信度」（矩形の上。入らなければ矩形の中）。"""
    out = _shade(image, detections, alpha=110)
    draw = ImageDraw.Draw(out)
    width = max(2, round(min(image.size) / 300))
    font = _font(out, 0.6)
    for d in detections:
        color = PALETTE[(d.detection_id - 1) % len(PALETTE)]
        draw.rectangle(d.bbox, outline=color, width=width)
        text = f"{d.detection_id} {d.cls} {d.confidence:.2f}"
        w, h, _ = _tag_size(draw, text, font)
        y = d.bbox[1] - h if d.bbox[1] - h >= 0 else d.bbox[1]
        _draw_tag(draw, text, _clamp(d.bbox[0], y, w, h, out), font, fill=color, outline=color)
    return out


def scale_detections(detections: Sequence[Detection], factor: float) -> list[Detection]:
    """画像を factor 倍にしたときの検出（描くためだけに使う）。"""
    return [d.model_copy(update={"bbox": [v * factor for v in d.bbox],
                                 "mask": [[x * factor, y * factor] for x, y in d.mask]}) for d in detections]
