#!/usr/bin/env python3
"""Gazebo あり用: TF world -> odom を出して、world (= Unity の World) 基準でもロボットを表示できるようにする。

Gazebo は TF odom -> base_link (車輪オドメトリ) しか出さないので、world とつながっていない。
Gazebo の真値 (/unity/fetch_pose, world 基準) と /odom から
    world -> odom = (world -> base_link の真値) * (odom -> base_link)^-1
を計算して配信する。オドメトリがずれても world -> base_link は真値と一致する。
"""
import rospy
import tf2_ros
import tf.transformations as tft
from geometry_msgs.msg import PoseStamped, TransformStamped
from nav_msgs.msg import Odometry


def pose_to_matrix(pose):
    p, q = pose.position, pose.orientation
    m = tft.quaternion_matrix([q.x, q.y, q.z, q.w])
    m[0:3, 3] = [p.x, p.y, p.z]
    return m


class WorldOdomTf:
    def __init__(self):
        self.tf = TransformStamped()
        self.tf.header.frame_id = rospy.get_param("~world_frame", "world")
        self.tf.child_frame_id = rospy.get_param("~odom_frame", "odom")
        self.tf.transform.rotation.w = 1.0
        self.world_to_base = None
        self.odom_to_base = None

        self.broadcaster = tf2_ros.TransformBroadcaster()
        rospy.Subscriber("/unity/fetch_pose", PoseStamped, self.on_truth, queue_size=1)
        rospy.Subscriber("/odom", Odometry, self.on_odom, queue_size=1)
        rospy.Timer(rospy.Duration(1.0 / float(rospy.get_param("~rate", 30.0))), self.publish)

    def on_truth(self, msg):
        self.world_to_base = pose_to_matrix(msg.pose)

    def on_odom(self, msg):
        self.odom_to_base = pose_to_matrix(msg.pose.pose)

    def publish(self, _event):
        if self.world_to_base is None or self.odom_to_base is None:
            return
        m = self.world_to_base.dot(tft.inverse_matrix(self.odom_to_base))
        t = self.tf.transform
        t.translation.x, t.translation.y, t.translation.z = m[0:3, 3]
        t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w = tft.quaternion_from_matrix(m)
        self.tf.header.stamp = rospy.Time.now()
        self.broadcaster.sendTransform(self.tf)


if __name__ == "__main__":
    rospy.init_node("coground_world_odom_tf")
    WorldOdomTf()
    rospy.spin()
