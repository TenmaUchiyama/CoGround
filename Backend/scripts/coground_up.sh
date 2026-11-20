#!/usr/bin/env bash
# make coground の中身: CoGround のデモ一式 (MoveIt + 台車のナビゲーション) を起動し、揃ったか確かめる。
#   腕     : MoveIt (疑似実行) + /coground/arm/*, /coground/pick_place/*
#   台車   : fake_base_driver (cmd_vel を積分) + move_base + /coground/base/*   … どちらも ROS 側
#   Unity  : 目標を置いて送り、ROS から届く経路・台車の位置・関節角を表示するだけ
#   通信   : ROS-TCP-Endpoint :10000
# 1. Gazebo なし + NAV=true の構成でコンテナを起動 (起動済みで同じ構成ならそのまま。別の構成なら作り直される)
# 2. move_group / move_base と必要なノードが揃うまで待つ
# 3. Unity (NavSim) がつながっているか (地図が届いているか) を表示する (つながっていなくても失敗にしない)
# 既定で操作用の RViz も開く (RVIZ=false で開かない。画面のある環境のみ)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../docker/fetch_sim"
CONTAINER=fetch_sim
IMAGE=coground/fetch-sim:noetic

# 0. 自前のノード (CMakeLists.txt の catkin_install_python) がイメージに入っているか確かめ、足りなければ作り直す。
#    ros_pkgs はコンテナにマウントされるが、ノードの「追加」は catkin_make (= docker compose build) しないと roslaunch が見つけられない
want=$(sed -n '/catkin_install_python(/,/)/p' ros_pkgs/coground_control/CMakeLists.txt | grep -o 'scripts/[A-Za-z0-9_]*\.py' | sed 's#scripts/##' | sort)
have=$(docker run --rm --entrypoint ls "$IMAGE" /opt/fetch_ws/devel/lib/coground_control 2>/dev/null | sort || true)
missing=$(comm -23 <(echo "$want") <(echo "$have"))
if [ -n "$missing" ]; then
  echo "イメージに入っていないノードがあるので作り直します: $(echo $missing)"
  docker compose build "$CONTAINER"
fi

GAZEBO=false GAZEBO_GUI=false MOVEIT=true RVIZ=false AUTO_EXECUTE=false NAV=true docker compose up -d "$CONTAINER"

echo "MoveIt (move_group) の起動を待っています..."
if ! docker exec "$CONTAINER" bash -c 'source /opt/fetch_ws/devel/setup.bash; for i in $(seq 90); do rosservice list 2>/dev/null | grep -q "^/plan_kinematic_path$" && exit 0; sleep 1; done; exit 1'; then
  echo "MoveIt が 90 秒以内に起動しませんでした。'make logs' でログを確認してください" >&2
  exit 1
fi

docker exec -i "$CONTAINER" bash -s <<'IN'
source /opt/fetch_ws/devel/setup.bash
ok=1
# 指令ノードは move_group の後に立ち上がるので少し待つ
for i in $(seq 20); do
  nodes=$(rosnode list 2>/dev/null)
  grep -qx /coground_pick_place_server <<<"$nodes" && timeout 3 rostopic echo -n 1 /coground/base/status 2>/dev/null | grep -q ready && break
  sleep 2
done
echo "== ノード"
check() { if grep -qx "$1" <<<"$nodes"; then echo "  OK  $1  ($2)"; else echo "  NG  $1  ($2)"; ok=0; fi; }
check /move_group                   "MoveIt"
check /coground_arm_command_server  "腕の Plan / Execute"
check /coground_pick_place_server   "pick & place"
check /coground_scene_sync          "Unity の箱 -> Planning Scene"
check /coground_fake_base_driver    "台車 (cmd_vel を積分 -> TF / odom / /unity/base_pose)"
check /move_base                    "台車の計画・実行"
check /coground_base_command_server "台車の指令 /coground/base/*"
check /unity_endpoint               "Unity 通信 :10000"
echo "  台車の状態: $(timeout 3 rostopic echo -n 1 /coground/base/status 2>/dev/null | sed -n 's/^data: //p')"

echo "== Unity"
if timeout 3 rostopic echo -n 1 /coground/nav/map_unity >/dev/null 2>&1; then
  echo "  OK  Unity の地図 (/coground/nav/map_unity) が届いている"
else
  echo "  --  Unity の地図は未着 (NavSim を Play すると届く。それまでは障害物なしの地図で計画する)"
fi
[ "$ok" = 1 ] || { echo "足りないノードがあります。'make logs' を確認してください" >&2; exit 1; }
IN

case "${RVIZ:-true}" in 0|false|FALSE|no) RVIZ_ON=0 ;; *) RVIZ_ON=1 ;; esac
if [ "$RVIZ_ON" = 1 ]; then
  bash "$SCRIPT_DIR/allow_x.sh"
  docker exec -d "$CONTAINER" bash -c "roslaunch coground_vr_bridge rviz.launch frame:=world"
  echo "RViz (world 基準) を開きました"
fi

cat <<'MSG'
起動しました。Unity で Assets/Main/Scene/NavSim.unity を Play:
  - 右上 Navigation パネル: 目標を置く → (ROS が計画) → Execute (ROS の move_base が動かす)
  - 左上 MoveIt パネル    : 腕の Plan / Execute、Pick & Place
確認: make test-moveit (腕) / make test-nav (台車。Unity なしでも可) / make test (両方)
MSG
