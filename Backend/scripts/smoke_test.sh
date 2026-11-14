#!/usr/bin/env bash
# 起動中のコンテナに対して、MoveIt と腕の指令ノードが動くかを確認する
# 使い方: bash scripts/smoke_test.sh            (先に docker compose up しておくこと)
#         CONTAINER=別名 bash scripts/smoke_test.sh
# 確認内容: 必要なノードの存在 → /coground/arm/goal_joints で計画 → execute → /unity/joint_states に反映
set -euo pipefail

CONTAINER="${CONTAINER:-fetch_sim}"

docker exec -i "$CONTAINER" bash -s <<'IN'
set -eo pipefail
source /opt/fetch_ws/devel/setup.bash

echo "== ノード"
nodes=$(rosnode list)
for n in /move_group /unity_endpoint /coground_arm_command_server; do
  if grep -qx "$n" <<<"$nodes"; then echo "  OK  $n"; else echo "  NG  $n"; exit 1; fi
done

python3 - <<'PY'
import sys, rospy
from sensor_msgs.msg import JointState
from std_msgs.msg import Empty, String

rospy.init_node("coground_smoke_test", anonymous=True)
statuses = []
rospy.Subscriber("/coground/arm/status", String, lambda m: statuses.append(m.data))
goal = rospy.Publisher("/coground/arm/goal_joints", JointState, queue_size=1)
execute = rospy.Publisher("/coground/arm/execute", Empty, queue_size=1)
rospy.sleep(1.0)

def wait_for(prefixes, timeout):
    end = rospy.Time.now() + rospy.Duration(timeout)
    while rospy.Time.now() < end and not rospy.is_shutdown():
        for s in statuses:
            if s.split(":")[0] in prefixes:
                statuses.clear()
                return s
        rospy.sleep(0.1)
    return None

# 現在値から肩だけ少し回した姿勢を目標にする
cur = rospy.wait_for_message("/joint_states", JointState, timeout=5)
pan = dict(zip(cur.name, cur.position))["shoulder_pan_joint"]
target = 0.5 if pan < 0.25 else 0.0
statuses.clear()
goal.publish(JointState(name=["shoulder_pan_joint"], position=[target]))
s = wait_for({"planned", "plan_failed", "rejected", "succeeded"}, 15)
print("== 計画:", s)
if not s or not s.startswith(("planned", "succeeded")):
    sys.exit(1)
if s.startswith("planned"):
    execute.publish(Empty())
    s = wait_for({"succeeded", "exec_failed", "rejected"}, 30)
    print("== 実行:", s)
    if not s or not s.startswith("succeeded"):
        sys.exit(1)

rospy.sleep(0.5)
js = rospy.wait_for_message("/unity/joint_states", JointState, timeout=5)
got = dict(zip(js.name, js.position))["shoulder_pan_joint"]
print(f"== /unity/joint_states shoulder_pan_joint = {got:.3f} (目標 {target:.3f})")
sys.exit(0 if abs(got - target) < 0.05 else 1)
PY
echo "== すべて OK"
IN
