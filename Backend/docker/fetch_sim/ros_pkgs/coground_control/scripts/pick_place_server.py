#!/usr/bin/env python3
"""Planning Scene にある箱 (Unity の MoveItPickable) を、指定した場所へ運ぶ (上からつかむ)。
台車の移動 (move_base) も含めた一連の動きを「計画だけ」して見せ、その計画どおりに実行することもできる。

入力:
  /coground/pick_place/command  std_msgs/String (JSON)
      {"object": "BoxA",                       # Unity の GameObject 名 (Planning Scene の id は unity/BoxA)
       "frame_id": "world",                    # 省略時 world (= Unity の World)
       "place": {"position": [x, y, z],        # 置いたときの箱の中心
                 "orientation": [x, y, z, w]}} # 置いたときの箱の向き (省略時は今の向きのまま)
  /coground/arm/stop  std_msgs/Empty  実行中の動作を止める (arm_command_server と共通。止めると中断する)

出力 (すべて latch):
  /coground/pick_place/status    std_msgs/String  "<状態>: 詳細"
      ready / accepted / rejected / navigating / opening / approaching / descending / grasping / lifting / moving /
      lowering / releasing / retreating / succeeded / failed
  /coground/pick_place/held      std_msgs/String  いま扱っている物体名 ("" = なし)。scene_sync はこの物体を Unity の値で上書きしない
  /coground/pick_place/attached  std_msgs/String  手にくっついている物体名 ("" = なし)。Unity はこの間、物体をグリッパーに追従させる

手順: 開く → つかむ手前 (上空) → 物体を Planning Scene から外して真下へ → 閉じる → attach → 持ち上げる
     → 置き場所の上空 → 真下へ → 開く → detach → 上へ引く
途中で失敗したら止まる。物体を持ったまま失敗した場合は、次の command で同じ物体を指定すると置く手順から再開する。

スキル (グラウンディングサーバーの Executor が使う。goal_id で結果を見分けられる):
  /coground/skill/goal      std_msgs/String (JSON)
      {"goal_id": "g1", "skill": "pick" | "place" | "pick_place" | "navigate", "object": "BoxA",
       "frame_id": "world", "place": {"position": [...], "orientation": [...]},
       "pose": [x, y, yaw],                                        # navigate の行き先 (world)
       "plan_ref": {"plan_id": "...", "plan_version": 1, "step_id": "s1"}}   # 計画どおりに動かす (下の「計画」)
       "keepout_zones": [{"id": "zone_play", "polygon": [[x, y], ...]}]}     # navigate で避ける範囲 (world。省略時はなし)
      pick        つかんで持ち上げるまで。もう同じ物体を持っていれば、何もせず succeeded
      place       持っている物体を置く。place を省くと、つかんだ元の場所へ戻す
      pick_place  /coground/pick_place/command と同じ
      navigate    台車を pose へ動かす (move_base)。もうそこにいれば何もしない
  /coground/skill/cancel    std_msgs/String (JSON) {"goal_id": "g1"}  実行中の goal を止める (goal_id が空なら、どの goal でも止める)
  /coground/skill/feedback  std_msgs/String (JSON)
      {"goal_id", "skill", "object", "state", "phase", "detail", "holding", "mode"}
      state: accepted / running (phase に opening などが入る) / succeeded / failed / canceled / rejected
      mode : 終わったときだけ。replay (計画した軌道をそのまま使った) / replanned (その場で計画し直した。detail に理由) / online
  /coground/skill/state     std_msgs/String (JSON, latch。変わったときと 1 秒ごと)
      {"busy": bool, "goal_id": 実行中の goal か null, "holding": 手に持っている物体名か null, "hold": bool}
実行は別スレッドで行うので、実行中に届いた goal は rejected (busy) になる。

家庭ルール (グラウンディングサーバーの監視が使う。monitor.py):
  /coground/skill/hold  std_msgs/String (JSON)  {"hold": true, "reason": "..."} / {"hold": false, "keepout_zones": [...] か null}
      hold の間は台車を動かさない。スキルは取り消さず、その場で待つ (腕は止めない)。止めるのは次の 3 つすべて:
        move_base への goal (送ってあれば取り消し、hold が解けたら今の位置から送り直す)
        slide_base (障害物から離れるための置き直し)、着いたあとの置き直し (snap_base)
      cmd_vel を 0 にするだけでは、位置を直接書く後ろの 2 つが止まらないので、ここで止める。
      hold を解くときに keepout_zones を渡すと、その範囲を避ける地図に替えてから再開する (null なら今のまま)
  進入禁止の範囲 (keepout_zones) は /coground/nav/keepout_zones に出し、base_command_server が地図 (/coground/nav/keepout) にする。
  move_base の costmap の keepout_layer がそれを読むので、make_plan も実行も同じ範囲を避ける
  /coground/nav/route_request  std_msgs/String (JSON)  {"route_id", "goal": [x, y, yaw], "keepout_zones": [...] か null}
      今の位置から goal までの経路だけを計画する (スキルの実行中・hold 中でも使える。台車は動かさない)
  /coground/nav/route_result   std_msgs/String (JSON)  {"route_id", "ok", "reason", "base": [[t, x, y, yaw], ...]}  t は今からの秒

計画 (動かさずに、移動 → ピック → 移動 → プレース を全部計算する):
  /coground/task/plan_request   std_msgs/String (JSON)
      {"plan_id": "plan_3", "plan_version": 1,
       "steps": [{"step_id": "s1", "object": "BoxA",
                  "place": {"position": [...], "orientation": [...]},   # 離すときの物体の中心 (world)
                  "rest": {"position": [...], "orientation": [...]},    # 落ちたあとの物体 (world。省略時は place と同じ)
                  "approach": {"pick": [[x, y, yaw], ...], "place": [...]}}],  # 家具に決めてある止まる位置 (先に試す)
       "keepout_zones": [{"id": "zone_play", "polygon": [[x, y], ...]}]}  # 避ける範囲 (world。省略時はなし)
      step の kind (省略時 pick_place):
        pick_place  移動 → つかむ → 移動 → 置く (上の形)
        pick        {"step_id", "kind": "pick", "object", "stay": true}  つかんで持ち上げるまで。stay なら台車を動かさない
        navigate    {"step_id", "kind": "navigate", "pose": [x, y, yaw]}  台車の移動だけ (move_base の経路)
      Web UI の「ロボット単体テスト」が pick / navigate を使う。計画は直近の数個を覚えておく (plan_ref で使える)
  /coground/task/plan_feedback  std_msgs/String (JSON)  {"plan_id", "plan_version", "step_id", "detail"} 途中経過
  /coground/task/plan_result    std_msgs/String (JSON, latch)  結果と、通しで再生するための時間軸 (Unity と Web UI が使う)
      {"plan_id", "plan_version", "error",
       "steps": [{"step_id", "object", "status": "ok" | "infeasible", "reason", "t0", "t1",
                  "stops": {"pick": [x, y, yaw], "place": [x, y, yaw]},
                  "stop_source": {"pick": "approach" | "auto" | "stay", "place": ...}}],
       "timeline": {"duration",
                    "base": [[t, x, y, yaw], ...],                     # world の base_link
                    "base_z": z,                                       # base_link の高さ (計画の間は変わらない)
                    "joint_names": [...], "joints": [[t, v1, v2, ...], ...],
                    "attached": [{"object", "t0", "t1", "link", "pose": {"position", "orientation"}}],  # link から見た物体
                    "phases": [{"step_id", "phase", "t0", "t1"}],
                    "objects": [{"object", "start": {...}, "rest": {...}}]}}   # world
  計画は step を順に、前の step を終えた状態から行う。計画できない step は infeasible にして飛ばす。
  止まる位置は、物体の手前を角度を変えて何か所か試し、move_base の経路があって腕が届く所にする
  (今の位置のまま届くなら動かない)。計画中は scene_sync を止め (/coground/scene/freeze)、
  机などを「仮に止まった位置の台車」から見た位置に置き直して計画する。
  計画した軌道は覚えておき、plan_ref 付きの skill で使う:
    - 台車が止まる位置から ~replay_tolerance 以内で、軌道の始まりが今の関節角と合い、今のシーンでぶつからなければ
      そのまま再生する (replay)。そうでなければ、その場で計画し直す (replanned)
    - ~snap_base (シミュレーション) が true なら、move_base で着いたあとに台車を止まる位置へぴったり置き直す
"""
import copy
import json
import math
import sys
import threading

import actionlib
import moveit_commander
import numpy as np
import rospy
import tf.transformations as tft
import tf2_geometry_msgs  # noqa: F401
import tf2_ros
from actionlib_msgs.msg import GoalStatus
from geometry_msgs.msg import Pose, PoseStamped, Twist
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from moveit_msgs.msg import CollisionObject, PlanningScene, PlanningSceneWorld, RobotState
from moveit_msgs.srv import ApplyPlanningScene, GetPositionFK, GetPositionFKRequest, GetStateValidity, \
    GetStateValidityRequest
from map_msgs.msg import OccupancyGridUpdate
from nav_msgs.msg import OccupancyGrid
from nav_msgs.srv import GetPlan, GetPlanRequest
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import Bool, Empty, String
from visualization_msgs.msg import Marker, MarkerArray

PREFIX = "unity/"
MAX_PLANS = 4  # 覚えておく計画の数
STEP_KINDS = ("pick_place", "pick", "navigate")
WRIST_TO_GRIPPER = 0.16645  # wrist_roll_link -> gripper_link (fetch.urdf の gripper_axis)
TOUCH_LINKS = ["gripper_link", "l_gripper_finger_link", "r_gripper_finger_link", "wrist_roll_link"]
SKILLS = ("pick", "place", "pick_place", "navigate")
PHASES = ("navigating", "opening", "approaching", "descending", "grasping", "lifting",
          "moving", "lowering", "releasing", "retreating")  # plan_types.PHASES と同じ


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


def matrix_to_dict(m):
    q = tft.quaternion_from_matrix(m)
    return {"position": [round(float(v), 5) for v in m[0:3, 3]], "orientation": [round(float(v), 6) for v in q]}


