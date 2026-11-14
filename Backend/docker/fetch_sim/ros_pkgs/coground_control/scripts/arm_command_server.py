#!/usr/bin/env python3
"""Fetch の腕・グリッパーを MoveIt で動かす指令ノード。

Unity (ROS-TCP-Connector) から標準メッセージだけで使えるようにしてある。
自前の .msg / .srv を作らないので、Unity 側でメッセージ生成をしなくてよい。

入力 (すべて /coground/ 以下。MoveIt を root 名前空間で探すため、ノード自体は root に置く):
  arm/goal_pose     geometry_msgs/PoseStamped  手先 (wrist_roll_link) の目標。frame_id は world (Unity の World) か base_link
  arm/goal_joints   sensor_msgs/JointState     関節角の目標 (name と position だけ使う)
  arm/execute       std_msgs/Empty             直前の計画を実行
  arm/stop          std_msgs/Empty             実行中の動作を止める
  gripper/command   std_msgs/Float64           指の開き幅 [m] (0.0 = 閉, 0.1 = 全開)

出力:
  arm/planned_trajectory  trajectory_msgs/JointTrajectory  計画結果 (Unity でのプレビュー用, latch)
  arm/status              std_msgs/String                   状態 (下の STATUS_* のどれか + ": 詳細")

~auto_execute が true なら、計画に成功した時点で実行まで行う。
goal_pose は TF で planning frame (base_link) に変換してから MoveIt に渡す。
"""
import sys
import threading

import moveit_commander
import rospy
import tf2_geometry_msgs  # noqa: F401  PoseStamped を tf2 で変換できるようにする
import tf2_ros
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState
from std_msgs.msg import Empty, Float64, String
from trajectory_msgs.msg import JointTrajectory

STATUS_PLANNING = "planning"
STATUS_PLANNED = "planned"
STATUS_PLAN_FAILED = "plan_failed"
STATUS_EXECUTING = "executing"
STATUS_SUCCEEDED = "succeeded"
STATUS_EXEC_FAILED = "exec_failed"
STATUS_STOPPED = "stopped"
STATUS_REJECTED = "rejected"

# Fetch の指 1 本あたりの可動範囲 [m] (fetch.urdf の l/r_gripper_finger_joint)
FINGER_MAX = 0.05


