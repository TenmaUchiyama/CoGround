"""実機 Fetch の確認ツール。

core.py      確認項目 (Check) の登録・実行・結果の型
ros_util.py  トピックの周期を測る等、確認項目から使う ROS の小道具
checks/      確認項目そのもの (import すると core.REGISTRY に登録される)
cli.py       コマンドライン (`fetch_check list` / `fetch_check run ...`)
"""