def dict_to_matrix(d):
    q = d.get("orientation") or [0.0, 0.0, 0.0, 1.0]
    m = tft.quaternion_matrix(q)
    m[0:3, 3] = d["position"]
    return m


def yaw_of(m):
    return math.atan2(m[1, 0], m[0, 0])


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def planar(x, y, yaw, z=0.0):
    m = tft.euler_matrix(0.0, 0.0, yaw)
    m[0:3, 3] = [x, y, z]
    return m


def base_track(x, y, yaw, waypoints, linear, angular):
    """(x, y, yaw) から waypoints [(x, y, yaw), ...] を順に通るときの [[t, x, y, yaw], ...] (DryRun.add_base と同じ動き方)"""
    t, track = 0.0, [[0.0, x, y, yaw]]
    for wx, wy, _wyaw in waypoints:
        dist = math.hypot(wx - x, wy - y)
        if dist > 1e-3:
            heading = math.atan2(wy - y, wx - x)
            turn = abs(wrap(heading - yaw))
            if turn > 1e-3:
                t += turn / angular
                track.append([round(t, 3), x, y, heading])
            t += dist / linear
            x, y, yaw = wx, wy, heading
            track.append([round(t, 3), x, y, yaw])
    last_yaw = waypoints[-1][2] if waypoints else yaw
    turn = abs(wrap(last_yaw - yaw))
    if turn > 1e-3:
        t += turn / angular
        track.append([round(t, 3), x, y, last_yaw])
    return [[p[0], round(float(p[1]), 4), round(float(p[2]), 4), round(float(p[3]), 4)] for p in track]


def top_down(x, y, z, yaw):
    """gripper_link が (x, y, z) で真下を向き、指が yaw 方向と直交して閉じるときの wrist_roll_link の姿勢"""
    m = tft.euler_matrix(0.0, math.pi / 2, yaw, "sxyz")  # Rz(yaw) * Ry(90°): gripper の x 軸 (進む向き) が真下
    m[0:3, 3] = [x, y, z + WRIST_TO_GRIPPER]
    return m


class DryRun:
    """計画だけするときの、仮のロボットの状態と、通しで再生するための時間軸。"""

    def __init__(self, base, joints, world):
        self.base = base            # world から見た仮の base_link (4x4)
        self.joints = dict(joints)  # 関節名 -> 値
        self.world = world          # 物体名 -> (world の 4x4, size)
        self.t = 0.0
        self.base_track = []        # (t, x, y, yaw)
        self.joint_track = []       # (t, {name: value})
        self.attached = []          # {"object", "t0", "t1", "link", "pose"}
        self.phases = []            # {"step_id", "phase", "t0", "t1"}
        self.step_id = None
        self.kind = None            # いま計画している skill ("pick" / "place")
        self.store = {}             # step_id -> {"pick": {phase: RobotTrajectory}, "place": {...}, "stops": {...}, ...}
        self.holding_rel = None     # 持っている物体の gripper_link から見た姿勢 (4x4)
        self.keyframe()

    # ---- 時間軸 ----
    def keyframe(self):
        self.base_track.append((self.t, float(self.base[0, 3]), float(self.base[1, 3]), float(yaw_of(self.base))))
        self.joint_track.append((self.t, dict(self.joints)))

    def phase(self, phase, t0):
        self.phases.append({"step_id": self.step_id, "phase": phase, "t0": round(t0, 3), "t1": round(self.t, 3)})

    def add_arm(self, phase, plan):
        t0 = self.t
        self.keyframe()
        jt = plan.joint_trajectory
        last = 0.0
        for p in jt.points:
            last = p.time_from_start.to_sec()
            self.joints.update(dict(zip(jt.joint_names, p.positions)))
            self.joint_track.append((t0 + last, dict(self.joints)))
        self.t = t0 + last
        self.keyframe()
        self.phase(phase, t0)
        if self.step_id is not None and self.kind is not None:
            self.store.setdefault(self.step_id, {}).setdefault(self.kind, {})[phase] = plan

    def add_gripper(self, phase, target, speed):
        t0 = self.t
        self.keyframe()
        delta = max([abs(v - self.joints.get(k, v)) for k, v in target.items()] or [0.0])
        self.joints.update(target)
        self.t = t0 + max(0.3, delta / speed)
        self.keyframe()
        self.phase(phase, t0)

    def add_base(self, waypoints, linear, angular):
        """waypoints: [(x, y, yaw), ...] (最後が止まる位置)。その場で向きを変えてから進み、最後に向きを合わせる。"""
        t0 = self.t
        self.keyframe()
        x, y, yaw = self.base[0, 3], self.base[1, 3], yaw_of(self.base)
        for wx, wy, wyaw in waypoints:
            dist = math.hypot(wx - x, wy - y)
            if dist > 1e-3:
                heading = math.atan2(wy - y, wx - x)
                turn = abs(wrap(heading - yaw))
                if turn > 1e-3:
                    self.t += turn / angular
                    self.base_track.append((self.t, x, y, heading))
                self.t += dist / linear
                x, y, yaw = wx, wy, heading
                self.base_track.append((self.t, x, y, yaw))
        last_yaw = waypoints[-1][2] if waypoints else yaw
        turn = abs(wrap(last_yaw - yaw))
        if turn > 1e-3:
            self.t += turn / angular
            self.base_track.append((self.t, x, y, last_yaw))
        self.base = planar(x, y, last_yaw, self.base[2, 3])
        self.keyframe()
        self.phase("navigating", t0)

    # ---- やり直し用 ----
    def checkpoint(self, server):
        return {
            "base": self.base.copy(), "joints": dict(self.joints), "world": dict(self.world), "t": self.t,
            "n_base": len(self.base_track), "n_joint": len(self.joint_track), "n_att": len(self.attached),
            "n_phase": len(self.phases), "store": copy.copy(self.store.get(self.step_id, {}).get(self.kind, {})),
            "holding_rel": None if self.holding_rel is None else self.holding_rel.copy(),
            "server": (server.holding, server.wrist_to_obj, server.obj_size, server.picked_from),
        }

    def restore(self, cp, server):
        self.base, self.joints, self.world, self.t = cp["base"], cp["joints"], cp["world"], cp["t"]
        del self.base_track[cp["n_base"]:]
        del self.joint_track[cp["n_joint"]:]
        del self.attached[cp["n_att"]:]
        del self.phases[cp["n_phase"]:]
        if self.step_id is not None and self.kind is not None:
            self.store.setdefault(self.step_id, {})[self.kind] = cp["store"]
        self.holding_rel = cp["holding_rel"]
        server.holding, server.wrist_to_obj, server.obj_size, server.picked_from = cp["server"]

    def timeline(self, joint_names, objects):
        duration = self.t
        joints = [[round(t, 3)] + [round(float(j.get(n, 0.0)), 5) for n in joint_names] for t, j in self.joint_track]
        return {
            "duration": round(duration, 3),
            "base": [[round(t, 3), round(x, 4), round(y, 4), round(yaw, 4)] for t, x, y, yaw in self.base_track],
            "base_z": round(float(self.base[2, 3]), 4),
            "joint_names": joint_names,
            "joints": joints,
            "attached": [dict(a, t1=a["t1"] if a["t1"] is not None else round(duration, 3)) for a in self.attached],
            "phases": self.phases,
            "objects": objects,
        }


