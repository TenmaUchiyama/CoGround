"""level 0: センサーと TF (読むだけ)。

周期の目安は Fetch の実機の標準値から。シムは遅いことがあるので min_hz (下回ると FAIL) は控えめにしてある。
"""
import math

import rospy
import tf2_ros

from ..core import check, fail, ok, warn
from .. import ros_util as ru
from .system import HINT_NETWORK

# Fetch の関節 (joint_states に全部出るはず)
FETCH_JOINTS = [
    "l_wheel_joint", "r_wheel_joint", "torso_lift_joint", "head_pan_joint", "head_tilt_joint",
    "shoulder_pan_joint", "shoulder_lift_joint", "upperarm_roll_joint", "elbow_flex_joint",
    "forearm_roll_joint", "wrist_flex_joint", "wrist_roll_joint",
    "l_gripper_finger_joint", "r_gripper_finger_joint",
]
# 受信時刻 - header.stamp がこれを超えたら時計のずれ / 遅延を疑う [s]
MAX_STAMP_AGE = 0.5


def measure(ctx, topic, ok_hz, min_hz, msg_class=None, duration=None, extra=None, keep_all=False):
    """トピックの周期を測って判定する共通処理。

    extra(last, details) -> Optional[Result] で型ごとの追加の確認 (画像サイズ等) をする。
    last は最後のメッセージ (keep_all=True なら全メッセージのリスト)。
    """
    if topic not in ru.published_topics():
        return ctx.missing(f"{topic} が出ていない", "rostopic list で名前を確認 / ドライバが起動しているか")
    s = ru.sample_topic(topic, duration or ctx.duration, msg_class, keep_all=keep_all)
    details = s.summary_details()
    if s.count == 0:
        return fail(f"{topic} はあるがデータが来ない", HINT_NETWORK, **details)
    rate = f"{s.rate_hz:.1f} Hz" if s.count >= 2 else f"{s.count} 件"
    if s.count >= 2 and s.rate_hz < min_hz:
        return fail(f"{rate} (最低 {min_hz} Hz)", "負荷 / Wi-Fi の帯域を疑う", **details)
    if extra is not None and s.decoded and s.last is not None:
        r = extra(s.last, details)
        if r is not None:
            return r
    age = s.mean_age
    if age is not None and abs(age) > MAX_STAMP_AGE:
        return warn(f"{rate} だが時刻が {age:+.2f} s ずれている",
                    "PC と Fetch の時計を合わせる (chrony / ntpdate)。TF や MoveIt が失敗する原因になる", **details)
    if s.count < 2 or s.rate_hz < ok_hz:
        return warn(f"{rate} (目安 {ok_hz} Hz 以上)", **details)
    return ok(rate, **details)


@check("sense.joint_states", 0, "関節角 (/joint_states)", "周期と、Fetch の全関節が出ているか")
def joint_states(ctx):
    from sensor_msgs.msg import JointState

    def extra(msgs, details):
        # Fetch はグリッパーの関節を別のメッセージで出すことがあるので、期間中に見えた名前を全部集める
        seen = {n for m in msgs for n in m.name}
        missing = [j for j in FETCH_JOINTS if j not in seen]
        details["joints_seen"] = sorted(seen)
        if missing:
            return warn(f"出ていない関節: {', '.join(missing)}", **dict(details, missing=missing))
        return None

    return measure(ctx, "/joint_states", ok_hz=50, min_hz=5, msg_class=JointState, extra=extra, keep_all=True)


@check("sense.base_scan", 0, "レーザー (/base_scan)", "周期と、有効な距離の割合・一番近い障害物")
def base_scan(ctx):
    from sensor_msgs.msg import LaserScan

    def extra(m, details):
        valid = [r for r in m.ranges if math.isfinite(r) and m.range_min <= r <= m.range_max]
        details["valid_ratio"] = len(valid) / max(len(m.ranges), 1)
        details["nearest_m"] = min(valid) if valid else None
        if details["valid_ratio"] < 0.2:
            return warn(f"有効な距離が {details['valid_ratio']:.0%} しかない (レーザーが塞がれている?)", **details)
        return None

    return measure(ctx, "/base_scan", ok_hz=10, min_hz=3, msg_class=LaserScan, extra=extra)


