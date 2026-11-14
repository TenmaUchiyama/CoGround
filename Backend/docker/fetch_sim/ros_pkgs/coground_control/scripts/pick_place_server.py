#!/usr/bin/env python3
"""Planning Scene にある箱 (Unity の MoveItPickable) を、指定した場所へ運ぶ (上からつかむ)。

入力:
  /coground/pick_place/command  std_msgs/String (JSON)
      {"object": "BoxA",                       # Unity の GameObject 名 (Planning Scene の id は unity/BoxA)
       "frame_id": "world",                    # 省略時 world (= Unity の World)
       "place": {"position": [x, y, z],        # 置いたときの箱の中心
                 "orientation": [x, y, z, w]}} # 置いたときの箱の向き (省略時は今の向きのまま)
  /coground/arm/stop  std_msgs/Empty  実行中の動作を止める (arm_command_server と共通。止めると中断する)

出力 (すべて latch):
  /coground/pick_place/status    std_msgs/String  "<状態>: 詳細"
      ready / accepted / rejected / opening / approaching / descending / grasping / lifting / moving / lowering /
      releasing / retreating / succeeded / failed
  /coground/pick_place/held      std_msgs/String  いま扱っている物体名 ("" = なし)。scene_sync はこの物体を Unity の値で上書きしない
  /coground/pick_place/attached  std_msgs/String  手にくっついている物体名 ("" = なし)。Unity はこの間、物体をグリッパーに追従させる

手順: 開く → つかむ手前 (上空) → 物体を Planning Scene から外して真下へ → 閉じる → attach → 持ち上げる
     → 置き場所の上空 → 真下へ → 開く → detach → 上へ引く
途中で失敗したら止まる。物体を持ったまま失敗した場合は、次の command で同じ物体を指定すると置く手順から再開する。
"""
import json
import math
import sys
import threading

import moveit_commander
import numpy as np
import rospy
import tf.transformations as tft
import tf2_geometry_msgs  # noqa: F401
import tf2_ros
from geometry_msgs.msg import Pose, PoseStamped
from std_msgs.msg import Empty, String

PREFIX = "unity/"
WRIST_TO_GRIPPER = 0.16645  # wrist_roll_link -> gripper_link (fetch.urdf の gripper_axis)
TOUCH_LINKS = ["gripper_link", "l_gripper_finger_link", "r_gripper_finger_link", "wrist_roll_link"]


class Abort(Exception):
    pass


def pose_to_matrix(pose):
    p, q = pose.position, pose.orientation
    m = tft.quaternion_matrix([q.x, q.y, q.z, q.w])
    m[0:3, 3] = [p.x, p.y, p.z]
    return m


def matrix_to_pose(m):
    pose = Pose()
    pose.position.x, pose.position.y, pose.position.z = m[0:3, 3]
    q = tft.quaternion_from_matrix(m)
    pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w = q
    return pose


def yaw_of(m):
    return math.atan2(m[1, 0], m[0, 0])


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def top_down(x, y, z, yaw):
    """gripper_link が (x, y, z) で真下を向き、指が yaw 方向と直交して閉じるときの wrist_roll_link の姿勢"""
    m = tft.euler_matrix(0.0, math.pi / 2, yaw, "sxyz")  # Rz(yaw) * Ry(90°): gripper の x 軸 (進む向き) が真下
    m[0:3, 3] = [x, y, z + WRIST_TO_GRIPPER]
    return m


