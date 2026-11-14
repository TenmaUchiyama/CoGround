#!/usr/bin/env python3
"""Gazebo 上のモデルの真値姿勢 (world 座標) を PoseStamped で間引いて配信する。

/odom はオドメトリなのでスリップでずれる。VR で重ねるときは
Gazebo world 座標の真値を使う方がずれない。
"""
import time

import rospy
from gazebo_msgs.msg import ModelStates
from geometry_msgs.msg import PoseStamped


class ModelPoseRelay:
    def __init__(self):
        self.model_name = rospy.get_param("~model_name", "fetch")
        self.frame_id = rospy.get_param("~frame_id", "world")
        rate_hz = float(rospy.get_param("~rate", 30.0))
        self.min_interval = 1.0 / rate_hz if rate_hz > 0 else 0.0
        self.last_pub = 0.0
        self.pub = rospy.Publisher("~pose", PoseStamped, queue_size=1)
        rospy.Subscriber("/gazebo/model_states", ModelStates, self.on_states, queue_size=1)

    def on_states(self, msg):
        now = time.monotonic()
        if now - self.last_pub < self.min_interval:
            return
        try:
            i = msg.name.index(self.model_name)
        except ValueError:
            return
        out = PoseStamped()
        out.header.stamp = rospy.Time.now()
        out.header.frame_id = self.frame_id
        out.pose = msg.pose[i]
        self.pub.publish(out)
        self.last_pub = now


if __name__ == "__main__":
    rospy.init_node("model_pose_relay")
    ModelPoseRelay()
    rospy.spin()
