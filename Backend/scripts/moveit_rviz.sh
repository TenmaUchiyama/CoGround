#!/usr/bin/env bash
# make moveit の中身: MoveIt を起動し、操作用の RViz を開く。
#   1. コンテナを起動 (起動済みならそのまま。MoveIt は既定で起動する)
#   2. move_group が立ち上がるまで待つ
#   3. CoGround の RViz がまだ開いていなければ開く (FRAME=odom で odom 基準。既定は world)
# 何度実行しても MoveIt は再起動しない。
set -euo pipefail
cd "$(dirname "$0")/../docker/fetch_sim"
FRAME="${FRAME:-world}"

docker compose up -d fetch_sim

echo "MoveIt (move_group) の起動を待っています..."
if ! docker exec fetch_sim bash -c 'for i in $(seq 90); do rosservice list 2>/dev/null | grep -q "^/plan_kinematic_path$" && exit 0; sleep 1; done; exit 1'; then
  echo "MoveIt が 90 秒以内に起動しませんでした。'make logs' でログを確認してください (MOVEIT=false で起動していないかも)" >&2
  exit 1
fi

if docker exec fetch_sim pgrep -f "coground_vr_bridge/rviz/${FRAME}.rviz" >/dev/null; then
  echo "RViz (${FRAME} 基準) はすでに開いています"
else
  docker exec -d fetch_sim bash -c "roslaunch coground_vr_bridge rviz.launch frame:=${FRAME}"
  echo "RViz (${FRAME} 基準) を開きました"
fi
cat <<'MSG'
RViz での操作:
  - オレンジの手先 (目標) をドラッグ → 左下 MotionPlanning パネルの Planning タブで Plan → Execute
    (Plan & Execute で一度に。Gazebo なしなら Unity のロボットも同じ動きをする)
  - 目標の姿勢は Planning タブの Goal State (random valid / current など) でも選べる
  - 計画グループは Planning Group で切り替え (arm / arm_with_torso / gripper)
MSG
