"""物体のカテゴリ表と属性の語彙（机の上の片付けタスク）。

Unity は category だけ送ればよい。role と group が省略されていれば、サーバーがこの表から埋める。
表に無い category（検出器が出した未知の物体）も受け付ける。その場合は role = item、group = other。

カテゴリを足すときは、Unity の CoGroundCategory（CoGroundSceneTypes.cs）にも同じ名前を足す。
"""

from __future__ import annotations

from typing import Literal

ObjectRole = Literal["item", "receptacle", "surface"]
"""item: ロボットが運ぶ物 / receptacle: 中に入れる場所（シンク、ごみ箱） / surface: 上に置く場所（机、棚）"""

ObjectGroup = Literal["dish", "cutlery", "trash", "receptacle", "surface", "other"]

# category -> (role, group)
CATEGORIES: dict[str, tuple[ObjectRole, ObjectGroup]] = {
    # 食器
    "plate": ("item", "dish"),
    "bowl": ("item", "dish"),
    "cup": ("item", "dish"),
    "mug": ("item", "dish"),
    "glass": ("item", "dish"),
    # カトラリー
    "fork": ("item", "cutlery"),
    "spoon": ("item", "cutlery"),
    "knife": ("item", "cutlery"),
    "chopsticks": ("item", "cutlery"),
    # ごみ
    "can": ("item", "trash"),
    "plastic_bottle": ("item", "trash"),
    "paper_cup": ("item", "trash"),
    "tissue": ("item", "trash"),
    "wrapper": ("item", "trash"),
    "food_waste": ("item", "trash"),
    # 入れる場所
    "sink": ("receptacle", "receptacle"),
    "trash_bin": ("receptacle", "receptacle"),
    "dish_rack": ("receptacle", "receptacle"),
    # 置く場所
    "table": ("surface", "surface"),
    "shelf": ("surface", "surface"),
}

# 属性の語彙（ルールの条件と VLM のプロンプトに使う）。値は検証しない（VLM の出力で scene.update 全体を落とさないため）。
ATTRIBUTES: dict[str, str] = {
    "material": "glass | ceramic | plastic | metal | paper | wood",
    "fragile": "bool（割れ物か）",
    "dirty": "bool（汚れているか）",
    "contents": "empty | liquid | food（中に何が残っているか）",
    "waste_type": "burnable | plastic | can | bottle（ごみの分別。ごみ箱ではどの分別を受け付けるか）",
}


def lookup(category: str) -> tuple[ObjectRole, ObjectGroup]:
    return CATEGORIES.get(category, ("item", "other"))