class PickPlaceServer:
    def __init__(self):
        self.frame = rospy.get_param("~planning_frame", "base_link")
        self.approach = float(rospy.get_param("~approach_distance", 0.10))   # 上空からまっすぐ下ろす距離 [m]
        self.grasp_depth = float(rospy.get_param("~grasp_depth", 0.015))     # 箱の上面から gripper_link を下げる量 [m]
        self.place_clearance = float(rospy.get_param("~place_clearance", 0.005))  # 置くときに浮かせる量 [m]
        self.max_open = float(rospy.get_param("~gripper_max_open", 0.10))
        self.velocity = float(rospy.get_param("~velocity_scaling", 0.5))

        # 胴体 (torso) も使う。胴体を下げたままだと上からつかめるのは正面 0.65 m 程度まで
        group = rospy.get_param("~arm_group", "arm_with_torso")
        self.arm = moveit_commander.MoveGroupCommander(group, wait_for_servers=60.0)
        self.arm.set_end_effector_link("wrist_roll_link")
        self.arm.set_pose_reference_frame(self.frame)
        self.arm.set_planning_time(5.0)
        self.arm.set_max_velocity_scaling_factor(self.velocity)
        self.arm.set_max_acceleration_scaling_factor(self.velocity)
        self.gripper = moveit_commander.MoveGroupCommander("gripper", wait_for_servers=60.0)
        self.gripper.set_max_velocity_scaling_factor(1.0)
        self.gripper.set_max_acceleration_scaling_factor(1.0)
        self.scene = moveit_commander.PlanningSceneInterface(synchronous=True)

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        self.lock = threading.Lock()
        self.stop_requested = False
        self.holding = None        # 手にくっついている物体名 (PREFIX なし)
        self.wrist_to_obj = None   # つかんだときの wrist_roll_link から見た箱の姿勢
        self.obj_size = None

        self.status_pub = rospy.Publisher("/coground/pick_place/status", String, queue_size=10, latch=True)
        self.held_pub = rospy.Publisher("/coground/pick_place/held", String, queue_size=1, latch=True)
        self.attached_pub = rospy.Publisher("/coground/pick_place/attached", String, queue_size=1, latch=True)

        # 前回の起動で手に残った物体を外す
        for name in self.scene.get_attached_objects().keys():
            if name.startswith(PREFIX):
                self.scene.remove_attached_object(name=name)
                self.scene.remove_world_object(name)
        self.held_pub.publish(String(""))
        self.attached_pub.publish(String(""))

        rospy.Subscriber("/coground/pick_place/command", String, self.on_command, queue_size=1)
        rospy.Subscriber("/coground/arm/stop", Empty, self.on_stop, queue_size=1)
        self.status("ready")

    # ---- 共通 ----
    def status(self, state, detail=""):
        text = f"{state}: {detail}" if detail else state
        self.status_pub.publish(String(text))
        rospy.loginfo("[pick_place] %s", text)

    def on_stop(self, _msg):
        self.stop_requested = True

    def check_stop(self):
        if self.stop_requested:
            raise Abort("stopped")

    def execute(self, plan, what):
        self.check_stop()
        if not self.arm.execute(plan, wait=True):
            self.arm.stop()
            raise Abort(f"{what}: 実行に失敗" + (" (stop)" if self.stop_requested else ""))
        self.arm.stop()

    def plan_to(self, wrist_m):
        self.arm.set_start_state_to_current_state()
        target = PoseStamped()
        target.header.frame_id = self.frame
        target.pose = matrix_to_pose(wrist_m)
        self.arm.set_pose_target(target)
        ok, plan, _, _ = self.arm.plan()
        self.arm.clear_pose_targets()
        return plan if ok else None

    def straight(self, dz, what, avoid_collisions=True):
        """手先を真上 / 真下に dz [m] 動かす"""
        self.check_stop()
        self.arm.set_start_state_to_current_state()
        pose = matrix_to_pose(self.current_wrist())
        pose.position.z += dz
        plan, fraction = self.arm.compute_cartesian_path([pose], 0.005, avoid_collisions=avoid_collisions)
        if fraction < 0.95:
            raise Abort(f"{what}: 直線で動けない (到達率 {fraction:.0%})")
        plan = self.arm.retime_trajectory(self.arm.get_current_state(), plan,
                                          velocity_scaling_factor=self.velocity,
                                          acceleration_scaling_factor=self.velocity)
        self.execute(plan, what)

    def set_gripper(self, width):
        self.check_stop()
        finger = min(max(width / 2.0, 0.0), self.max_open / 2.0)
        self.gripper.go({j: finger for j in self.gripper.get_active_joints()}, wait=True)
        self.gripper.stop()

    def object_in_scene(self, oid):
        """Planning Scene の箱の姿勢 (planning frame の行列) と大きさ"""
        objs = self.scene.get_objects([oid])
        if oid not in objs:
            return None, None
        co = objs[oid]
        if not co.primitives:
            return None, None
        m = pose_to_matrix(co.primitive_poses[0])
        q = co.pose.orientation
        if (q.x, q.y, q.z, q.w) != (0.0, 0.0, 0.0, 0.0):  # MoveIt 1.1 以降は物体全体の pose がある
            m = pose_to_matrix(co.pose).dot(m)
        if co.header.frame_id and co.header.frame_id != self.frame:
            raise Abort(f"{oid} の frame が {co.header.frame_id} ({self.frame} のはず)")
        return m, list(co.primitives[0].dimensions)

    def to_planning_frame(self, frame_id, position, orientation):
        ps = PoseStamped()
        ps.header.frame_id = frame_id
        ps.header.stamp = rospy.Time(0)
        ps.pose.position.x, ps.pose.position.y, ps.pose.position.z = position
        ps.pose.orientation.x, ps.pose.orientation.y, ps.pose.orientation.z, ps.pose.orientation.w = orientation
        try:
            return pose_to_matrix(self.tf_buffer.transform(ps, self.frame, rospy.Duration(1.0)).pose)
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
            raise Abort(f"TF {frame_id} -> {self.frame}: {e}")

    # ---- 指令 ----
    def on_command(self, msg):
        try:
            cmd = json.loads(msg.data)
            name = cmd["object"]
            frame_id = cmd.get("frame_id", "world")
            place = cmd["place"]
            position = [float(v) for v in place["position"]]
            orientation = place.get("orientation")
            orientation = [float(v) for v in orientation] if orientation else None
        except (ValueError, KeyError, TypeError) as e:
            self.status("rejected", f"command の形式が不正: {e}")
            return
        if not self.lock.acquire(blocking=False):
            self.status("rejected", "busy")
            return
        self.stop_requested = False
        self.status("accepted", name)  # Unity の順番待ちは、これを見てからの終わりの状態をこの指令の結果とみなす
        try:
            if self.holding is not None and self.holding != name:
                raise Abort(f"{self.holding} を持っているので {name} はつかめない")
            if self.holding is None:
                self.pick(name)
            self.place(name, frame_id, position, orientation)
            self.status("succeeded", name)
        except Abort as e:
            self.arm.stop()
            self.status("failed", str(e))
        except Exception as e:  # 想定外でもロックを外して次の指令を受けられるようにする
            rospy.logerr("[pick_place] %s", e, exc_info=True)
            self.status("failed", f"内部エラー: {e}")
        finally:
            if self.holding is None:
                self.held_pub.publish(String(""))
            self.lock.release()

    def pick(self, name):
        oid = PREFIX + name
        obj, size = self.object_in_scene(oid)
        if obj is None:
            raise Abort(f"{oid} が Planning Scene にない (Unity の MoveItCollisionBox を確認)")
        if abs(obj[2, 2]) < 0.99:
            raise Abort(f"{name} が傾いている (上からつかめるのは置いたままの向きだけ)")

        # つかみ方の候補: 箱の辺に合わせて 90° ずつ。指の間に入る向きだけ、ロボットの正面に近い順
        candidates = []
        for k in range(4):
            yaw = wrap(yaw_of(obj) + k * math.pi / 2)
            width = size[1] if k % 2 == 0 else size[0]  # 指が閉じる方向 (gripper の y 軸) の幅
            if width < self.max_open - 0.01:
                candidates.append((abs(yaw), yaw, width))
        if not candidates:
            raise Abort(f"{name} は指の間 ({self.max_open * 100:.0f} cm) に入らない: {size}")
        candidates.sort()

        cx, cy, cz = obj[0:3, 3]
        grip_z = cz + size[2] / 2 - min(self.grasp_depth, size[2] / 2)

        self.held_pub.publish(String(name))
        self.status("opening", name)
        self.set_gripper(self.max_open)

        for _, yaw, width in candidates:
            grasp = top_down(cx, cy, grip_z, yaw)
            above = grasp.copy()
            above[2, 3] += self.approach
            self.status("approaching", f"{name} (yaw {math.degrees(yaw):.0f}°)")
            plan = self.plan_to(above)
            if plan is None:
                continue
            self.execute(plan, "つかむ手前へ")

            # 指が箱に触れるので、下ろす前に Planning Scene から外す
            self.scene.remove_world_object(oid)
            self.status("descending", name)
            try:
                self.straight(-self.approach, "下ろす")
            except Abort:
                # 下ろせない (机に当たるなど)。上空にいるので次の向きを試す。物体は scene_sync が戻す
                self.held_pub.publish(String(""))
                rospy.sleep(0.5)
                self.held_pub.publish(String(name))
                continue

            self.status("grasping", name)
            # 箱の幅まで閉じる (疑似実行では力が無いので、0 まで閉じると Unity で指が箱にめり込む)
            self.set_gripper(max(width - 0.002, 0.0))
            obj_pose = PoseStamped()
            obj_pose.header.frame_id = self.frame
            obj_pose.pose = matrix_to_pose(obj)
            self.scene.attach_box("gripper_link", oid, obj_pose, size, touch_links=TOUCH_LINKS)
            self.holding = name
            self.obj_size = size
            self.wrist_to_obj = np.linalg.inv(grasp).dot(obj)
            self.attached_pub.publish(String(name))

            self.status("lifting", name)
            self.straight(self.approach, "持ち上げる")
            return
        raise Abort(f"{name} をつかめる向きがない (腕が届かない / 机に当たる)")

    def place(self, name, frame_id, position, orientation):
        oid = PREFIX + name
        if orientation is None:
            # 向きの指定なし: 今の (持ち上げたときの) 箱の向きの yaw だけ使う
            current = self.current_wrist().dot(self.wrist_to_obj)
            target = tft.euler_matrix(0, 0, yaw_of(current))
            target[0:3, 3] = self.to_planning_frame(frame_id, position, [0, 0, 0, 1])[0:3, 3]
        else:
            target = self.to_planning_frame(frame_id, position, orientation)
        target[2, 3] += self.place_clearance

        # 箱は左右対称なので 180° 回しても同じ置き方。正方形なら 90° も
        turns = [0, math.pi]
        if abs(self.obj_size[0] - self.obj_size[1]) < 0.005:
            turns += [math.pi / 2, -math.pi / 2]
        for turn in turns:
            obj_target = target.dot(tft.rotation_matrix(turn, (0, 0, 1)))
            wrist = obj_target.dot(np.linalg.inv(self.wrist_to_obj))
            above = wrist.copy()
            above[2, 3] += self.approach
            self.status("moving", f"{name} を置き場所の上へ")
            plan = self.plan_to(above)
            if plan is None:
                continue
            self.execute(plan, "置き場所の上へ")
            self.status("lowering", name)
            self.straight(-self.approach, "下ろす")
            break
        else:
            raise Abort(f"置き場所に届かない / ぶつかる ({name} は手に持ったまま)")

        self.status("releasing", name)
        self.set_gripper(self.max_open)
        self.scene.remove_attached_object("gripper_link", oid)  # MoveIt では今の位置に置いた物体になる
        self.holding = None
        self.attached_pub.publish(String(""))

        self.status("retreating", name)
        try:
            self.straight(self.approach, "上へ引く")
        except Abort:
            self.straight(self.approach, "上へ引く", avoid_collisions=False)  # 真上なので安全
        self.held_pub.publish(String(""))  # 以後は Unity の位置で scene_sync が更新する

    def current_wrist(self):
        pose = self.arm.get_current_pose("wrist_roll_link")
        if pose.header.frame_id != self.frame:
            pose.header.stamp = rospy.Time(0)
            pose = self.tf_buffer.transform(pose, self.frame, rospy.Duration(1.0))
        return pose_to_matrix(pose.pose)


if __name__ == "__main__":
    moveit_commander.roscpp_initialize(sys.argv)
    rospy.init_node("coground_pick_place_server")
    PickPlaceServer()
    rospy.spin()
    moveit_commander.roscpp_shutdown()