class PickPlaceServer:
    def __init__(self):
        self.frame = rospy.get_param("~planning_frame", "base_link")
        self.approach = float(rospy.get_param("~approach_distance", 0.10))   # 上空からまっすぐ下ろす距離 [m]
        self.grasp_depth = float(rospy.get_param("~grasp_depth", 0.015))     # 箱の上面から gripper_link を下げる量 [m]
        self.place_clearance = float(rospy.get_param("~place_clearance", 0.005))  # 置くときに浮かせる量 [m]
        self.max_open = float(rospy.get_param("~gripper_max_open", 0.10))
        self.velocity = float(rospy.get_param("~velocity_scaling", 0.5))
        # 止まる位置の候補: 物体から standoffs [m] 離れ、(台車から物体への向き + angles [度]) の方向から物体を向く。
        # move_base の地図 (global costmap) が届いていれば、台車がぶつかる位置 (机に近すぎる) は候補から外す
        self.standoffs = [float(v) for v in rospy.get_param("~stop_standoffs", [0.55, 0.65, 0.75])]
        self.stop_angles = [float(v) for v in rospy.get_param(
            "~stop_angles", [0, -30, 30, -60, 60, -90, 90, -120, 120, -150, 150, 180])]
        self.max_stops = int(rospy.get_param("~max_stop_candidates", 8))
        # 台車が障害物に近すぎて動き出せないとき、まっすぐ離れてよい距離 [m]
        self.escape_max = float(rospy.get_param("~escape_max_distance", 0.6))
        # 今の位置のまま届くとみなす範囲 (base_link から見た物体の位置) [m]
        self.reach_x = [float(v) for v in rospy.get_param("~reach_x", [0.35, 0.8])]
        self.reach_y = float(rospy.get_param("~reach_y", 0.35))
        # 計画の時間軸で使う台車の速さ (move_base の実際の速さとは少し違う)
        self.nav_linear = float(rospy.get_param("~nav_linear_speed", 0.4))
        self.nav_angular = float(rospy.get_param("~nav_angular_speed", 0.8))
        self.finger_speed = float(rospy.get_param("~finger_speed", 0.05))
        # 計画どおりに再生してよい、止まる位置とのずれ [m], [rad]、関節角のずれ [rad]
        self.replay_tol_xy = float(rospy.get_param("~replay_tolerance_xy", 0.01))
        self.replay_tol_yaw = math.radians(float(rospy.get_param("~replay_tolerance_yaw_deg", 1.0)))
        self.replay_tol_joint = float(rospy.get_param("~replay_tolerance_joint", 0.02))
        # シミュレーション: move_base で着いたら、台車を止まる位置へぴったり置き直す (この距離以内なら)
        self.snap_base = bool(rospy.get_param("~snap_base", True))
        self.snap_max = float(rospy.get_param("~snap_max_distance", 0.25))
        self.world_frame = rospy.get_param("~world_frame", "world")
        ns = rospy.get_param("~move_base_ns", "move_base").rstrip("/")

        # 胴体 (torso) も使う。胴体を下げたままだと上からつかめるのは正面 0.65 m 程度まで
        group = rospy.get_param("~arm_group", "arm_with_torso")
        self.group_name = group
        self.arm = moveit_commander.MoveGroupCommander(group, wait_for_servers=60.0)
        self.arm.set_end_effector_link("wrist_roll_link")
        self.arm.set_pose_reference_frame(self.frame)
        self.arm.set_planning_time(float(rospy.get_param("~planning_time", 3.0)))
        self.arm.set_max_velocity_scaling_factor(self.velocity)
        self.arm.set_max_acceleration_scaling_factor(self.velocity)
        self.gripper = moveit_commander.MoveGroupCommander("gripper", wait_for_servers=60.0)
        self.gripper.set_max_velocity_scaling_factor(1.0)
        self.gripper.set_max_acceleration_scaling_factor(1.0)
        self.scene = moveit_commander.PlanningSceneInterface(synchronous=True)
        self.arm_joints = list(self.arm.get_active_joints())
        self.gripper_joints = list(self.gripper.get_active_joints())
        self.all_joints = self.arm_joints + self.gripper_joints

        self.fk_srv = rospy.ServiceProxy("/compute_fk", GetPositionFK)
        self.validity_srv = rospy.ServiceProxy("/check_state_validity", GetStateValidity)
        self.apply_scene_srv = rospy.ServiceProxy("/apply_planning_scene", ApplyPlanningScene)
        self.make_plan_srv = rospy.ServiceProxy(ns + "/make_plan", GetPlan)
        self.costmap = None  # move_base の global costmap (OccupancyGrid、値は 0..100。99 = 台車がはみ出る、100 = 障害物)
        self.costmap_data = None
        rospy.Subscriber(ns + "/global_costmap/costmap", OccupancyGrid, self.on_costmap, queue_size=1)
        rospy.Subscriber(ns + "/global_costmap/costmap_updates", OccupancyGridUpdate, self.on_costmap_update, queue_size=5)
        self.move_base = actionlib.SimpleActionClient(ns, MoveBaseAction)

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        self.lock = threading.Lock()
        self.stop_requested = False
        self.holding = None        # 手にくっついている物体名 (PREFIX なし)
        self.wrist_to_obj = None   # つかんだときの wrist_roll_link から見た箱の姿勢
        self.obj_size = None
        self.picked_from = None    # つかんだ元の場所 (frame_id, position, orientation)。place を省いたときに戻す先
        self.goal = None           # 実行中の skill の goal (dict)。/coground/pick_place/command から来たものは goal_id が ""
        self.dry = None            # 計画だけしている間の DryRun
        self.replay = None         # 計画どおりに動かすときの、phase -> 計画した軌道
        self.replay_log = []       # 計画し直した理由
        self.replay_used = 0
        self.prefer_yaw = None     # つかむ向きの第一候補 (計画どおりに動かすとき)
        self.plans = {}            # (plan_id, plan_version) -> {step_id: store}。直近 MAX_PLANS 個を持つ (単体テストの計画で本番の計画を消さない)
        self.world = {}            # Unity の物体: 名前 -> (world の 4x4, size)。/coground/scene/objects から
        # 家庭ルール: hold (台車を止めておく) と、進入禁止の範囲
        self.hold = False
        self.keepout = []          # いま地図に入れてある範囲 [{"id", "polygon"}]
        self.keepout_seq = 0
        self.keepout_ack = -1      # base_command_server が地図にし終えた seq
        self.keepout_lock = threading.Lock()
        self.keepout_wait = float(rospy.get_param("~keepout_wait", 3.0))  # 地図に反映されるのを待つ秒

        self.status_pub = rospy.Publisher("/coground/pick_place/status", String, queue_size=10, latch=True)
        self.held_pub = rospy.Publisher("/coground/pick_place/held", String, queue_size=1, latch=True)
        self.attached_pub = rospy.Publisher("/coground/pick_place/attached", String, queue_size=1, latch=True)
        self.feedback_pub = rospy.Publisher("/coground/skill/feedback", String, queue_size=50)
        self.state_pub = rospy.Publisher("/coground/skill/state", String, queue_size=1, latch=True)
        self.plan_feedback_pub = rospy.Publisher("/coground/task/plan_feedback", String, queue_size=20)
        self.plan_result_pub = rospy.Publisher("/coground/task/plan_result", String, queue_size=1, latch=True)
        self.freeze_pub = rospy.Publisher("/coground/scene/freeze", Bool, queue_size=1, latch=True)
        self.initial_pose_pub = rospy.Publisher("/coground/robot/initial_pose", PoseStamped, queue_size=1)
        self.reset_result_pub = rospy.Publisher("/coground/system/reset_result", String, queue_size=5)
        self.keepout_pub = rospy.Publisher("/coground/nav/keepout_zones", String, queue_size=1, latch=True)
        self.route_result_pub = rospy.Publisher("/coground/nav/route_result", String, queue_size=5)
        self.base_hold_pub = rospy.Publisher("/coground/base/hold", String, queue_size=1, latch=True)
        self.cmd_vel_pub = rospy.Publisher(rospy.get_param("~cmd_vel_topic", "/coground/base/cmd_vel"), Twist, queue_size=1)
        self.reset_wait = float(rospy.get_param("~reset_wait", 20.0))  # リセットで、動いている途中のスキルが止まるのを待つ秒

        # 前回の起動で手に残った物体を外す
        for name in self.scene.get_attached_objects().keys():
            if name.startswith(PREFIX):
                self.scene.remove_attached_object(name=name)
                self.scene.remove_world_object(name)
        self.held_pub.publish(String(""))
        self.attached_pub.publish(String(""))
        self.freeze_pub.publish(Bool(False))

        rospy.Subscriber("/coground/pick_place/command", String, self.on_command, queue_size=1)
        rospy.Subscriber("/coground/arm/stop", Empty, self.on_stop, queue_size=1)
        rospy.Subscriber("/coground/skill/goal", String, self.on_goal, queue_size=10)
        rospy.Subscriber("/coground/skill/cancel", String, self.on_cancel, queue_size=10)
        rospy.Subscriber("/coground/task/plan_request", String, self.on_plan_request, queue_size=1)
        rospy.Subscriber("/coground/scene/objects", MarkerArray, self.on_objects, queue_size=10)
        rospy.Subscriber("/coground/system/reset", String, self.on_reset, queue_size=1)
        rospy.Subscriber("/coground/skill/hold", String, self.on_hold, queue_size=10)
        rospy.Subscriber("/coground/nav/route_request", String, self.on_route_request, queue_size=5)
        rospy.Subscriber("/coground/nav/keepout_state", String, self.on_keepout_state, queue_size=5)
        rospy.Timer(rospy.Duration(1.0), lambda _e: self.publish_state())
        # 初期姿勢 = 起動したときの腕と指の関節角 (リセットでここへ戻す)
        try:
            self.home_joints = self.current_joints()
        except Exception as e:
            rospy.logwarn("[pick_place] 初期姿勢を覚えられなかった (リセットで腕を戻せない): %s", e)
            self.home_joints = {}
        self.status("ready")

    # ---- 共通 ----
    def status(self, state, detail=""):
        if self.dry is not None:
            if state in PHASES:
                self.plan_progress(f"{state} {detail}".strip())
            return
        text = f"{state}: {detail}" if detail else state
        self.status_pub.publish(String(text))
        rospy.loginfo("[pick_place] %s", text)
        goal = self.goal
        if goal is not None and state in PHASES:
            self.feedback(goal, "running", phase=state, detail=detail)

    def publish_held(self, name):
        if self.dry is None:
            self.held_pub.publish(String(name))

    def feedback(self, goal, state, phase=None, detail="", mode=None):
        self.feedback_pub.publish(String(json.dumps({
            "goal_id": goal.get("goal_id", ""), "skill": goal.get("skill", ""), "object": goal.get("object", ""),
            "state": state, "phase": phase, "detail": detail, "holding": self.holding, "mode": mode,
        }, ensure_ascii=False)))

    def publish_state(self):
        goal = self.goal
        self.state_pub.publish(String(json.dumps({
            "busy": goal is not None or self.dry is not None,
            "goal_id": goal.get("goal_id") if goal else None, "holding": self.holding, "hold": self.hold,
        }, ensure_ascii=False)))

    # ---- 家庭ルール: hold と進入禁止の範囲 ----
    def on_hold(self, msg):
        try:
            data = json.loads(msg.data or "{}")
            hold = bool(data.get("hold"))
            zones = self.parse_zones(data.get("keepout_zones"))
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            rospy.logwarn("[hold] 形式が不正: %s", e)
            return
        if hold:
            self.hold = True
            self.stop_base()  # move_base の goal は navigate のループが取り消す
            rospy.loginfo("[hold] 台車を止める: %s", data.get("reason") or "")
        else:
            if zones is not None:
                try:
                    self.set_keepout(zones)  # 範囲を替えてから再開する
                except Abort as e:
                    rospy.logwarn("[hold] %s (hold を解かない)", e)
                    return
            if self.hold:
                rospy.loginfo("[hold] 解く (避ける範囲: %s)", [z["id"] for z in self.keepout] or "なし")
            self.hold = False
        self.base_hold_pub.publish(String(json.dumps({"hold": self.hold})))
        self.publish_state()

    def stop_base(self):
        for _ in range(3):
            self.cmd_vel_pub.publish(Twist())

    def wait_hold(self):
        """hold の間、ここで待つ (stop されたら Abort)"""
        announced = False
        while self.hold:
            if self.stop_requested or rospy.is_shutdown():
                raise Abort("stopped")
            if not announced and self.dry is None:
                rospy.loginfo("[pick_place] hold 中 (家庭ルールにより台車を止めている)")
                announced = True
            rospy.sleep(0.05)

    @staticmethod
    def parse_zones(value):
        if value is None:
            return None
        zones = []
        for z in value:
            polygon = [[float(p[0]), float(p[1])] for p in z["polygon"]]
            if len(polygon) < 3:
                raise ValueError("keepout_zones polygon needs 3 or more points")
            zones.append({"id": str(z.get("id", "")), "polygon": polygon})
        return zones

    def on_keepout_state(self, msg):
        try:
            self.keepout_ack = int(json.loads(msg.data or "{}").get("seq", -1))
        except (ValueError, AttributeError, TypeError):
            pass

    def set_keepout(self, zones, wait=True):
        """進入禁止の範囲を置き換え、move_base の地図に反映されるのを待つ。同じなら何もしない"""
        with self.keepout_lock:
            if zones == self.keepout:
                return
            if self.keepout_seq == 0:
                self.keepout_seq = int(rospy.get_time() * 10) % 1000000  # 起動し直しても、前の seq と重ならないように
            self.keepout_seq += 1
            seq = self.keepout_seq
            self.keepout_pub.publish(String(json.dumps({"seq": seq, "zones": zones}, ensure_ascii=False)))
            if not wait:
                self.keepout = zones
                return
            deadline = rospy.get_time() + 2.0
            while self.keepout_ack != seq and rospy.get_time() < deadline and not rospy.is_shutdown():
                rospy.sleep(0.02)
            if self.keepout_ack != seq:
                if zones:
                    raise Abort("Can't put the no-entry areas into the map (base_command_server doesn't reply; start with NAV=true)")
                self.keepout = zones
                return
            removed = bool(self.keepout) and not all(z in zones for z in self.keepout)
            self.keepout = zones
            # costmap (2 層目の StaticLayer) に反映されるのを待つ。範囲の中の点が「通れない」になるまで
            probes = [(sum(p[0] for p in z["polygon"]) / len(z["polygon"]), sum(p[1] for p in z["polygon"]) / len(z["polygon"]))
                      for z in zones]
            rospy.sleep(0.4)
            deadline = rospy.get_time() + self.keepout_wait
            while rospy.get_time() < deadline and not rospy.is_shutdown():
                if all(self.cost_at(x, y) is None or self.cost_at(x, y) >= 99 or self.cost_at(x, y) == -2 for x, y in probes):
                    break
                rospy.sleep(0.05)
            else:
                if probes:
                    rospy.logwarn("[keepout] %.0f 秒待っても地図に反映されない (keepout_layer は入っているか)", self.keepout_wait)
            if removed:
                rospy.sleep(0.6)  # 消した範囲が地図から消えるのを待つ
            rospy.loginfo("[keepout] 避ける範囲: %s", [z["id"] for z in zones] or "なし")

    def on_route_request(self, msg):
        threading.Thread(target=self.run_route, args=(msg.data,), daemon=True).start()

    def run_route(self, text):
        """今の位置から goal までの経路だけを計画する (台車は動かさない)"""
        result = {"route_id": "", "ok": False, "reason": "", "base": []}
        try:
            req = json.loads(text)
            result["route_id"] = str(req.get("route_id", ""))
            goal = tuple(float(v) for v in req["goal"])
            zones = self.parse_zones(req.get("keepout_zones"))
            if len(goal) != 3:
                raise ValueError("goal is [x, y, yaw]")
            if self.dry is not None:
                raise Abort("Motion planning in progress")
            if zones is not None:
                self.set_keepout(zones)
            base = self.base_world()
            start = (float(base[0, 3]), float(base[1, 3]), float(yaw_of(base)))
            path = self.nav_path(start, goal)
            result["base"] = base_track(start[0], start[1], start[2], path, self.nav_linear, self.nav_angular)
            result["ok"] = True
        except Abort as e:
            result["reason"] = str(e)
        except (ValueError, KeyError, TypeError) as e:
            result["reason"] = f"invalid route_request format: {e}"
        except Exception as e:
            rospy.logerr("[route] %s", e, exc_info=True)
            result["reason"] = f"internal error: {e}"
        rospy.loginfo("[route] %s: %s %s", result["route_id"], "ok" if result["ok"] else "できない", result["reason"])
        self.route_result_pub.publish(String(json.dumps(result, ensure_ascii=False)))

    def on_stop(self, _msg):
        self.stop_requested = True
        if self.goal is not None:
            try:
                self.arm.stop()  # 動いている途中の軌道も止める
            except Exception as e:
                rospy.logwarn("[pick_place] stop: %s", e)

    def on_cancel(self, msg):
        try:
            goal_id = json.loads(msg.data or "{}").get("goal_id") or ""
        except (ValueError, AttributeError):
            goal_id = ""
        goal = self.goal
        if goal is not None and (not goal_id or goal_id == goal.get("goal_id")):
            self.on_stop(None)

    def check_stop(self):
        if self.stop_requested:
            raise Abort("stopped")

    def on_objects(self, msg):
        for m in msg.markers:
            name = m.text or f"{m.ns}_{m.id}"
            if m.action == Marker.DELETE:
                self.world.pop(name, None)
                continue
            if m.type != Marker.CUBE or (m.header.frame_id or "world") != self.world_frame:
                continue
            size = (abs(m.scale.x), abs(m.scale.y), abs(m.scale.z))
            if min(size) > 0.0:
                self.world[name] = (pose_to_matrix(m.pose), size)

    # ---- リセット (Web UI の「まっさら」= grounding_server の system.reset) ----
    def on_reset(self, msg):
        """動いていれば止め、持っている物・計画・latch した古い値を消し、腕を初期姿勢へ戻す。
        終わったら /coground/system/reset_result に {"reset_id", "ok", "detail"} を出す。"""
        try:
            reset_id = str(json.loads(msg.data or "{}").get("reset_id", ""))
        except (ValueError, AttributeError):
            reset_id = ""
        rospy.loginfo("[reset] %s: 受け取った", reset_id)
        self.stop_requested = True
        if self.goal is not None:
            try:
                self.arm.stop()
                self.move_base.cancel_all_goals()
            except Exception as e:
                rospy.logwarn("[reset] stop: %s", e)
        got = self.lock.acquire(timeout=self.reset_wait)
        ok, detail = False, f"running skill / plan didn't stop within {self.reset_wait:.0f} s"
        try:
            if got:
                self.stop_requested = False
                self.holding, self.wrist_to_obj, self.obj_size, self.picked_from = None, None, None, None
                self.replay, self.replay_log, self.prefer_yaw = None, [], None
                self.hold = False
                self.base_hold_pub.publish(String(json.dumps({"hold": False})))
                self.set_keepout([], wait=False)
                self.plans.clear()
                for name in self.scene.get_attached_objects().keys():
                    if name.startswith(PREFIX):
                        self.scene.remove_attached_object(name=name)
                        self.scene.remove_world_object(name)  # scene_sync が Unity の位置で置き直す
                self.held_pub.publish(String(""))
                self.attached_pub.publish(String(""))
                self.freeze_pub.publish(Bool(False))
                # latch している古い計画を消す (Unity の Ghost も消える)
                self.publish_plan_result({"plan_id": "", "plan_version": 0, "error": "", "steps": [], "timeline": None})
                ok, detail = self.go_home()
                self.status("ready", "reset done" if ok else f"reset: {detail}")
        except Exception as e:
            rospy.logerr("[reset] %s", e, exc_info=True)
            ok, detail = False, f"internal error: {e}"
        finally:
            if got:
                self.lock.release()
            self.publish_state()
            self.reset_result_pub.publish(String(json.dumps({"reset_id": reset_id, "ok": ok, "detail": detail},
                                                            ensure_ascii=False)))
            rospy.loginfo("[reset] %s: %s %s", reset_id, "ok" if ok else "failed", detail)

    def go_home(self):
        """腕と指を初期姿勢 (起動したときの関節角) へ戻す。(ok, 理由)"""
        if not self.home_joints:
            return False, "initial pose unknown"
        arm = {n: self.home_joints[n] for n in self.arm_joints if n in self.home_joints}
        now = self.current_joints()
        if max((abs(now.get(n, v) - v) for n, v in arm.items()), default=0.0) > 1e-3:
            self.arm.set_start_state_to_current_state()
            self.arm.set_joint_value_target(arm)
            planned, plan, _, _ = self.arm.plan()
            self.arm.clear_pose_targets()
            if not planned:
                return False, "can't plan returning the arm to the initial pose (collision?)"
            if not self.arm.execute(plan, wait=True):
                self.arm.stop()
                return False, "couldn't return the arm to the initial pose"
            self.arm.stop()
        grip = {n: self.home_joints[n] for n in self.gripper_joints if n in self.home_joints}
        if grip:
            self.gripper.go(grip, wait=True)
            self.gripper.stop()
        return True, ""

    # ---- 状態 (実物か、計画中の仮のものか) ----
    def current_joints(self):
        if self.dry is not None:
            return dict(self.dry.joints)
        joints = dict(zip(self.arm_joints, self.arm.get_current_joint_values()))
        joints.update(zip(self.gripper_joints, self.gripper.get_current_joint_values()))
        return joints

    def state_msg(self, joints=None):
        joints = self.current_joints() if joints is None else joints
        names = [n for n in self.all_joints if n in joints]
        return RobotState(joint_state=JointState(name=names, position=[joints[n] for n in names]), is_diff=True)

    def set_start(self):
        if self.dry is not None:
            self.arm.set_start_state(self.state_msg())
        else:
            self.arm.set_start_state_to_current_state()

    def fk(self, link):
        req = GetPositionFKRequest()
        req.header.frame_id = self.frame
        req.fk_link_names = [link]
        req.robot_state = self.state_msg()
        res = self.fk_srv(req)
        if res.error_code.val != 1 or not res.pose_stamped:
            raise Abort(f"forward kinematics ({link}) failed: {res.error_code.val}")
        return pose_to_matrix(res.pose_stamped[0].pose)

    def current_wrist(self):
        if self.dry is not None:
            return self.fk("wrist_roll_link")
        pose = self.arm.get_current_pose("wrist_roll_link")
        if pose.header.frame_id != self.frame:
            pose.header.stamp = rospy.Time(0)
            pose = self.tf_buffer.transform(pose, self.frame, rospy.Duration(1.0))
        return pose_to_matrix(pose.pose)

    def base_world(self):
        """world から見た base_link (4x4)"""
        if self.dry is not None:
            return self.dry.base
        try:
            t = self.tf_buffer.lookup_transform(self.world_frame, self.frame, rospy.Time(0), rospy.Duration(1.0))
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
            raise Abort(f"can't get the base pose: {e}")
        tr, q = t.transform.translation, t.transform.rotation
        m = tft.quaternion_matrix([q.x, q.y, q.z, q.w])
        m[0:3, 3] = [tr.x, tr.y, tr.z]
        return m

    # ---- 腕と指 ----
    def run_arm(self, phase, make):
        """phase の軌道を作って動かす。計画中は動かさずに記録する。計画どおりに動かすときは、覚えている軌道を先に試す。"""
        self.check_stop()
        if self.dry is not None:
            plan = make()
            if plan is not None:
                self.dry.add_arm(phase, plan)
            return plan
        plan = None
        stored = self.replay.pop(phase, None) if self.replay is not None else None
        if stored is not None:
            ok, why = self.replay_ok(stored)
            if ok:
                plan = stored
                self.replay_used += 1
            else:
                self.replay_log.append(f"{phase}: {why}")
        if plan is None:
            plan = make()
        if plan is None:
            return None
        self.execute(plan, phase)
        return plan

    def replay_ok(self, plan):
        jt = plan.joint_trajectory
        if not jt.points:
            return False, "empty trajectory"
        now = self.current_joints()
        diff = max(abs(now.get(n, p) - p) for n, p in zip(jt.joint_names, jt.points[0].positions))
        if diff > self.replay_tol_joint:
            return False, f"start joint angles are off by {diff:.3f} rad"
        step = max(1, len(jt.points) // 15)
        for i in list(range(0, len(jt.points), step)) + [len(jt.points) - 1]:
            joints = dict(now)
            joints.update(zip(jt.joint_names, jt.points[i].positions))
            req = GetStateValidityRequest(robot_state=self.state_msg(joints), group_name=self.group_name)
            try:
                if not self.validity_srv(req).valid:
                    return False, "collides in the current scene"
            except rospy.ServiceException as e:
                return False, f"can't check collisions: {e}"
        return True, ""

    def execute(self, plan, what):
        self.check_stop()
        if not self.arm.execute(plan, wait=True):
            self.arm.stop()
            raise Abort(f"{what}: execution failed" + (" (stop)" if self.stop_requested else ""))
        self.arm.stop()

    def plan_to(self, wrist_m):
        self.set_start()
        target = PoseStamped()
        target.header.frame_id = self.frame
        target.pose = matrix_to_pose(wrist_m)
        self.arm.set_pose_target(target)
        ok, plan, _, _ = self.arm.plan()
        self.arm.clear_pose_targets()
        return plan if ok else None

    def cartesian(self, dz, avoid_collisions):
        self.set_start()
        pose = matrix_to_pose(self.current_wrist())
        pose.position.z += dz
        plan, fraction = self.arm.compute_cartesian_path([pose], 0.005, avoid_collisions=avoid_collisions)
        if fraction < 0.95:
            self.cartesian_fraction = fraction
            return None
        ref = self.state_msg() if self.dry is not None else self.arm.get_current_state()
        return self.arm.retime_trajectory(ref, plan, velocity_scaling_factor=self.velocity,
                                          acceleration_scaling_factor=self.velocity)

    def straight(self, dz, what, phase, avoid_collisions=True):
        """手先を真上 / 真下に dz [m] 動かす"""
        self.cartesian_fraction = 0.0
        if self.run_arm(phase, lambda: self.cartesian(dz, avoid_collisions)) is None:
            raise Abort(f"{what}: can't move in a straight line (achieved {self.cartesian_fraction:.0%})")

    def set_gripper(self, width, phase):
        self.check_stop()
        finger = min(max(width / 2.0, 0.0), self.max_open / 2.0)
        target = {j: finger for j in self.gripper_joints}
        if self.dry is not None:
            self.dry.add_gripper(phase, target, self.finger_speed)
            return
        self.gripper.go(target, wait=True)
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
            raise Abort(f"frame of {oid} is {co.header.frame_id} (should be {self.frame})")
        return m, list(co.primitives[0].dimensions)

    def to_planning_frame(self, frame_id, position, orientation):
        if self.dry is not None and frame_id == self.world_frame:
            return np.linalg.inv(self.dry.base).dot(dict_to_matrix({"position": position, "orientation": orientation}))
        ps = PoseStamped()
        ps.header.frame_id = frame_id
        ps.header.stamp = rospy.Time(0)
        ps.pose.position.x, ps.pose.position.y, ps.pose.position.z = position
        ps.pose.orientation.x, ps.pose.orientation.y, ps.pose.orientation.z, ps.pose.orientation.w = orientation
        try:
            return pose_to_matrix(self.tf_buffer.transform(ps, self.frame, rospy.Duration(1.0)).pose)
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
            raise Abort(f"TF {frame_id} -> {self.frame}: {e}")

    def remember_pose(self, obj):
        """planning frame の行列 -> (frame_id, position, orientation)。台車が動いても使えるよう、できれば world で持つ"""
        if self.dry is not None:
            d = matrix_to_dict(self.dry.base.dot(obj))
            return self.world_frame, d["position"], d["orientation"]
        ps = PoseStamped()
        ps.header.frame_id = self.frame
        ps.header.stamp = rospy.Time(0)
        ps.pose = matrix_to_pose(obj)
        try:
            ps = self.tf_buffer.transform(ps, self.world_frame, rospy.Duration(1.0))
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException):
            pass  # world が無ければ planning frame のまま
        p, q = ps.pose.position, ps.pose.orientation
        return ps.header.frame_id, [p.x, p.y, p.z], [q.x, q.y, q.z, q.w]

    # ---- 台車 ----
    def navigate(self, x, y, yaw):
        """台車を (x, y, yaw) [world] へ動かす。着いたら (シミュレーションでは) ぴったり置き直す。"""
        base = self.base_world()
        if math.hypot(base[0, 3] - x, base[1, 3] - y) <= self.replay_tol_xy and \
                abs(wrap(yaw_of(base) - yaw)) <= self.replay_tol_yaw:
            return
        self.status("navigating", f"({x:.2f}, {y:.2f})")
        if not self.move_base.wait_for_server(rospy.Duration(2.0)):
            raise Abort("no move_base (start with NAV=true)")
        while True:
            self.wait_hold()  # hold の間は goal を送らない
            base = self.base_world()
            bx, by, byaw = base[0, 3], base[1, 3], yaw_of(base)
            if not self.free(bx, by):
                # 障害物に近すぎると move_base は動き出せない。計画と同じく、まっすぐ離れてから
                esc = self.escape_point(bx, by, byaw)
                if esc is None or not self.snap_base:
                    raise Abort(f"the base's current position is {self.describe_cost(self.cost_at(bx, by))}, so it can't start moving")
                self.slide_base(base, esc[0], esc[1])
            goal = MoveBaseGoal()
            goal.target_pose.header.frame_id = self.world_frame
            goal.target_pose.header.stamp = rospy.Time.now()
            goal.target_pose.pose = matrix_to_pose(planar(x, y, yaw))
            self.move_base.send_goal(goal)
            held = False
            while not self.move_base.wait_for_result(rospy.Duration(0.05)):
                if self.stop_requested or rospy.is_shutdown():
                    self.move_base.cancel_goal()
                    raise Abort("stopped")
                if self.hold:
                    # hold: goal を取り消して止まる。スキルは続いていて、hold が解けたら今の位置から送り直す
                    self.move_base.cancel_goal()
                    self.stop_base()
                    held = True
                    break
            if held:
                self.move_base.wait_for_result(rospy.Duration(1.0))  # 取り消しが済むのを待つ
                self.stop_base()
                continue
            state = self.move_base.get_state()
            if state != GoalStatus.SUCCEEDED:
                raise Abort(f"move failed (move_base: {state})")
            break
        self.wait_hold()  # 着いたあとの置き直しも、hold の間はしない
        base = self.base_world()
        error = math.hypot(base[0, 3] - x, base[1, 3] - y)
        if self.snap_base and error <= self.snap_max:
            ps = PoseStamped()
            ps.header.frame_id = self.world_frame
            ps.header.stamp = rospy.Time.now()
            ps.pose = matrix_to_pose(planar(x, y, yaw, base[2, 3]))
            self.initial_pose_pub.publish(ps)
            rospy.sleep(0.3)  # TF が新しい位置になるのを待つ

    # ---- 台車の地図 (move_base の global costmap) ----
    def on_costmap(self, msg):
        self.costmap = msg.info
        self.costmap_data = np.array(msg.data, dtype=np.int16).reshape(msg.info.height, msg.info.width)
        rospy.loginfo_once("[pick_place] move_base の地図を受け取った: %dx%d, %.2f m/セル",
                           msg.info.width, msg.info.height, msg.info.resolution)

    def on_costmap_update(self, msg):
        data = self.costmap_data
        if data is None:
            return
        try:
            data[msg.y:msg.y + msg.height, msg.x:msg.x + msg.width] = \
                np.array(msg.data, dtype=np.int16).reshape(msg.height, msg.width)
        except ValueError:
            pass

    def cost_at(self, x, y):
        """world (x, y) の costmap の値。地図が無ければ None、地図の外なら -2"""
        info, data = self.costmap, self.costmap_data
        if info is None or data is None:
            return None
        o = info.origin.position  # global costmap は world に置いている (回転なし)
        i, j = int(math.floor((x - o.x) / info.resolution)), int(math.floor((y - o.y) / info.resolution))
        if not (0 <= i < info.width and 0 <= j < info.height):
            return -2
        return int(data[j, i])

    def free(self, x, y):
        """台車の中心をそこに置いてもぶつからない (地図が無いときは分からないので True)"""
        c = self.cost_at(x, y)
        return c is None or 0 <= c < 99

    @staticmethod
    def describe_cost(c):
        return {None: "without a map", -2: "outside the map", -1: "unknown", 99: "too close to an obstacle", 100: "on an obstacle"}.get(c, f"cost {c}")

    def escape_point(self, x, y, yaw):
        """(x, y) が障害物に近すぎるとき、まっすぐ離れて抜け出せる一番近い位置。無ければ None"""
        step = 0.05
        dirs = sorted(range(0, 360, 20), key=lambda a: abs(wrap(math.radians(a) - (yaw + math.pi))))
        for k in range(1, int(self.escape_max / step) + 1):
            r = k * step
            for a in dirs:
                th = math.radians(a)
                ex, ey = x + r * math.cos(th), y + r * math.sin(th)
                if not self.free(ex, ey):
                    continue
                # 途中で障害物 (100) を通らないこと
                if all(self.cost_at(x + f * (ex - x), y + f * (ey - y)) != 100 for f in np.linspace(0, 1, 10)):
                    return ex, ey
        return None

    def slide_base(self, base, x, y):
        """(シミュレーションだけ) 台車をまっすぐ (x, y) へ少しずつ置き直す。向きは変えない"""
        sx, sy, yaw, z = base[0, 3], base[1, 3], yaw_of(base), base[2, 3]
        n = max(1, int(math.hypot(x - sx, y - sy) / self.nav_linear * 10))
        rate = rospy.Rate(10)
        for k in range(1, n + 1):
            if self.stop_requested:
                raise Abort("stopped")
            self.wait_hold()  # hold の間は、置き直しでも動かさない
            ps = PoseStamped()
            ps.header.frame_id = self.world_frame
            ps.header.stamp = rospy.Time.now()
            ps.pose = matrix_to_pose(planar(sx + (x - sx) * k / n, sy + (y - sy) * k / n, yaw, z))
            self.initial_pose_pub.publish(ps)
            rate.sleep()
        rospy.sleep(0.3)

    def nav_path(self, start, goal):
        """make_plan の経路 [(x, y, yaw), ...] (最後が goal)。通れなければ Abort (理由つき)。
        出発点が障害物に近すぎるときは、まずまっすぐ離れる (経路の先頭にその点が入る)"""
        if not self.free(goal[0], goal[1]):
            raise Abort(f"the stop position is {self.describe_cost(self.cost_at(goal[0], goal[1]))}")
        head = []
        if not self.free(start[0], start[1]):
            esc = self.escape_point(*start)
            if esc is None:
                raise Abort(f"the base's current position is {self.describe_cost(self.cost_at(start[0], start[1]))}, and "
                            f"there's nowhere to escape to within {self.escape_max:.1f} m")
            head = [(esc[0], esc[1], 0.0)]
            start = (esc[0], esc[1], start[2])
        req = GetPlanRequest(tolerance=0.0)
        for ps, (x, y, yaw) in ((req.start, start), (req.goal, goal)):
            ps.header.frame_id = self.world_frame
            ps.header.stamp = rospy.Time.now()
            ps.pose = matrix_to_pose(planar(x, y, yaw))
        try:
            res = self.make_plan_srv(req)
        except rospy.ServiceException as e:
            rospy.logwarn("[plan] make_plan: %s", e)
            raise Abort(f"move_base's make_plan is unavailable: {e}")
        if not res.plan.poses:
            raise Abort("move_base can't find a path (start %s, stop position %s)" % (
                self.describe_cost(self.cost_at(start[0], start[1])), self.describe_cost(self.cost_at(goal[0], goal[1]))))
        points, last = list(head), None
        for p in res.plan.poses:  # 10 cm ごとに間引く
            xy = (p.pose.position.x, p.pose.position.y)
            if last is None or math.hypot(xy[0] - last[0], xy[1] - last[1]) >= 0.1:
                points.append((xy[0], xy[1], 0.0))
                last = xy
        points.append(goal)
        return points

    def nav_available(self):
        try:
            self.make_plan_srv.wait_for_service(0.5)
            return True
        except rospy.ROSException:
            return False

    # ---- 指令 ----
    def on_command(self, msg):
        """従来の指令 (pick と place を続けて行う)"""
        try:
            goal = self.parse_goal(json.loads(msg.data), default_skill="pick_place")
            if goal["skill"] != "pick_place" or goal["place"] is None:
                raise ValueError("place is missing")
        except (ValueError, KeyError, TypeError) as e:
            self.status("rejected", f"invalid command format: {e}")
            return
        self.start(goal)

    def on_goal(self, msg):
        try:
            data = json.loads(msg.data)
        except ValueError as e:
            rospy.logwarn("[pick_place] goal が JSON ではない: %s", e)
            return
        try:
            goal = self.parse_goal(data)
        except (ValueError, KeyError, TypeError) as e:
            bad = data if isinstance(data, dict) else {}
            self.feedback({"goal_id": str(bad.get("goal_id", "")), "skill": str(bad.get("skill", "")),
                           "object": str(bad.get("object", ""))}, "rejected", detail=f"invalid goal format: {e}")
            return
        self.start(goal)

    @staticmethod
    def parse_place(place):
        if place is None:
            return None
        orientation = place.get("orientation")
        place = {"position": [float(v) for v in place["position"]],
                 "orientation": [float(v) for v in orientation] if orientation else None}
        if len(place["position"]) != 3 or (place["orientation"] and len(place["orientation"]) != 4):
            raise ValueError("position needs 3 numbers, orientation 4")
        return place

    @classmethod
    def parse_goal(cls, data, default_skill=None):
        skill = data.get("skill", default_skill)
        if skill not in SKILLS:
            raise ValueError(f"skill {skill!r} is none of {list(SKILLS)}")
        place = cls.parse_place(data.get("place"))
        if skill == "pick_place" and place is None:
            raise ValueError("pick_place requires place")
        pose = data.get("pose")
        if skill == "navigate":
            pose = [float(v) for v in pose]
            if len(pose) != 3:
                raise ValueError("navigate pose is [x, y, yaw]")
        ref = data.get("plan_ref")
        if ref is not None:
            ref = (str(ref["plan_id"]), int(ref["plan_version"]), str(ref["step_id"]))
        return {"goal_id": str(data.get("goal_id", "")), "skill": skill, "object": str(data.get("object", "")),
                "frame_id": data.get("frame_id") or "world", "place": place, "pose": pose, "plan_ref": ref,
                "keepout_zones": cls.parse_zones(data.get("keepout_zones"))}

    def start(self, goal):
        if not self.lock.acquire(blocking=False):
            self.status("rejected", "busy")
            self.feedback(goal, "rejected", detail="busy")
            return
        self.stop_requested = False
        self.goal = goal
        threading.Thread(target=self.run_goal, args=(goal,), daemon=True).start()

    def stored_step(self, ref):
        if ref is None:
            return None
        return self.plans.get(ref[:2], {}).get(ref[2])

    def begin_replay(self, stored, kind):
        """計画どおりに動かす準備。台車が止まる位置からずれていれば、計画し直す"""
        self.replay, self.replay_log, self.replay_used, self.prefer_yaw = None, [], 0, None
        if stored is None or kind not in stored:
            return
        stop = stored.get("stops", {}).get(kind)
        if stop is not None:
            base = self.base_world()
            d, dyaw = math.hypot(base[0, 3] - stop[0], base[1, 3] - stop[1]), abs(wrap(yaw_of(base) - stop[2]))
            if d > self.replay_tol_xy or dyaw > self.replay_tol_yaw:
                self.replay_log.append(f"the base is off from the stop position by {d * 100:.1f} cm / {math.degrees(dyaw):.1f}°")
                return
        self.replay = dict(stored[kind])
        self.prefer_yaw = stored.get("grasp_yaw") if kind == "pick" else None

    def run_goal(self, goal):
        """lock を持った状態で呼ばれる (別スレッド)。終わったら lock を外す"""
        name, skill = goal["object"], goal["skill"]
        self.publish_state()
        self.feedback(goal, "accepted")
        self.status("accepted", name or skill)  # Unity の順番待ちは、これを見てからの終わりの状態をこの指令の結果とみなす
        result, detail, mode = "failed", "", None
        stored = self.stored_step(goal["plan_ref"])
        try:
            if skill == "navigate":
                self.set_keepout(goal.get("keepout_zones") or [])  # 避ける範囲 (省略時はなし)
                self.navigate(*goal["pose"])
            else:
                if self.holding is not None and self.holding != name:
                    raise Abort(f"holding {self.holding}, so can't handle {name}")
                if skill in ("pick", "pick_place") and self.holding is None:
                    self.begin_replay(stored, "pick")
                    self.pick(name)
                if skill in ("place", "pick_place"):
                    if self.holding is None:
                        raise Abort(f"not holding {name}, so can't place it")
                    place = goal["place"]
                    if place is None:
                        if self.picked_from is None:
                            raise Abort("where it was grasped is unknown, so place must be specified")
                        frame_id, position, orientation = self.picked_from
                    else:
                        frame_id, position, orientation = goal["frame_id"], place["position"], place["orientation"]
                    if skill == "place":
                        self.begin_replay(stored, "place")
                    self.place(name, frame_id, position, orientation)
            result = "succeeded"
            if goal["plan_ref"] is not None and skill != "navigate":
                mode = "replanned" if self.replay_log or stored is None else "replay"
                detail = "; ".join(self.replay_log) if self.replay_log else ("" if stored else "plan not found")
            self.status("succeeded", name or skill)
        except Abort as e:
            if skill != "navigate":
                self.arm.stop()
            result, detail = ("canceled" if self.stop_requested else "failed"), str(e)
            self.status("failed", detail)
        except Exception as e:  # 想定外でもロックを外して次の指令を受けられるようにする
            rospy.logerr("[pick_place] %s", e, exc_info=True)
            detail = f"internal error: {e}"
            self.status("failed", detail)
        finally:
            self.replay, self.prefer_yaw = None, None
            if self.holding is None:
                self.held_pub.publish(String(""))
            self.goal = None
            self.lock.release()
            self.feedback(goal, result, detail=detail, mode=mode)
            self.publish_state()

    # ---- ピックとプレース (実行・計画・再生で共通) ----
    def pick(self, name):
        oid = PREFIX + name
        obj, size = self.object_in_scene(oid)
        if obj is None:
            raise Abort(f"{oid} is not in the Planning Scene (check Unity's MoveItCollisionBox)")
        if abs(obj[2, 2]) < 0.99:
            raise Abort(f"{name} is tilted (it can only be grasped from above in its resting orientation)")

        # つかみ方の候補: 箱の辺に合わせて 90° ずつ。指の間に入る向きだけ、ロボットの正面に近い順
        candidates = []
        for k in range(4):
            yaw = wrap(yaw_of(obj) + k * math.pi / 2)
            width = size[1] if k % 2 == 0 else size[0]  # 指が閉じる方向 (gripper の y 軸) の幅
            if width < self.max_open - 0.01:
                order = abs(yaw) if self.prefer_yaw is None else abs(wrap(yaw - self.prefer_yaw))
                candidates.append((order, yaw, width))
        if not candidates:
            raise Abort(f"{name} doesn't fit between the fingers ({self.max_open * 100:.0f} cm): {size}")
        candidates.sort()

        cx, cy, cz = obj[0:3, 3]
        grip_z = cz + size[2] / 2 - min(self.grasp_depth, size[2] / 2)

        self.publish_held(name)
        self.status("opening", name)
        self.set_gripper(self.max_open, "opening")

        for _, yaw, width in candidates:
            grasp = top_down(cx, cy, grip_z, yaw)
            above = grasp.copy()
            above[2, 3] += self.approach
            self.status("approaching", f"{name} (yaw {math.degrees(yaw):.0f}°)")
            if self.run_arm("approaching", lambda: self.plan_to(above)) is None:
                continue

            # 指が箱に触れるので、下ろす前に Planning Scene から外す
            self.scene.remove_world_object(oid)
            self.status("descending", name)
            try:
                self.straight(-self.approach, "lower", "descending")
            except Abort:
                if self.stop_requested:
                    raise
                # 下ろせない (机に当たるなど)。上空にいるので次の向きを試す。物体は scene_sync が戻す
                if self.dry is not None:
                    self.apply_virtual_scene()
                else:
                    self.held_pub.publish(String(""))
                    rospy.sleep(0.5)
                    self.held_pub.publish(String(name))
                continue

            self.status("grasping", name)
            # 箱の幅まで閉じる (疑似実行では力が無いので、0 まで閉じると Unity で指が箱にめり込む)
            self.set_gripper(max(width - 0.002, 0.0), "grasping")
            self.attach(oid, obj, size)
            self.holding = name
            self.obj_size = size
            self.wrist_to_obj = np.linalg.inv(grasp).dot(obj)
            self.picked_from = self.remember_pose(obj)
            if self.dry is not None:
                self.dry.store.setdefault(self.dry.step_id, {})["grasp_yaw"] = yaw
            else:
                self.attached_pub.publish(String(name))

            self.status("lifting", name)
            self.straight(self.approach, "lift", "lifting")
            return
        raise Abort(f"no heading from which {name} can be grasped (the arm can't reach / hits the desk)")

    def attach(self, oid, obj, size):
        if self.dry is None:
            obj_pose = PoseStamped()
            obj_pose.header.frame_id = self.frame
            obj_pose.pose = matrix_to_pose(obj)
            self.scene.attach_box("gripper_link", oid, obj_pose, size, touch_links=TOUCH_LINKS)
            return
        # 計画中: 仮の姿勢の手に付ける (planning frame で渡すと、実物の手の位置で付いてしまう)
        rel = np.linalg.inv(self.fk("gripper_link")).dot(obj)
        self.dry.holding_rel = rel
        self.attach_rel(oid, rel, size)
        self.dry.attached.append({"object": oid[len(PREFIX):], "t0": round(self.dry.t, 3), "t1": None,
                                  "link": "gripper_link", "pose": matrix_to_dict(rel)})

    def attach_rel(self, oid, rel, size):
        ps = PoseStamped()
        ps.header.frame_id = "gripper_link"
        ps.pose = matrix_to_pose(rel)
        self.scene.attach_box("gripper_link", oid, ps, size, touch_links=TOUCH_LINKS)

    def place(self, name, frame_id, position, orientation, rest=None):
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
        placed = None
        for turn in turns:
            obj_target = target.dot(tft.rotation_matrix(turn, (0, 0, 1)))
            wrist = obj_target.dot(np.linalg.inv(self.wrist_to_obj))
            above = wrist.copy()
            above[2, 3] += self.approach
            self.status("moving", f"{name} over the placement")
            if self.run_arm("moving", lambda: self.plan_to(above)) is None:
                continue
            self.status("lowering", name)
            self.straight(-self.approach, "lower", "lowering")
            placed = obj_target
            break
        if placed is None:
            raise Abort(f"can't reach the placement / collides ({name} still in hand)")

        self.status("releasing", name)
        self.set_gripper(self.max_open, "releasing")
        self.scene.remove_attached_object("gripper_link", oid)  # MoveIt では今の位置に置いた物体になる
        self.holding = None
        if self.dry is not None:
            # 計画中: 物体は「落ちたあと」の位置に置き直す (MoveIt は実物の手の位置に置いてしまうので消してから)
            self.scene.remove_world_object(oid)
            rest_w = dict_to_matrix(rest) if rest is not None else self.dry.base.dot(placed)
            self.dry.world[name] = (rest_w, self.dry.world[name][1] if name in self.dry.world else tuple(self.obj_size))
            self.dry.holding_rel = None
            for a in self.dry.attached:
                if a["object"] == name and a["t1"] is None:
                    a["t1"] = round(self.dry.t, 3)
            self.apply_virtual_scene()
        else:
            self.attached_pub.publish(String(""))

        self.status("retreating", name)
        try:
            self.straight(self.approach, "pull up", "retreating")
        except Abort:
            if self.stop_requested:
                raise
            self.straight(self.approach, "pull up", "retreating", avoid_collisions=False)  # 真上なので安全
        self.publish_held("")  # 以後は Unity の位置で scene_sync が更新する

    # ---- 計画 ----
    def plan_progress(self, detail):
        dry = self.dry
        self.plan_feedback_pub.publish(String(json.dumps({
            "plan_id": getattr(self, "_plan_id", ""), "plan_version": getattr(self, "_plan_version", 0),
            "step_id": dry.step_id if dry else None, "detail": detail}, ensure_ascii=False)))

    def on_plan_request(self, msg):
        try:
            req = json.loads(msg.data)
            plan_id, version = str(req["plan_id"]), int(req["plan_version"])
            steps = [self.parse_plan_step(s) for s in req.get("steps") or []]
            keepout = self.parse_zones(req.get("keepout_zones")) or []
        except (ValueError, KeyError, TypeError) as e:
            rospy.logwarn("[plan] plan_request の形式が不正: %s", e)
            self.publish_plan_result({"plan_id": "", "plan_version": 0, "error": f"invalid plan_request format: {e}",
                                      "steps": [], "timeline": None})
            return
        rospy.loginfo("[plan] %s v%d を受け取った: %s (Unity から届いている物体: %s, move_base: %s)", plan_id, version,
                      ", ".join(f"{s['step_id']} {s['object']}" for s in steps), sorted(self.world) or "なし",
                      "あり" if self.nav_available() else "無し (NAV=true で起動していない?)")
        threading.Thread(target=self.run_plan, args=(plan_id, version, steps, keepout), daemon=True).start()

    @classmethod
    def parse_plan_step(cls, s):
        kind = s.get("kind") or "pick_place"
        if kind not in STEP_KINDS:
            raise ValueError(f"kind {kind!r} is none of {list(STEP_KINDS)}")
        step = {"step_id": str(s["step_id"]), "kind": kind, "object": str(s.get("object") or ""),
                "place": cls.parse_place(s.get("place")), "rest": cls.parse_place(s.get("rest")),
                "stay": bool(s.get("stay", False)), "pose": None,
                # 家具ごとに Unity で決めた止まる位置 [[x, y, yaw], ...] (world)。まずこれを試す
                "approach": {k: [tuple(float(v) for v in p[:3]) for p in (s.get("approach") or {}).get(k) or []]
                             for k in ("pick", "place")}}
        if kind == "pick_place" and step["place"] is None:
            raise ValueError(f"{step['step_id']}: pick_place requires place")
        if kind in ("pick_place", "pick") and not step["object"]:
            raise ValueError(f"{step['step_id']}: object is required")
        if kind == "navigate":
            step["pose"] = tuple(float(v) for v in s["pose"])
            if len(step["pose"]) != 3:
                raise ValueError(f"{step['step_id']}: navigate pose is [x, y, yaw]")
        return step

    def publish_plan_result(self, result):
        self.plan_result_pub.publish(String(json.dumps(result, ensure_ascii=False)))

    def run_plan(self, plan_id, version, steps, keepout=()):
        result = {"plan_id": plan_id, "plan_version": version, "error": "", "steps": [], "timeline": None}
        if not self.lock.acquire(blocking=False):
            result["error"] = "busy (the robot is moving)"
            rospy.logwarn("[plan] %s v%d: %s", plan_id, version, result["error"])
            self.publish_plan_result(result)
            return
        self._plan_id, self._plan_version = plan_id, version
        saved = (self.holding, self.wrist_to_obj, self.obj_size, self.picked_from)
        self.stop_requested = False
        try:
            if self.holding is not None:
                raise Abort(f"holding {self.holding}, so can't plan (place it first)")
            started = rospy.get_time()
            self.set_keepout(list(keepout))  # 避ける範囲を地図に入れてから計画する (止まる位置も、その中は選ばない)
            self.begin_dry(need_objects=any(s["kind"] != "navigate" for s in steps))
            for step in steps:
                result["steps"].append(self.plan_step(step))
            objects = []
            for s in steps:
                start = self.initial_world.get(s["object"])
                end = self.dry.world.get(s["object"])
                if start is not None:
                    objects.append({"object": s["object"], "start": matrix_to_dict(start[0]),
                                    "rest": matrix_to_dict(end[0]) if end is not None else None})
            result["timeline"] = self.dry.timeline(self.all_joints, objects)
            self.plans.pop((plan_id, version), None)
            self.plans[(plan_id, version)] = self.dry.store
            while len(self.plans) > MAX_PLANS:
                self.plans.pop(next(iter(self.plans)))
            rospy.loginfo("[plan] %s v%d: %d step を %.1f 秒で計画 (ok %d)", plan_id, version, len(steps),
                          rospy.get_time() - started, sum(1 for s in result["steps"] if s["status"] == "ok"))
        except Abort as e:
            result["error"] = str(e)
            rospy.logwarn("[plan] %s v%d: 計画できない: %s", plan_id, version, e)
        except Exception as e:
            rospy.logerr("[plan] %s", e, exc_info=True)
            result["error"] = f"internal error: {e}"
        finally:
            self.end_dry()
            self.holding, self.wrist_to_obj, self.obj_size, self.picked_from = saved
            self.lock.release()
            self.publish_state()
        self.publish_plan_result(result)

    def begin_dry(self, need_objects=True):
        if need_objects and not self.world:
            raise Abort("no objects received from Unity (/coground/scene/objects)")
        self.freeze_pub.publish(Bool(True))
        rospy.sleep(0.3)  # scene_sync が止まるのを待つ
        base = self.base_world()
        joints = self.current_joints()
        self.initial_world = dict(self.world)
        self.dry = DryRun(base, joints, dict(self.world))
        self.publish_state()

    def end_dry(self):
        self.dry = None
        try:
            for name in self.scene.get_attached_objects().keys():
                if name.startswith(PREFIX):
                    self.scene.remove_attached_object(name=name)
                    self.scene.remove_world_object(name)
        except Exception as e:
            rospy.logwarn("[plan] 後片付け: %s", e)
        self.freeze_pub.publish(Bool(False))  # scene_sync が実物の位置で置き直す

    def apply_virtual_scene(self):
        """仮の台車から見た位置に、Unity の物体を全部置き直す (持っている物は手に付け直す)"""
        dry = self.dry
        inv = np.linalg.inv(dry.base)
        for name in self.scene.get_attached_objects().keys():
            if name.startswith(PREFIX):
                self.scene.remove_attached_object(name=name)
        objects = []
        for name, (m, size) in dry.world.items():
            if name == self.holding:
                continue
            co = CollisionObject()
            co.header.frame_id = self.frame
            co.id = PREFIX + name
            co.primitives = [SolidPrimitive(type=SolidPrimitive.BOX, dimensions=list(size))]
            co.primitive_poses = [matrix_to_pose(inv.dot(m))]
            co.operation = CollisionObject.ADD
            objects.append(co)
        if self.holding is not None:
            remove = CollisionObject()
            remove.header.frame_id = self.frame
            remove.id = PREFIX + self.holding
            remove.operation = CollisionObject.REMOVE
            objects.append(remove)
        scene = PlanningScene(is_diff=True, world=PlanningSceneWorld(collision_objects=objects))
        if not self.apply_scene_srv(scene=scene).success:
            raise Abort("can't re-place the Planning Scene")
        if self.holding is not None and dry.holding_rel is not None:
            self.attach_rel(PREFIX + self.holding, dry.holding_rel, self.obj_size)

    def stop_candidates(self, target, fixed=()):
        """止まる位置の候補 [((x, y, yaw) か None (= 今の位置のまま), 出どころ "stay" / "approach" / "auto")]。
        fixed (家具に決めてある止まる位置) を、目標に近い順に先に試す"""
        base = self.dry.base
        bx, by, byaw = base[0, 3], base[1, 3], yaw_of(base)
        tx, ty = target[0], target[1]
        out = []
        c, s = math.cos(-byaw), math.sin(-byaw)
        lx, ly = c * (tx - bx) - s * (ty - by), s * (tx - bx) + c * (ty - by)
        if self.reach_x[0] <= lx <= self.reach_x[1] and abs(ly) <= self.reach_y:
            out.append((None, "stay"))
        nav = self.nav_available()
        if fixed and nav:
            for p in sorted(fixed, key=lambda p: math.hypot(p[0] - tx, p[1] - ty)):
                out.append((tuple(p), "approach"))
        auto = []
        if nav:
            th0 = math.atan2(ty - by, tx - bx)
            blocked = 0
            for a in self.stop_angles:  # 台車から見て手前側の向きを先に試す
                for d in self.standoffs:
                    th = wrap(th0 + math.radians(a))
                    x, y = tx - d * math.cos(th), ty - d * math.sin(th)
                    if self.free(x, y):
                        auto.append(((x, y, th), "auto"))
                    else:
                        blocked += 1
            if blocked:
                rospy.loginfo("[plan] 止まる位置の候補のうち %d か所は、地図で障害物に近すぎるので外した", blocked)
            if self.costmap is None:
                rospy.logwarn_throttle(30, "[plan] move_base の地図 (global_costmap/costmap) が届いていない。止まる位置を地図で選べない")
        return out + auto[:max(0, self.max_stops - len(out))]

    def at_stop(self, kind, target, action, fixed=(), stay_only=False):
        """止まる位置を試しながら action (pick / place) を計画する。うまくいった (止まる位置, 出どころ) を返す。
        stay_only なら台車を動かさず、今の位置だけで試す"""
        dry = self.dry
        dry.kind = kind
        candidates = [(None, "stay")] if stay_only else self.stop_candidates(target, fixed)
        rospy.loginfo("[plan] %s %s: 止まる位置の候補 %d か所 (目標 x=%.2f y=%.2f)", dry.step_id, kind, len(candidates),
                      target[0], target[1])
        if not candidates:
            if not self.nav_available():
                raise Abort(f"{kind}: not reachable from the current pose, and there's no move_base (start with NAV=true)")
            raise Abort(f"{kind}: everything around the object ({', '.join('%.2f' % d for d in self.standoffs)} m) is too close to obstacles, "
                        "so there's nowhere to stop the base (is the object at the back of the desk?)")
        errors = []
        for i, (stop, source) in enumerate(candidates):
            cp = dry.checkpoint(self)
            try:
                if stop is not None:
                    self.plan_progress(f"{kind}: stop position {i + 1}/{len(candidates)}"
                                       + (" (specified position)" if source == "approach" else ""))
                    here = (dry.base[0, 3], dry.base[1, 3], yaw_of(dry.base))
                    path = self.nav_path(here, stop)
                    dry.add_base(path, self.nav_linear, self.nav_angular)
                self.apply_virtual_scene()
                action()
                base = dry.base
                if source == "auto" and fixed:
                    rospy.logwarn("[plan] %s %s: 指定した止まる位置ではだめだったので、自動で選んだ位置を使う", dry.step_id, kind)
                return [round(float(base[0, 3]), 4), round(float(base[1, 3]), 4), round(float(yaw_of(base)), 4)], source
            except Abort as e:
                if self.stop_requested:
                    raise
                errors.append(str(e))
                (rospy.logwarn if source == "approach" else rospy.loginfo)(
                    "[plan] %s %s: 候補 %d/%d (%s%s) はだめ: %s", dry.step_id, kind, i + 1, len(candidates),
                    "今の位置" if stop is None else "x=%.2f y=%.2f yaw=%.0f°" % (stop[0], stop[1], math.degrees(stop[2])),
                    "、指定した位置" if source == "approach" else "", e)
                dry.restore(cp, self)
        reasons = sorted(set(errors), key=errors.index)
        if stay_only:
            raise Abort(f"can't {kind} from the current pose: {' / '.join(reasons[:3])}")
        raise Abort(f"no stop position from which {kind} is possible (tried {len(candidates)}: {' / '.join(reasons[:3])})")

    def plan_step(self, step):
        dry = self.dry
        name, sid = step["object"], step["step_id"]
        dry.step_id = sid
        out = {"step_id": sid, "object": name, "status": "infeasible", "reason": "", "t0": round(dry.t, 3),
               "t1": round(dry.t, 3), "stops": {}}
        cp = dry.checkpoint(self)
        try:
            kind = step.get("kind", "pick_place")
            stops, sources = {}, {}
            if kind == "navigate":
                if not self.nav_available():
                    raise Abort("no move_base (start with NAV=true)")
                goal = step["pose"]
                here = (dry.base[0, 3], dry.base[1, 3], yaw_of(dry.base))
                self.plan_progress("navigate: planning the path")
                dry.add_base(self.nav_path(here, goal), self.nav_linear, self.nav_angular)
                stops["navigate"], sources["navigate"] = [round(float(v), 4) for v in goal], "goal"
            else:
                if name not in dry.world:
                    raise Abort(f"{name} hasn't been received from Unity")
                approach = step.get("approach") or {}
                stops["pick"], sources["pick"] = self.at_stop(
                    "pick", dry.world[name][0][0:3, 3], lambda: self.pick(name), approach.get("pick") or (),
                    stay_only=step.get("stay", False))
            if kind == "pick_place":
                place = step["place"]
                stops["place"], sources["place"] = self.at_stop(
                    "place", place["position"],
                    lambda: self.place(name, self.world_frame, place["position"], place["orientation"], step["rest"]),
                    approach.get("place") or ())
            dry.store.setdefault(sid, {})["stops"] = stops
            out.update(status="ok", t1=round(dry.t, 3), stops=stops, stop_source=sources)
        except Abort as e:
            if self.stop_requested:
                raise
            dry.kind = None
            dry.restore(cp, self)
            dry.store.pop(sid, None)
            self.apply_virtual_scene()
            out["reason"] = str(e)
        (rospy.loginfo if out["status"] == "ok" else rospy.logwarn)(
            "[plan] %s %s: %s %s %s", sid, name, out["status"], out["reason"] or out["stops"], out.get("stop_source", ""))
        dry.step_id, dry.kind = None, None
        self.plan_progress(f"{sid}: {out['status']}" + (f" ({out['reason']})" if out["reason"] else ""))
        return out


if __name__ == "__main__":
    moveit_commander.roscpp_initialize(sys.argv)
    rospy.init_node("coground_pick_place_server")
    PickPlaceServer()
    rospy.spin()
    moveit_commander.roscpp_shutdown()
