#!/usr/bin/env python3
"""腕の軌道を「手先の通り道」として ROS 側で計算して出すノード (RViz の Trail 相当)。

Unity では何もしなくてよい。結果は RViz で見るか、標準メッセージなので他のノード / Unity からも購読できる。

計画した軌道 (planned):
  /coground/arm/planned_trajectory (JointTrajectory) を受けたら、各点の関節角を MoveIt の /compute_fk に
  渡して手先 (~tip_link) の位置を求める。点の間は関節空間で補間してから FK するので、線は実際の通り道に沿う。
  計画時の base_link の位置で ~frame (world) に変換して固定する。空の軌道 (計画失敗) を受けたら消す。

実際に動いた軌跡 (executed):
  /coground/arm/status が executing の間、TF ~frame -> ~tip_link を ~record_rate で記録する。
  succeeded / exec_failed / stopped で記録を止め、次の executing まで残す。

出力 (すべて latch):
  /coground/arm/planned_path    nav_msgs/Path                 計画した手先の通り道
  /coground/arm/executed_path   nav_msgs/Path                 実際に動いた手先の通り道
  /coground/arm/path_markers    visualization_msgs/MarkerArray 上の 2 本の線 (ns: planned 緑 / executed 橙) と始点・終点
"""
import math

import rospy
import tf2_geometry_msgs
import tf2_ros
from geometry_msgs.msg import Point, PoseStamped
from moveit_msgs.msg import RobotState
from moveit_msgs.srv import GetPositionFK, GetPositionFKRequest
from nav_msgs.msg import Path
from sensor_msgs.msg import JointState
from std_msgs.msg import ColorRGBA, String
from trajectory_msgs.msg import JointTrajectory
from visualization_msgs.msg import Marker, MarkerArray

PLANNED_COLOR = ColorRGBA(0.2, 1.0, 0.3, 0.9)
EXECUTED_COLOR = ColorRGBA(1.0, 0.55, 0.0, 0.9)


