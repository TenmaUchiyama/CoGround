#!/usr/bin/env python3
"""台車のナビゲーションの指令ノード (arm_command_server の台車版)。計画・実行は move_base が行う。

Unity は目標を置いて送り、返ってきた経路 (planned_path) と台車の位置 (/unity/base_pose) を表示するだけ。
シミュレーション (fake_base_driver) でも Gazebo / 実機でも同じトピックで使える。

入力:
  /coground/base/goal_pose   geometry_msgs/PoseStamped  目標 (frame world か ~global_frame)。受けたら計画だけする (make_plan)
  /coground/base/execute     std_msgs/Empty             直前の目標へ動く (計画し直してから move_base に送る)
  /coground/base/stop        std_msgs/Empty             止める (move_base の goal を取り消し、速度 0 を送る)
  /coground/nav/map_unity    nav_msgs/OccupancyGrid     Unity (NavMapPublisher) が作った地図
  /coground/nav/keepout_zones  std_msgs/String (JSON)   進入禁止ゾーン (家庭ルール)。全体を置き換える
                                 {"seq": 3, "zones": [{"id": "zone_play", "polygon": [[x, y], ...]}]}  (world、空のリストで消す)
  /coground/base/hold        std_msgs/String (JSON)     {"hold": true | false}  hold の間は動かない (実行中なら止める)
出力 (latch):
  /coground/base/planned_path  nav_msgs/Path    計画した経路 (失敗で空)。実行時は move_base が実際に使う経路で上書きする
  /coground/base/status        std_msgs/String  ready / planning / planned / plan_failed / executing / succeeded /
                                                exec_failed / stopped / rejected (+ ": 詳細")
  /coground/nav/map            nav_msgs/OccupancyGrid  move_base の costmap が読む地図。
                                                起動時は何もない地図を出し、Unity から地図が届いたらそれに替える
  /coground/nav/keepout        nav_msgs/OccupancyGrid  進入禁止ゾーンを塗った地図 (costmap の keepout_layer が読む)。
                                                大きさ・解像度・原点は /coground/nav/map と必ず同じにする
                                                (違うと StaticLayer が costmap 全体の大きさを取り合う)
  /coground/nav/keepout_state  std_msgs/String (JSON)  {"seq", "ids": [...]}  いま塗ってあるゾーン (keepout を出したあとに出す)

move_base は planner_frequency 0 (目標を受けたときに 1 回だけ計画) で使う前提。
そうすると make_plan で見せた経路と、実行時の経路が同じになる (地図と台車の位置が変わっていなければ)。
pick & place / 腕の実行中は動かない (rejected)。
"""
import json
import math
import threading

import actionlib
import numpy as np
import rospy
import tf2_geometry_msgs  # noqa: F401  PoseStamped を tf2 で変換できるようにする
import tf2_ros
from actionlib_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, Twist
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from nav_msgs.msg import OccupancyGrid, Path
from nav_msgs.srv import GetPlan, GetPlanRequest
from std_msgs.msg import Empty, String

# pick_place / arm の status のうち「動いていない」もの
IDLE_STATES = {"ready", "succeeded", "failed", "rejected", "planned", "plan_failed", "exec_failed", "stopped", ""}


