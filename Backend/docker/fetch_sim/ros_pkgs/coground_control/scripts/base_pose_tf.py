#!/usr/bin/env python3
"""Unity から届くロボットの置き場所を TF (world -> odom -> base_link) と /odom にする。

Gazebo なし (運動学だけのロボット) 用。Unity の World 座標を ROS の world フレームとして扱う。
  入力: /coground/robot/base_pose  geometry_msgs/PoseStamped
        Unity の World 座標 (To<FLU>() 済み) での base_link の位置・向き。frame_id は world
  出力: TF world -> odom      odom の原点 = Unity から最初に届いたロボットの位置 (以後固定)
        TF odom  -> base_link そこからの移動量 (実機のオドメトリと同じ見え方)
        /odom (nav_msgs/Odometry) odom 基準の位置 (RViz の Odometry 表示用。速度は 0)

world -> base_link の合成結果は Unity の位置そのものなので、world 基準の指令はこれまでどおり使える。
Unity から何も届いていないうちは world = odom = 原点。odom の原点を取り直すにはノードを再起動する。
Gazebo / 実機では odom -> base_link を Gazebo / 実機が出すので、このノードは起動しないこと
(base_link に親が 2 つできて TF が壊れる)。
"""
import rospy
import tf2_ros
import tf.transformations as tft
from geometry_msgs.msg import PoseStamped, TransformStamped
from nav_msgs.msg import Odometry


def pose_to_matrix(position, orientation):
    m = tft.quaternion_matrix([orientation.x, orientation.y, orientation.z, orientation.w])
    m[0:3, 3] = [position.x, position.y, position.z]
    return m


def set_transform(tf_msg, m):
    t = tf_msg.transform
    t.translation.x, t.translation.y, t.translation.z = m[0:3, 3]
    t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w = tft.quaternion_from_matrix(m)


class BasePoseTf:
    def __init__(self):
        self.world_frame = rospy.get_param("~world_frame", "world")
        self.odom_frame = rospy.get_param("~odom_frame", "odom")
        self.base_frame = rospy.get_param("~base_frame", "base_link")
        rate = float(rospy.get_param("~rate", 30.0))

        self.world_to_odom = TransformStamped()
        self.world_to_odom.header.frame_id = self.world_frame
        self.world_to_odom.child_frame_id = self.odom_frame
        self.world_to_odom.transform.rotation.w = 1.0
        self.odom_inv = None  # world -> odom の逆行列。最初の base_pose で決まる

        self.odom_to_base = TransformStamped()
        self.odom_to_base.header.frame_id = self.odom_frame
        self.odom_to_base.child_frame_id = self.base_frame
        self.odom_to_base.transform.rotation.w = 1.0

        self.broadcaster = tf2_ros.TransformBroadcaster()
        self.odom_pub = rospy.Publisher("/odom", Odometry, queue_size=1)
        rospy.Subscriber("/coground/robot/base_pose", PoseStamped, self.on_pose, queue_size=1)
        rospy.Timer(rospy.Duration(1.0 / rate), self.publish)
        rospy.loginfo("base_pose_tf: %s -> %s -> %s (Unity から /coground/robot/base_pose を待つ。それまでは原点)",
                      self.world_frame, self.odom_frame, self.base_frame)

    def on_pose(self, msg):
        if msg.header.frame_id and msg.header.frame_id != self.world_frame:
            rospy.logwarn_throttle(5.0, "base_pose の frame_id は %s のはず (受信: %s)",
                                   self.world_frame, msg.header.frame_id)
            return
        q = msg.pose.orientation
        if q.x == 0.0 and q.y == 0.0 and q.z == 0.0 and q.w == 0.0:
            rospy.logwarn_throttle(5.0, "base_pose の orientation が全部 0 なので無視")
            return
        world_to_base = pose_to_matrix(msg.pose.position, q)
        if self.odom_inv is None:
            set_transform(self.world_to_odom, world_to_base)
            self.odom_inv = tft.inverse_matrix(world_to_base)
            rospy.loginfo("base_pose_tf: odom の原点を Unity の World (%.2f, %.2f, %.2f) に固定",
                          *world_to_base[0:3, 3])
        set_transform(self.odom_to_base, self.odom_inv.dot(world_to_base))

    def publish(self, _event):
        now = rospy.Time.now()
        self.world_to_odom.header.stamp = now
        self.odom_to_base.header.stamp = now
        self.broadcaster.sendTransform([self.world_to_odom, self.odom_to_base])

        odom = Odometry()
        odom.header.stamp = now
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame
        t = self.odom_to_base.transform
        odom.pose.pose.position.x = t.translation.x
        odom.pose.pose.position.y = t.translation.y
        odom.pose.pose.position.z = t.translation.z
        odom.pose.pose.orientation = t.rotation
        self.odom_pub.publish(odom)


if __name__ == "__main__":
    rospy.init_node("coground_base_pose_tf")
    BasePoseTf()
    rospy.spin()
