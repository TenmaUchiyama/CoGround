#!/usr/bin/env python3
"""Gazebo なし (運動学だけ) の台車。cmd_vel を積分して台車の位置を決める (腕の fake controller の台車版)。

台車の位置の正解は ROS 側 (このノード) が持ち、Unity は届いた位置にロボットを置いて表示するだけ。
Gazebo / 実機に替えるときは、このノードの代わりに Gazebo / 実機が同じ TF と /odom を出す。

入力:
  /coground/base/cmd_vel         geometry_msgs/Twist        move_base の速度指令
  /teleop/cmd_vel                geometry_msgs/Twist        キーボード操作 (make teleop)
  /coground/robot/initial_pose   geometry_msgs/PoseStamped  台車をこの位置に置き直す (frame world)。
                                                             Unity (RosBasePoseToFetch) が Play 開始時にシーン上の位置を送る
出力:
  TF  world -> odom             odom の原点 = 最初に置かれた位置 (以後固定。実機のオドメトリと同じ見え方)
  TF  odom  -> base_link        積分した位置
  /odom             nav_msgs/Odometry         odom 基準の位置と速度 (move_base の局所計画が速度を使う)
  /unity/base_pose  geometry_msgs/PoseStamped Unity 用。world 基準の base_link の位置 (~unity_rate Hz)

速度は差動二輪 (linear.x と angular.z) だけを使い、~max_linear / ~max_angular で頭打ちにする。
~cmd_timeout 秒指令が来なければ止まる。
"""
import math
import threading

import rospy
import tf.transformations as tft
import tf2_ros
from geometry_msgs.msg import PoseStamped, TransformStamped, Twist
from nav_msgs.msg import Odometry


