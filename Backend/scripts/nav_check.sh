#!/usr/bin/env bash
# make test-nav の中身: Unity ベースの台車ナビゲーションと ROS がつながっているかを確かめる。
# 台車の計画・実行は Unity (BaseNavigator) の中なので、ROS 側で確かめるのは「動いた位置が TF に反映されるか」。
# 先に make coground で起動し、Unity で NavSim を Play しておくこと。
#   1. /coground/robot/base_pose が届く (レート)
#   2. TF world -> base_link が base_pose と一致する (止まっている間に比べる)
#   WATCH=秒数 を付けると、その間 TF の台車の位置を 1 秒ごとに表示する (Unity で Execute して追従を見る)
set -euo pipefail
CONTAINER="${CONTAINER:-fetch_sim}"

docker exec -i -e WATCH="${WATCH:-0}" "$CONTAINER" bash -s <<'IN'
set -eo pipefail
source /opt/fetch_ws/devel/setup.bash
python3 - <<'PY'
import math, os, sys
import rospy, tf2_ros
from geometry_msgs.msg import PoseStamped

rospy.init_node("coground_nav_check", anonymous=True)
msgs = []
rospy.Subscriber("/coground/robot/base_pose", PoseStamped, lambda m: msgs.append((rospy.get_time(), m)))
buf = tf2_ros.Buffer()
tf2_ros.TransformListener(buf)

def yaw(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))

rospy.sleep(3.0)
if len(msgs) < 2:
    print("NG  /coground/robot/base_pose が届かない (Unity の NavSim を Play しているか、FetchBasePosePublisher があるか)")
    sys.exit(1)
rate = (len(msgs) - 1) / (msgs[-1][0] - msgs[0][0])
print(f"OK  /coground/robot/base_pose {rate:.1f} Hz")

# 止まっている間に比べる (動いていると最大 1 周期ずれる)
for attempt in range(20):
    a, b = msgs[-2][1].pose, msgs[-1][1].pose
    moving = math.dist((a.position.x, a.position.y), (b.position.x, b.position.y)) > 1e-3
    if not moving:
        break
    rospy.sleep(0.5)
else:
    print("--  台車が動き続けているので一致の確認は省略")
    moving = True

if not moving:
    p = msgs[-1][1].pose
    rospy.sleep(0.3)
    try:
        t = buf.lookup_transform("world", "base_link", rospy.Time(0), rospy.Duration(2.0)).transform
    except Exception as e:
        print(f"NG  TF world -> base_link が取れない: {e}")
        sys.exit(1)
    d = math.dist((p.position.x, p.position.y), (t.translation.x, t.translation.y))
    dyaw = abs(math.degrees(math.atan2(math.sin(yaw(p.orientation) - yaw(t.rotation)),
                                       math.cos(yaw(p.orientation) - yaw(t.rotation)))))
    ok = d < 0.02 and dyaw < 2.0
    print(f"{'OK' if ok else 'NG'}  TF world -> base_link と base_pose の差: 位置 {d * 100:.1f} cm, 向き {dyaw:.1f}°"
          f"  (台車 x={p.position.x:.2f} y={p.position.y:.2f} yaw={math.degrees(yaw(p.orientation)):.0f}°)")
    if not ok:
        sys.exit(1)

watch = int(os.environ.get("WATCH", "0"))
for _ in range(watch):
    rospy.sleep(1.0)
    t = buf.lookup_transform("world", "base_link", rospy.Time(0), rospy.Duration(1.0)).transform
    print(f"    TF base_link: x={t.translation.x:.2f} y={t.translation.y:.2f} yaw={math.degrees(yaw(t.rotation)):.0f}°")
PY
echo "== すべて OK"
IN