class ArmCommandServer:
    def __init__(self):
        arm_group = rospy.get_param("~arm_group", "arm")
        gripper_group = rospy.get_param("~gripper_group", "gripper")
        self.auto_execute = rospy.get_param("~auto_execute", False)

        # move_group と同時に起動するので、立ち上がるまで待つ
        wait = float(rospy.get_param("~wait_for_move_group", 60.0))
        self.arm = moveit_commander.MoveGroupCommander(arm_group, wait_for_servers=wait)
        self.arm.set_planning_time(float(rospy.get_param("~planning_time", 5.0)))
        self.arm.set_max_velocity_scaling_factor(float(rospy.get_param("~velocity_scaling", 0.5)))
        self.arm.set_max_acceleration_scaling_factor(float(rospy.get_param("~acceleration_scaling", 0.5)))
        self.gripper = moveit_commander.MoveGroupCommander(gripper_group, wait_for_servers=wait)
        # 未設定だと MoveIt の既定 (0.1 倍) になり遅いので、指は別に指定する。
        # 1.0 = URDF の上限 (指 1 本 0.05 m/s) 。実機もこの速さが上限
        self.gripper.set_max_velocity_scaling_factor(float(rospy.get_param("~gripper_velocity_scaling", 1.0)))
        self.gripper.set_max_acceleration_scaling_factor(float(rospy.get_param("~gripper_acceleration_scaling", 1.0)))

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

        # 計画・実行は 1 本ずつ。stop だけはロックを取らずに割り込む
        self.lock = threading.Lock()
        self.last_plan = None

        self.status_pub = rospy.Publisher("/coground/arm/status", String, queue_size=10, latch=True)
        self.traj_pub = rospy.Publisher("/coground/arm/planned_trajectory", JointTrajectory, queue_size=1, latch=True)

        rospy.Subscriber("/coground/arm/goal_pose", PoseStamped, self.on_goal_pose, queue_size=1)
        rospy.Subscriber("/coground/arm/goal_joints", JointState, self.on_goal_joints, queue_size=1)
        rospy.Subscriber("/coground/arm/execute", Empty, self.on_execute, queue_size=1)
        rospy.Subscriber("/coground/arm/stop", Empty, self.on_stop, queue_size=1)
        rospy.Subscriber("/coground/gripper/command", Float64, self.on_gripper, queue_size=1)

        rospy.loginfo("arm_command_server ready: group=%s planning_frame=%s ee=%s auto_execute=%s",
                      arm_group, self.arm.get_planning_frame(), self.arm.get_end_effector_link(),
                      self.auto_execute)
        self.publish_status("ready")

    # ---- 共通 ----
    def publish_status(self, status, detail=""):
        text = f"{status}: {detail}" if detail else status
        self.status_pub.publish(String(data=text))
        rospy.loginfo("[arm] %s", text)

    def plan_and_maybe_execute(self, set_target, description):
        if not self.lock.acquire(blocking=False):
            self.publish_status(STATUS_REJECTED, "busy")
            return
        try:
            self.publish_status(STATUS_PLANNING, description)
            self.arm.set_start_state_to_current_state()
            try:
                set_target()
            except Exception as e:  # 不正な関節名・範囲外など
                self.publish_status(STATUS_REJECTED, str(e))
                return
            success, plan, planning_time, error_code = self.arm.plan()
            self.arm.clear_pose_targets()
            if not success:
                self.last_plan = None
                self.traj_pub.publish(JointTrajectory())
                self.publish_status(STATUS_PLAN_FAILED, f"error_code={error_code.val}")
                return
            self.last_plan = plan
            self.traj_pub.publish(plan.joint_trajectory)
            n = len(plan.joint_trajectory.points)
            self.publish_status(STATUS_PLANNED, f"{n} points, {planning_time:.2f}s")
            if self.auto_execute:
                self.execute_locked()
        finally:
            self.lock.release()

    def execute_locked(self):
        if self.last_plan is None:
            self.publish_status(STATUS_REJECTED, "no plan")
            return
        self.publish_status(STATUS_EXECUTING)
        ok = self.arm.execute(self.last_plan, wait=True)
        self.arm.stop()
        # 同じ計画を 2 回実行すると開始姿勢がずれて失敗するので捨てる
        self.last_plan = None
        self.publish_status(STATUS_SUCCEEDED if ok else STATUS_EXEC_FAILED)

    # ---- コールバック ----
    def on_goal_pose(self, msg):
        planning_frame = self.arm.get_planning_frame()
        if not msg.header.frame_id:
            msg.header.frame_id = planning_frame
        p = msg.pose.position
        src = f"({p.x:.3f}, {p.y:.3f}, {p.z:.3f}) in {msg.header.frame_id}"
        if msg.header.frame_id != planning_frame:
            msg.header.stamp = rospy.Time(0)  # 最新の TF を使う
            try:
                msg = self.tf_buffer.transform(msg, planning_frame, rospy.Duration(1.0))
            except (tf2_ros.LookupException, tf2_ros.ConnectivityException,
                    tf2_ros.ExtrapolationException) as e:
                self.publish_status(STATUS_REJECTED, f"TF {src} -> {planning_frame}: {e}")
                return
            p = msg.pose.position
            src += f" = ({p.x:.3f}, {p.y:.3f}, {p.z:.3f}) in {planning_frame}"
        self.plan_and_maybe_execute(lambda: self.arm.set_pose_target(msg), f"pose {src}")

    def on_goal_joints(self, msg):
        if len(msg.name) != len(msg.position) or not msg.name:
            self.publish_status(STATUS_REJECTED, "name and position must have the same non-zero length")
            return
        target = dict(zip(msg.name, msg.position))
        self.plan_and_maybe_execute(lambda: self.arm.set_joint_value_target(target),
                                    f"joints {list(target.keys())}")

    def on_execute(self, _msg):
        if not self.lock.acquire(blocking=False):
            self.publish_status(STATUS_REJECTED, "busy")
            return
        try:
            self.execute_locked()
        finally:
            self.lock.release()

    def on_stop(self, _msg):
        self.arm.stop()
        self.publish_status(STATUS_STOPPED)

    def on_gripper(self, msg):
        finger = min(max(msg.data / 2.0, 0.0), FINGER_MAX)
        joints = self.gripper.get_active_joints()
        ok = self.gripper.go({j: finger for j in joints}, wait=True)
        self.gripper.stop()
        rospy.loginfo("[gripper] width=%.3f -> %s", finger * 2.0, "ok" if ok else "failed")


if __name__ == "__main__":
    moveit_commander.roscpp_initialize(sys.argv)
    rospy.init_node("coground_arm_command_server")
    ArmCommandServer()
    rospy.spin()
    moveit_commander.roscpp_shutdown()