def yaw_of(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def quat(yaw):
    return tft.quaternion_from_euler(0.0, 0.0, yaw)


class FakeBaseDriver:
    def __init__(self):
        self.world_frame = rospy.get_param("~world_frame", "world")
        self.odom_frame = rospy.get_param("~odom_frame", "odom")
        self.base_frame = rospy.get_param("~base_frame", "base_link")
        self.max_linear = float(rospy.get_param("~max_linear", 1.0))
        self.max_angular = float(rospy.get_param("~max_angular", 1.5))
        self.cmd_timeout = float(rospy.get_param("~cmd_timeout", 0.5))
        rate = float(rospy.get_param("~rate", 50.0))
        unity_rate = float(rospy.get_param("~unity_rate", 30.0))

        self.lock = threading.Lock()
        # world 基準の台車の位置 (x, y, yaw) と高さ
        self.x = self.y = self.yaw = 0.0
        self.z = 0.0
        # world -> odom (最初に置かれた位置)
        self.odom_origin = None
        self.cmd = Twist()
        self.cmd_time = rospy.Time(0)
        self.vx = self.wz = 0.0
        self.last_tick = None

        self.broadcaster = tf2_ros.TransformBroadcaster()
        self.odom_pub = rospy.Publisher("/odom", Odometry, queue_size=1)
        self.unity_pub = rospy.Publisher("/unity/base_pose", PoseStamped, queue_size=1, latch=True)
        rospy.Subscriber("/coground/base/cmd_vel", Twist, self.on_cmd, queue_size=1)
        rospy.Subscriber("/teleop/cmd_vel", Twist, self.on_cmd, queue_size=1)
        rospy.Subscriber("/coground/robot/initial_pose", PoseStamped, self.on_initial_pose, queue_size=1)

        rospy.Timer(rospy.Duration(1.0 / rate), self.tick)
        rospy.Timer(rospy.Duration(1.0 / unity_rate), self.publish_unity)
        rospy.loginfo("fake_base_driver: %s -> %s -> %s (Unity から /coground/robot/initial_pose を待つ。それまでは原点)",
                      self.world_frame, self.odom_frame, self.base_frame)

    def on_cmd(self, msg):
        with self.lock:
            self.cmd = msg
            self.cmd_time = rospy.Time.now()

    def on_initial_pose(self, msg):
        if msg.header.frame_id and msg.header.frame_id != self.world_frame:
            rospy.logwarn("initial_pose の frame_id は %s のはず (受信: %s)", self.world_frame, msg.header.frame_id)
            return
        q = msg.pose.orientation
        if q.x == 0.0 and q.y == 0.0 and q.z == 0.0 and q.w == 0.0:
            rospy.logwarn("initial_pose の orientation が全部 0 なので無視")
            return
        with self.lock:
            self.x, self.y, self.z = msg.pose.position.x, msg.pose.position.y, msg.pose.position.z
            self.yaw = yaw_of(q)
            self.cmd = Twist()
            self.vx = self.wz = 0.0
            if self.odom_origin is None:
                self.odom_origin = (self.x, self.y, self.z, self.yaw)
        rospy.loginfo("fake_base_driver: 台車を (%.2f, %.2f, yaw %.0f°) に置いた", self.x, self.y, math.degrees(self.yaw))

    def tick(self, _event):
        now = rospy.Time.now()
        with self.lock:
            dt = 0.0 if self.last_tick is None else (now - self.last_tick).to_sec()
            self.last_tick = now
            if (now - self.cmd_time).to_sec() > self.cmd_timeout:
                self.vx = self.wz = 0.0
            else:
                self.vx = max(-self.max_linear, min(self.max_linear, self.cmd.linear.x))
                self.wz = max(-self.max_angular, min(self.max_angular, self.cmd.angular.z))
            if 0.0 < dt < 0.5:
                # 中点の向きで進める (回りながら進むときの誤差を減らす)
                mid = self.yaw + 0.5 * self.wz * dt
                self.x += self.vx * math.cos(mid) * dt
                self.y += self.vx * math.sin(mid) * dt
                self.yaw = math.atan2(math.sin(self.yaw + self.wz * dt), math.cos(self.yaw + self.wz * dt))
            x, y, z, yaw, vx, wz = self.x, self.y, self.z, self.yaw, self.vx, self.wz
            ox, oy, oz, oyaw = self.odom_origin or (0.0, 0.0, 0.0, 0.0)

        # odom 基準の位置
        c, s = math.cos(-oyaw), math.sin(-oyaw)
        dx, dy = x - ox, y - oy
        lx, ly, lyaw = c * dx - s * dy, s * dx + c * dy, yaw - oyaw

        world_to_odom = self.transform(now, self.world_frame, self.odom_frame, ox, oy, oz, oyaw)
        odom_to_base = self.transform(now, self.odom_frame, self.base_frame, lx, ly, z - oz, lyaw)
        self.broadcaster.sendTransform([world_to_odom, odom_to_base])

        odom = Odometry()
        odom.header.stamp = now
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame
        odom.pose.pose.position.x, odom.pose.pose.position.y, odom.pose.pose.position.z = lx, ly, z - oz
        q = quat(lyaw)
        odom.pose.pose.orientation.x, odom.pose.pose.orientation.y = q[0], q[1]
        odom.pose.pose.orientation.z, odom.pose.pose.orientation.w = q[2], q[3]
        odom.twist.twist.linear.x = vx
        odom.twist.twist.angular.z = wz
        self.odom_pub.publish(odom)

    def publish_unity(self, _event):
        with self.lock:
            x, y, z, yaw = self.x, self.y, self.z, self.yaw
        msg = PoseStamped()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = self.world_frame
        msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = x, y, z
        q = quat(yaw)
        msg.pose.orientation.x, msg.pose.orientation.y = q[0], q[1]
        msg.pose.orientation.z, msg.pose.orientation.w = q[2], q[3]
        self.unity_pub.publish(msg)

    @staticmethod
    def transform(stamp, parent, child, x, y, z, yaw):
        t = TransformStamped()
        t.header.stamp = stamp
        t.header.frame_id = parent
        t.child_frame_id = child
        t.transform.translation.x, t.transform.translation.y, t.transform.translation.z = x, y, z
        q = quat(yaw)
        t.transform.rotation.x, t.transform.rotation.y = q[0], q[1]
        t.transform.rotation.z, t.transform.rotation.w = q[2], q[3]
        return t


if __name__ == "__main__":
    rospy.init_node("coground_fake_base_driver")
    FakeBaseDriver()
    rospy.spin()
