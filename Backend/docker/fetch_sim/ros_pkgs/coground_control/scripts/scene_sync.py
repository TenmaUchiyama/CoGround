#!/usr/bin/env python3
"""Unity に置いた箱 (机など) を MoveIt の Planning Scene に衝突物体として登録する。

入力: /coground/scene/objects  visualization_msgs/MarkerArray
  Unity の MoveItCollisionBox が送る。1 つの Marker = 1 つの箱
    type   CUBE だけ対応
    action ADD (= 追加・更新) / DELETE (= 削除)
    text   物体の名前 (Planning Scene の id は "unity/<text>")
    header.frame_id world (Unity の World) / pose 箱の中心 / scale 箱の大きさ [m]
出力: /collision_object (moveit_msgs/CollisionObject) → move_group が Planning Scene に反映

MoveIt (ROS1) は物体を planning frame (base_link) 基準で持つので、world 基準のままだと
ロボットが動いたときに物体も一緒に動いてしまう。このノードが TF で base_link 基準に直し、
ロボットが動くたびに置き直す。
Unity から stale_timeout 秒届かなくなった物体は消す (Unity の Play を止めたときなど)。
pick_place_server が扱っている物体 (/coground/pick_place/held) は、その間 Unity の値で上書きしない
(Planning Scene から外したり手にくっつけたりしているため)。扱い終わったら Unity の最新の位置で置き直す。
"""
import math

import moveit_commander
import rospy
import tf2_geometry_msgs  # noqa: F401  PoseStamped を tf2 で変換できるようにする
import tf2_ros
from geometry_msgs.msg import PoseStamped
from moveit_msgs.msg import CollisionObject
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray

PREFIX = "unity/"


class SceneSync:
    def __init__(self):
        self.planning_frame = rospy.get_param("~planning_frame", "base_link")
        self.stale_timeout = float(rospy.get_param("~stale_timeout", 3.0))
        self.objects = {}  # id -> {"pose": PoseStamped(world), "size": (x, y, z), "seen": float}
        self.sent = {}     # id -> (base_link での位置・向き, size) 最後に送った値
        self.held = None   # pick_place_server が扱っている物体の id

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        self.pub = rospy.Publisher("/collision_object", CollisionObject, queue_size=50)

        # 前回の起動で残った Unity の物体を消す
        scene = moveit_commander.PlanningSceneInterface(synchronous=False)
        rospy.sleep(1.0)
        for name in scene.get_known_object_names():
            if name.startswith(PREFIX):
                self.remove(name)

        rospy.Subscriber("/coground/scene/objects", MarkerArray, self.on_objects, queue_size=10)
        rospy.Subscriber("/coground/pick_place/held", String, self.on_held, queue_size=1)
        rospy.Timer(rospy.Duration(1.0 / float(rospy.get_param("~rate", 5.0))), self.update)
        rospy.loginfo("scene_sync: /coground/scene/objects -> Planning Scene (%s 基準)", self.planning_frame)

    def on_objects(self, msg):
        now = rospy.get_time()
        for m in msg.markers:
            oid = PREFIX + (m.text or f"{m.ns}_{m.id}")
            if m.action == Marker.DELETE:
                self.objects.pop(oid, None)
                if oid != self.held:
                    self.remove(oid)
                continue
            if m.type != Marker.CUBE:
                rospy.logwarn_throttle(10.0, "scene_sync: CUBE 以外は未対応 (%s)", oid)
                continue
            size = (abs(m.scale.x), abs(m.scale.y), abs(m.scale.z))
            if min(size) <= 0.0:
                continue
            pose = PoseStamped(header=m.header, pose=m.pose)
            if not pose.header.frame_id:
                pose.header.frame_id = "world"
            if oid not in self.objects:
                rospy.loginfo("scene_sync: 追加 %s size=(%.2f, %.2f, %.2f)", oid, *size)
            self.objects[oid] = {"pose": pose, "size": size, "seen": now}

    def on_held(self, msg):
        held = PREFIX + msg.data if msg.data else None
        for oid in (self.held, held):
            self.sent.pop(oid, None)  # 扱い終わった物体は次の update で必ず置き直す
        self.held = held

    def update(self, _event):
        now = rospy.get_time()
        for oid in [k for k, o in self.objects.items()
                    if now - o["seen"] > self.stale_timeout and k != self.held]:
            rospy.loginfo("scene_sync: Unity から届かなくなったので削除 %s", oid)
            del self.objects[oid]
            self.remove(oid)

        for oid, o in self.objects.items():
            if oid == self.held:
                continue
            src = o["pose"]
            src.header.stamp = rospy.Time(0)  # 最新の TF を使う
            try:
                pose = self.tf_buffer.transform(src, self.planning_frame, rospy.Duration(0.1))
            except (tf2_ros.LookupException, tf2_ros.ConnectivityException,
                    tf2_ros.ExtrapolationException) as e:
                rospy.logwarn_throttle(5.0, "scene_sync: TF %s -> %s: %s",
                                       src.header.frame_id, self.planning_frame, e)
                return
            p, q = pose.pose.position, pose.pose.orientation
            key = (p.x, p.y, p.z, q.x, q.y, q.z, q.w)
            last = self.sent.get(oid)
            if last is not None and last[1] == o["size"] and _close(last[0], key):
                continue
            self.add(oid, pose, o["size"])
            self.sent[oid] = (key, o["size"])

    def add(self, oid, pose, size):
        co = CollisionObject()
        co.header = pose.header
        co.header.stamp = rospy.Time.now()
        co.id = oid
        co.primitives = [SolidPrimitive(type=SolidPrimitive.BOX, dimensions=list(size))]
        co.primitive_poses = [pose.pose]
        co.operation = CollisionObject.ADD  # 同じ id があれば置き換え
        self.pub.publish(co)

    def remove(self, oid):
        self.sent.pop(oid, None)
        co = CollisionObject()
        co.header.frame_id = self.planning_frame
        co.header.stamp = rospy.Time.now()
        co.id = oid
        co.operation = CollisionObject.REMOVE
        self.pub.publish(co)


def _close(a, b, pos_tol=0.001, rot_tol=0.001):
    return (math.dist(a[:3], b[:3]) < pos_tol and
            abs(abs(sum(x * y for x, y in zip(a[3:], b[3:]))) - 1.0) < rot_tol)


if __name__ == "__main__":
    rospy.init_node("coground_scene_sync")
    SceneSync()
    rospy.spin()