class TrajectoryPath:
    def __init__(self):
        self.frame = rospy.get_param("~frame", "world")
        self.base_frame = rospy.get_param("~base_frame", "base_link")
        self.tip_link = rospy.get_param("~tip_link", "gripper_link")
        # 関節空間での補間の細かさ [rad]。点の間を最大この角度ごとに分けて FK する
        self.max_joint_step = float(rospy.get_param("~max_joint_step", 0.02))
        self.max_points = int(rospy.get_param("~max_points", 400))
        self.record_rate = float(rospy.get_param("~record_rate", 20.0))
        self.min_step = float(rospy.get_param("~min_step", 0.003))  # 実軌跡の間引き [m]
        self.line_width = float(rospy.get_param("~line_width", 0.01))

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

        self.joint_state = None
        self.planned = Path()
        self.executed = Path()
        self.recording = False

        self.planned_pub = rospy.Publisher("/coground/arm/planned_path", Path, queue_size=1, latch=True)
        self.executed_pub = rospy.Publisher("/coground/arm/executed_path", Path, queue_size=1, latch=True)
        self.marker_pub = rospy.Publisher("/coground/arm/path_markers", MarkerArray, queue_size=1, latch=True)

        rospy.loginfo("trajectory_path: waiting for /compute_fk")
        rospy.wait_for_service("/compute_fk")
        self.fk = rospy.ServiceProxy("/compute_fk", GetPositionFK, persistent=True)

        rospy.Subscriber("/joint_states", JointState, self.on_joint_states, queue_size=1)
        rospy.Subscriber("/coground/arm/planned_trajectory", JointTrajectory, self.on_trajectory, queue_size=1)
        rospy.Subscriber("/coground/arm/status", String, self.on_status, queue_size=10)
        rospy.Subscriber("/coground/system/reset", String, self.on_reset, queue_size=1)
        rospy.Timer(rospy.Duration(1.0 / self.record_rate), self.on_record_timer)
        rospy.loginfo("trajectory_path ready: tip=%s frame=%s", self.tip_link, self.frame)

    def on_reset(self, _msg):
        """Web UI の「まっさら」: latch している計画・実行の軌跡を消す"""
        self.recording = False
        self.planned = Path()
        self.planned.header.frame_id = self.frame
        self.executed = Path()
        self.executed.header.frame_id = self.frame
        self.publish()
        rospy.loginfo("[path] reset")

    # ---- 計画した軌道 ----
    def on_joint_states(self, msg):
        # 指だけの JointState が混ざる場合があるので、名前ごとに積み上げる
        if self.joint_state is None:
            self.joint_state = {}
        self.joint_state.update(zip(msg.name, msg.position))

    def interpolate(self, traj):
        """軌道の点を関節空間で補間した関節角のリストを返す。"""
        points = [list(p.positions) for p in traj.points]
        out = [points[0]]
        for a, b in zip(points, points[1:]):
            diff = max(abs(y - x) for x, y in zip(a, b))
            n = max(1, int(math.ceil(diff / self.max_joint_step)))
            for k in range(1, n + 1):
                t = k / n
                out.append([x + (y - x) * t for x, y in zip(a, b)])
        if len(out) > self.max_points:  # 長すぎる場合は等間隔に間引く (終点は必ず残す)
            step = len(out) / float(self.max_points - 1)
            out = [out[int(i * step)] for i in range(self.max_points - 1)] + [out[-1]]
        return out

    def on_trajectory(self, traj):
        if not traj.points:
            self.planned = Path()
            self.planned.header.frame_id = self.frame
            self.publish()
            rospy.loginfo("[path] planned path cleared")
            return
        try:
            to_frame = self.tf_buffer.lookup_transform(self.frame, self.base_frame, rospy.Time(0), rospy.Duration(1.0))
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
            rospy.logwarn("[path] TF %s -> %s: %s", self.frame, self.base_frame, e)
            return

        base = dict(self.joint_state or {})
        req = GetPositionFKRequest()
        req.header.frame_id = self.base_frame
        req.fk_link_names = [self.tip_link]
        path = Path()
        path.header.frame_id = self.frame
        path.header.stamp = rospy.Time.now()
        for positions in self.interpolate(traj):
            joints = dict(base)
            joints.update(zip(traj.joint_names, positions))
            req.robot_state = RobotState()
            req.robot_state.joint_state.name = list(joints.keys())
            req.robot_state.joint_state.position = list(joints.values())
            try:
                res = self.fk(req)
            except rospy.ServiceException as e:
                rospy.logwarn("[path] compute_fk failed: %s", e)
                self.fk = rospy.ServiceProxy("/compute_fk", GetPositionFK, persistent=True)
                return
            if res.error_code.val != 1 or not res.pose_stamped:
                rospy.logwarn("[path] compute_fk error_code=%d", res.error_code.val)
                return
            pose = tf2_geometry_msgs.do_transform_pose(res.pose_stamped[0], to_frame)
            pose.header = path.header
            path.poses.append(pose)
        self.planned = path
        self.publish()
        rospy.loginfo("[path] planned path: %d poses, %.3f m", len(path.poses), path_length(path))

    # ---- 実際に動いた軌跡 ----
    def on_status(self, msg):
        status = msg.data.split(":", 1)[0].strip()
        if status == "executing":
            self.executed = Path()
            self.executed.header.frame_id = self.frame
            self.executed.header.stamp = rospy.Time.now()
            self.recording = True
        elif self.recording and status in ("succeeded", "exec_failed", "stopped"):
            self.recording = False
            self.record_once()  # 止まった位置を最後の点にする
            self.publish()
            rospy.loginfo("[path] executed path: %d poses, %.3f m", len(self.executed.poses), path_length(self.executed))

    def on_record_timer(self, _event):
        if self.recording and self.record_once():
            self.publish()

    def record_once(self):
        try:
            t = self.tf_buffer.lookup_transform(self.frame, self.tip_link, rospy.Time(0))
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException):
            return False
        pose = PoseStamped()
        pose.header.frame_id = self.frame
        pose.header.stamp = t.header.stamp
        tr = t.transform.translation
        pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = tr.x, tr.y, tr.z
        pose.pose.orientation = t.transform.rotation
        if self.executed.poses and distance(self.executed.poses[-1], pose) < self.min_step:
            return False
        self.executed.poses.append(pose)
        return True

    # ---- 出力 ----
    def publish(self):
        self.planned_pub.publish(self.planned)
        self.executed_pub.publish(self.executed)
        markers = MarkerArray()
        markers.markers.append(Marker(action=Marker.DELETEALL))
        markers.markers += self.line_markers("planned", self.planned, PLANNED_COLOR)
        markers.markers += self.line_markers("executed", self.executed, EXECUTED_COLOR)
        self.marker_pub.publish(markers)

    def line_markers(self, ns, path, color):
        if len(path.poses) < 2:
            return []
        line = Marker()
        line.header.frame_id = self.frame
        line.header.stamp = rospy.Time.now()
        line.ns = ns
        line.id = 0
        line.type = Marker.LINE_STRIP
        line.action = Marker.ADD
        line.pose.orientation.w = 1.0
        line.scale.x = self.line_width
        line.color = color
        line.points = [Point(p.pose.position.x, p.pose.position.y, p.pose.position.z) for p in path.poses]
        ends = Marker()
        ends.header = line.header
        ends.ns = ns
        ends.id = 1
        ends.type = Marker.SPHERE_LIST
        ends.action = Marker.ADD
        ends.pose.orientation.w = 1.0
        ends.scale.x = ends.scale.y = ends.scale.z = self.line_width * 3
        ends.color = color
        ends.points = [line.points[0], line.points[-1]]
        return [line, ends]


def distance(a, b):
    pa, pb = a.pose.position, b.pose.position
    return math.sqrt((pa.x - pb.x) ** 2 + (pa.y - pb.y) ** 2 + (pa.z - pb.z) ** 2)


def path_length(path):
    return sum(distance(a, b) for a, b in zip(path.poses, path.poses[1:]))


if __name__ == "__main__":
    rospy.init_node("coground_trajectory_path")
    TrajectoryPath()
    rospy.spin()