class BaseCommandServer:
    def __init__(self):
        self.frame = rospy.get_param("~global_frame", "world")
        self.robot_frame = rospy.get_param("~robot_frame", "base_link")
        ns = rospy.get_param("~move_base_ns", "move_base").rstrip("/")
        self.cmd_vel_topic = rospy.get_param("~cmd_vel_topic", "/coground/base/cmd_vel")

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

        self.lock = threading.Lock()
        self.goal = None          # 直前の目標 (PoseStamped, global_frame)
        self.executing = False
        self.stop_requested = False
        self.other_status = {"pick_place": "", "arm": ""}

        self.status_pub = rospy.Publisher("/coground/base/status", String, queue_size=10, latch=True)
        self.path_pub = rospy.Publisher("/coground/base/planned_path", Path, queue_size=1, latch=True)
        self.map_pub = rospy.Publisher("/coground/nav/map", OccupancyGrid, queue_size=1, latch=True)
        self.keepout_pub = rospy.Publisher("/coground/nav/keepout", OccupancyGrid, queue_size=1, latch=True)
        self.keepout_state_pub = rospy.Publisher("/coground/nav/keepout_state", String, queue_size=1, latch=True)
        self.keepout_zones = []   # [{"id", "polygon": [[x, y], ...]}] (world)
        self.keepout_seq = 0
        self.map_info = None      # いま出している地図の大きさ・解像度・原点
        self.hold = False
        self.cmd_pub = rospy.Publisher(self.cmd_vel_topic, Twist, queue_size=1)
        self.publish_status("waiting", "waiting for move_base to start")

        # move_base は地図が届くまで起動しないので、まず何もない地図を出す
        self.unity_map = False
        self.publish_map(self.empty_map())
        rospy.Subscriber("/coground/nav/map_unity", OccupancyGrid, self.on_unity_map, queue_size=1)
        rospy.Subscriber("/coground/nav/keepout_zones", String, self.on_keepout_zones, queue_size=5)
        rospy.Subscriber("/coground/base/hold", String, self.on_hold, queue_size=5)

        self.make_plan = rospy.ServiceProxy(ns + "/make_plan", GetPlan)
        self.client = actionlib.SimpleActionClient(ns, MoveBaseAction)
        rospy.Subscriber(ns + "/NavfnROS/plan", Path, self.on_move_base_plan, queue_size=1)
        rospy.Subscriber("/coground/pick_place/status", String, lambda m: self.on_other("pick_place", m), queue_size=10)
        rospy.Subscriber("/coground/arm/status", String, lambda m: self.on_other("arm", m), queue_size=10)

        rospy.Subscriber("/coground/base/goal_pose", PoseStamped, self.on_goal, queue_size=1)
        rospy.Subscriber("/coground/base/execute", Empty, self.on_execute, queue_size=1)
        rospy.Subscriber("/coground/base/stop", Empty, self.on_stop, queue_size=1)
        rospy.Subscriber("/coground/system/reset", String, self.on_reset, queue_size=1)

        threading.Thread(target=self.wait_for_move_base, daemon=True).start()

    # ---- 共通 ----
    def publish_status(self, status, detail=""):
        text = f"{status}: {detail}" if detail else status
        self.status_pub.publish(String(data=text))
        rospy.loginfo("[base] %s", text)

    def wait_for_move_base(self):
        rospy.wait_for_service(self.make_plan.resolved_name)
        self.client.wait_for_server()
        rospy.loginfo("base_command_server ready: frame=%s robot=%s", self.frame, self.robot_frame)
        self.publish_status("ready")

    def empty_map(self):
        size = float(rospy.get_param("~default_map_size", 40.0))
        res = float(rospy.get_param("~default_map_resolution", 0.1))
        n = int(round(size / res))
        m = OccupancyGrid()
        m.header.stamp = rospy.Time.now()
        m.header.frame_id = self.frame
        m.info.resolution = res
        m.info.width = m.info.height = n
        m.info.origin.position.x = m.info.origin.position.y = -size / 2.0
        m.info.origin.orientation.w = 1.0
        m.data = [0] * (n * n)
        return m

    def publish_map(self, msg):
        """地図を出し、同じ大きさの keepout も出し直す (keepout_layer は最初の地図が届くまで move_base を待たせる)"""
        self.map_info = msg.info
        self.map_pub.publish(msg)
        self.publish_keepout()

    def publish_keepout(self):
        info = self.map_info
        if info is None:
            return
        grid = np.zeros((info.height, info.width), dtype=np.int8)
        res, o = info.resolution, info.origin.position
        for zone in self.keepout_zones:
            poly = np.array(zone["polygon"], dtype=float)
            # 多角形の外接矩形に入るセルだけ調べる (セルの中心が多角形の中なら塗る)
            i0 = max(0, int(math.floor((poly[:, 0].min() - o.x) / res)))
            i1 = min(info.width, int(math.ceil((poly[:, 0].max() - o.x) / res)) + 1)
            j0 = max(0, int(math.floor((poly[:, 1].min() - o.y) / res)))
            j1 = min(info.height, int(math.ceil((poly[:, 1].max() - o.y) / res)) + 1)
            if i0 >= i1 or j0 >= j1:
                continue
            xs = o.x + (np.arange(i0, i1) + 0.5) * res
            ys = o.y + (np.arange(j0, j1) + 0.5) * res
            gx, gy = np.meshgrid(xs, ys)
            inside = np.zeros(gx.shape, dtype=bool)
            n = len(poly)
            for k in range(n):  # 偶奇則
                (x1, y1), (x2, y2) = poly[k], poly[(k + 1) % n]
                if y1 == y2:
                    continue
                cross = ((y1 > gy) != (y2 > gy)) & (gx < (x2 - x1) * (gy - y1) / (y2 - y1) + x1)
                inside ^= cross
            grid[j0:j1, i0:i1][inside] = 100
        m = OccupancyGrid()
        m.header.stamp = rospy.Time.now()
        m.header.frame_id = self.frame
        m.info = info
        m.data = grid.flatten().tolist()
        self.keepout_pub.publish(m)
        self.keepout_state_pub.publish(String(data=json.dumps(
            {"seq": self.keepout_seq, "ids": [z["id"] for z in self.keepout_zones]}, ensure_ascii=False)))

    def on_keepout_zones(self, msg):
        try:
            data = json.loads(msg.data or "{}")
            zones = []
            for z in data.get("zones") or []:
                polygon = [[float(p[0]), float(p[1])] for p in z["polygon"]]
                if len(polygon) < 3:
                    raise ValueError("polygon needs 3 or more points")
                zones.append({"id": str(z.get("id", "")), "polygon": polygon})
            seq = int(data.get("seq", 0))
        except (ValueError, KeyError, TypeError, IndexError) as e:
            rospy.logwarn("[base] keepout_zones の形式が不正: %s", e)
            return
        self.keepout_zones, self.keepout_seq = zones, seq
        self.publish_keepout()
        rospy.loginfo("[base] 進入禁止ゾーン: %s", [z["id"] for z in zones] or "なし")

    def on_hold(self, msg):
        try:
            hold = bool(json.loads(msg.data or "{}").get("hold"))
        except (ValueError, AttributeError):
            return
        self.hold = hold
        if hold and self.executing:
            self.on_stop(None)

    def on_unity_map(self, msg):
        msg.header.frame_id = msg.header.frame_id or self.frame
        self.publish_map(msg)
        if not self.unity_map:
            rospy.loginfo("Unity の地図を使う: %dx%d, %.2f m/セル", msg.info.width, msg.info.height, msg.info.resolution)
        self.unity_map = True

    def on_other(self, name, msg):
        self.other_status[name] = msg.data.split(":")[0].strip()

    def busy_reason(self):
        for name, state in self.other_status.items():
            if state not in IDLE_STATES:
                return f"{name} is busy ({state})"
        return None

    def current_pose(self):
        t = self.tf_buffer.lookup_transform(self.frame, self.robot_frame, rospy.Time(0), rospy.Duration(1.0))
        p = PoseStamped()
        p.header.frame_id = self.frame
        p.header.stamp = rospy.Time.now()
        p.pose.position.x = t.transform.translation.x
        p.pose.position.y = t.transform.translation.y
        p.pose.position.z = t.transform.translation.z
        p.pose.orientation = t.transform.rotation
        return p

    def plan(self, goal):
        """今の位置から goal までの経路 (nav_msgs/Path)。失敗したら None と理由"""
        try:
            start = self.current_pose()
        except Exception as e:
            return None, f"can't get the base pose: {e}"
        req = GetPlanRequest(start=start, goal=goal, tolerance=0.0)
        try:
            res = self.make_plan(req)
        except rospy.ServiceException as e:
            return None, f"make_plan failed: {e}"
        if not res.plan.poses:
            return None, "no passable path to the goal (inside an obstacle, too close, or outside the map)"
        res.plan.header.frame_id = self.frame
        return res.plan, None

    @staticmethod
    def length(path):
        ps = [p.pose.position for p in path.poses]
        return sum(math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(ps, ps[1:]))

    # ---- コールバック ----
    def on_goal(self, msg):
        if self.executing:
            self.publish_status("rejected", "executing (stop first)")
            return
        if not self.lock.acquire(blocking=False):
            self.publish_status("rejected", "busy")
            return
        try:
            try:
                goal = self.tf_buffer.transform(msg, self.frame, rospy.Duration(1.0)) \
                    if msg.header.frame_id and msg.header.frame_id != self.frame else msg
            except Exception as e:
                self.publish_status("rejected", f"can't transform the goal to {self.frame}: {e}")
                return
            goal.header.frame_id = self.frame
            goal.pose.position.z = 0.0
            self.publish_status("planning")
            path, error = self.plan(goal)
            if path is None:
                self.goal = None
                self.path_pub.publish(Path(header=goal.header))
                self.publish_status("plan_failed", error)
                return
            self.goal = goal
            self.path_pub.publish(path)
            self.publish_status("planned", f"{self.length(path):.2f} m, {len(path.poses)} points")
        finally:
            self.lock.release()

    def on_execute(self, _msg):
        if self.executing:
            return
        if self.goal is None:
            self.publish_status("rejected", "no plan")
            return
        busy = self.busy_reason()
        if busy:
            self.publish_status("rejected", busy)
            return
        if self.hold:
            self.publish_status("rejected", "on hold (the base is stopped by a household rule)")
            return
        if not self.client.wait_for_server(rospy.Duration(1.0)):
            self.publish_status("rejected", "no move_base")
            return
        with self.lock:
            # 計画後に台車が動いていても見せる経路が実行と一致するよう、今の位置から計画し直して出す
            path, error = self.plan(self.goal)
            if path is None:
                self.publish_status("exec_failed", error)
                return
            self.path_pub.publish(path)
            self.executing = True
            self.stop_requested = False
            self.publish_status("executing", f"{self.length(path):.2f} m")
            goal = MoveBaseGoal(target_pose=self.goal)
            goal.target_pose.header.stamp = rospy.Time.now()
            self.client.send_goal(goal, done_cb=self.on_done)

    def on_move_base_plan(self, msg):
        # 実行中は move_base が実際に使っている経路を見せる
        if self.executing and msg.poses:
            msg.header.frame_id = msg.header.frame_id or self.frame
            self.path_pub.publish(msg)

    def on_done(self, state, _result):
        self.executing = False
        if state == GoalStatus.SUCCEEDED:
            self.goal = None
            self.publish_status("succeeded")
        elif state in (GoalStatus.PREEMPTED, GoalStatus.RECALLED) or self.stop_requested:
            self.publish_status("stopped")
        else:
            names = {GoalStatus.ABORTED: "aborted (stuck / path blocked)", GoalStatus.REJECTED: "rejected"}
            self.publish_status("exec_failed", f"move_base: {names.get(state, state)}")

    def on_reset(self, _msg):
        """Web UI の「まっさら」: 動いていれば止め、直前の目標と latch している古い経路・状態を消す"""
        if self.executing:
            self.on_stop(None)
        self.goal = None
        empty = Path()
        empty.header.frame_id = self.frame
        empty.header.stamp = rospy.Time.now()
        self.path_pub.publish(empty)
        try:
            self.make_plan.wait_for_service(0.2)
            self.publish_status("ready")
        except rospy.ROSException:
            self.publish_status("waiting", "waiting for move_base to start")

    def on_stop(self, _msg):
        self.stop_requested = True
        if self.executing:
            self.client.cancel_all_goals()
        # 局所計画器が最後に出した速度で動き続けないように止める
        for _ in range(3):
            self.cmd_pub.publish(Twist())
            rospy.sleep(0.05)
        if not self.executing:
            self.publish_status("stopped")


if __name__ == "__main__":
    rospy.init_node("coground_base_command_server")
    BaseCommandServer()
    rospy.spin()
