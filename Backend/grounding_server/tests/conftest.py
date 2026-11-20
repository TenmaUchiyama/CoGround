"""テスト全体の設定。"""

import os

# make test はコンテナ（compose.yaml の環境変数つき）で動くので、本物のルールバンク（data/rule_bank.json）を
# 読み書きしないように切る。ルールバンクのテストは、自分で一時ファイルを渡す（test_rulebank.py）
os.environ["COGROUND_RULE_BANK"] = ""

# 依頼のあとの自動の動作計画は、既存のテストの流れ（依頼 → 手で motion.plan）を変えるので切る。
# 自動のテストは Services(auto_motion_plan=True) で作る（test_auto_motion_plan.py）
os.environ["COGROUND_AUTO_MOTION_PLAN"] = "0"

# 物体の記憶（data/object_memory.json）と run の記録（logs/perception）も、本物を読み書きしない。
# perception のテストは、自分で一時フォルダを渡す（test_perception.py）
os.environ["COGROUND_OBJECT_MEMORY"] = ""
os.environ["COGROUND_PERCEPTION_RUNS"] = ""
os.environ["COGROUND_PERCEPTION_SEQUENCES"] = ""
os.environ["COGROUND_OBJECT_TRACKS"] = ""

# detect_app を作るテストで、本物の YOLOE-seg を読み込まない（test_segmentation.py は代役のモデルを差し込む）
os.environ["COGROUND_SEGMENT_ENABLED"] = "0"