@check("sense.odom", 0, "オドメトリ (/odom)", "台車が「どれだけ動いたか」の推定値の周期と速度")
def odom(ctx):
    from nav_msgs.msg import Odometry

    def extra(m, details):
        details["linear_x"] = m.twist.twist.linear.x
        details["angular_z"] = m.twist.twist.angular.z
        return None

    return measure(ctx, "/odom", ok_hz=20, min_hz=5, msg_class=Odometry, extra=extra)


@check("sense.imu", 0, "IMU (/imu)", "台車の加速度・角速度センサー")
def imu(ctx):
    from sensor_msgs.msg import Imu
    return measure(ctx, "/imu", ok_hz=50, min_hz=10, msg_class=Imu)


def _image_extra(m, details):
    details["size"] = f"{m.width}x{m.height}"
    details["encoding"] = m.encoding
    return None


@check("sense.head_rgb", 0, "頭のカメラ RGB", "/head_camera/rgb/image_raw の周期と解像度")
def head_rgb(ctx):
    from sensor_msgs.msg import Image
    return measure(ctx, "/head_camera/rgb/image_raw", ok_hz=10, min_hz=2, msg_class=Image, extra=_image_extra)


@check("sense.head_depth", 0, "頭のカメラ Depth", "/head_camera/depth_registered/image_raw の周期と解像度")
def head_depth(ctx):
    from sensor_msgs.msg import Image
    return measure(ctx, "/head_camera/depth_registered/image_raw", ok_hz=10, min_hz=2, msg_class=Image,
                   extra=_image_extra)


@check("sense.head_points", 0, "頭のカメラ 点群", "/head_camera/depth_registered/points (Phase 4 の卓上認識で使う)")
def head_points(ctx):
    from sensor_msgs.msg import PointCloud2

    def extra(m, details):
        details["size"] = f"{m.width}x{m.height}"
        details["frame"] = m.header.frame_id
        return None

    # 点群は重いので少し長めに測る
    return measure(ctx, "/head_camera/depth_registered/points", ok_hz=5, min_hz=1, msg_class=PointCloud2,
                   duration=max(ctx.duration, 3.0), extra=extra)


# (親, 子, 必須か)。必須でないものは無くても WARN
TF_PAIRS = [
    ("odom", "base_link", True),
    ("base_link", "torso_lift_link", True),
    ("base_link", "gripper_link", True),
    ("base_link", "head_camera_rgb_optical_frame", True),
    ("map", "odom", False),   # 地図 + amcl が動いていれば出る
]


@check("sense.tf", 0, "TF (座標のつながり)",
       "台車・腕・カメラ・地図の座標がつながっているか。座標ずれの原因 No.1 なので最初に確認する")
def tf(ctx):
    buf = tf2_ros.Buffer(rospy.Duration(10.0))
    listener = tf2_ros.TransformListener(buf)
    try:
        rospy.sleep(max(ctx.duration, 1.5))
    finally:
        listener.unregister()  # Web サーバーから何度も呼ぶので購読を残さない
    details = {}
    for parent, child, required in TF_PAIRS:
        key = f"{parent}->{child}"
        try:
            t = buf.lookup_transform(parent, child, rospy.Time(0), rospy.Duration(0.5))
            age = (rospy.Time.now() - t.header.stamp).to_sec() if not t.header.stamp.is_zero() else 0.0
            p = t.transform.translation
            details[key] = {"ok": True, "xyz": [p.x, p.y, p.z], "age_s": age}
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
            details[key] = {"ok": False, "error": str(e).splitlines()[0]}
    bad_req = [f"{p}->{c}" for (p, c, r) in TF_PAIRS if r and not details[f"{p}->{c}"]["ok"]]
    bad_opt = [f"{p}->{c}" for (p, c, r) in TF_PAIRS if not r and not details[f"{p}->{c}"]["ok"]]
    if bad_req:
        return fail(f"つながっていない: {', '.join(bad_req)}",
                    "robot_state_publisher / ドライバが動いているか。rosrun tf view_frames で木を見る", pairs=details)
    if bad_opt:
        return warn(f"必須はつながった。無いもの: {', '.join(bad_opt)} (地図・amcl が未起動)", pairs=details)
    return ok("すべてつながっている", pairs=details)
