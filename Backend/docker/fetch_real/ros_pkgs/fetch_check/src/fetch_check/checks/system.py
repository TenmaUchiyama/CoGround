"""level 0: ROS の接続・ロボットの状態 (読むだけ)。"""
import os
import socket

import actionlib
import rosgraph
import rosgraph.network
import rospy

from ..core import check, fail, ok, skip, warn
from .. import ros_util as ru

# Fetch の標準のコントローラ (robot_controllers) のアクション
CONTROLLER_ACTIONS = {
    "arm": "/arm_controller/follow_joint_trajectory",
    "arm_with_torso": "/arm_with_torso_controller/follow_joint_trajectory",
    "torso": "/torso_controller/follow_joint_trajectory",
    "head": "/head_controller/follow_joint_trajectory",
    "head_point": "/head_controller/point_head",
    "gripper": "/gripper_controller/gripper_action",
}
# 台車の速度指令の候補 (どちらを購読しているかは構成による)
BASE_CMD_TOPICS = ["/cmd_vel", "/base_controller/command"]

HINT_NETWORK = ("ROS_MASTER_URI / ROS_IP (ROS_HOSTNAME) と、お互いのホスト名が引けるか (/etc/hosts) を確認。"
                "docs/REAL_FETCH_QUICKSTART.md の Phase 1")


@check("sys.master", 0, "ROS マスターに接続",
       "roscore に届くか。自分が名乗るホスト名が相手から引けそうか、シム時間の設定も見る")
def master(ctx):
    uri = rosgraph.get_master_uri()
    try:
        pubs, subs, srvs = ru.system_state()
    except Exception as e:
        return fail(f"{uri} に届かない: {e}", HINT_NETWORK, master_uri=uri)
    nodes = {n for d in (pubs, subs, srvs) for ns in d.values() for n in ns}
    my_host = rosgraph.network.get_host_name()
    details = {
        "master_uri": uri,
        "ROS_HOSTNAME": os.environ.get("ROS_HOSTNAME"),
        "ROS_IP": os.environ.get("ROS_IP"),
        "advertised_host": my_host,
        "nodes": len(nodes),
        "topics": len(pubs),
        "use_sim_time": rospy.get_param("/use_sim_time", False),
    }
    # 自分が名乗るホスト名がループバックで、マスターが別マシンなら、相手は自分にデータを送れない
    try:
        my_ip = socket.gethostbyname(my_host)
        details["advertised_ip"] = my_ip
    except OSError:
        return warn(f"自分のホスト名 {my_host} が自分でも引けない", HINT_NETWORK, **details)
    master_host = rosgraph.network.parse_http_host_and_port(uri)[0]
    master_is_local = master_host in ("localhost", "127.0.0.1") or master_host == my_host
    if my_ip.startswith("127.") and not master_is_local:
        return warn(f"マスターは別マシン ({master_host}) なのに、自分の名前が {my_ip} (ループバック) になる",
                    "ROS_IP に自分の LAN の IP を設定する", **details)
    return ok(f"{uri} / ノード {len(nodes)} / トピック {len(pubs)}", **details)


@check("sys.nodes", 0, "全ノードに届くか",
       "マスターに登録された全ノードへ直接問い合わせる。届かないノードがあると「トピックは見えるのにデータが来ない」になる")
def nodes(ctx):
    pubs, subs, srvs = ru.system_state()
    names = sorted({n for d in (pubs, subs, srvs) for ns in d.values() for n in ns}
                   - {rospy.get_name()})
    res = ru.ping_nodes(names)
    bad = {n: e for n, e in res.items() if e}
    if bad:
        return fail(f"{len(bad)}/{len(names)} ノードに届かない: {', '.join(sorted(bad)[:5])}",
                    HINT_NETWORK, unreachable=bad)
    return ok(f"{len(names)} ノードすべてに届いた", nodes=names)


@check("sys.runstop", 0, "ランストップ (非常停止) の状態",
       "fetch_driver の RobotState を読む。ランストップ中は動作の確認ができない")
def runstop(ctx):
    topics = ru.find_topics_by_type("RobotState")
    if not topics:
        return ctx.missing("RobotState のトピックが無い (fetch_driver が動いていない?)",
                           "Fetch 本体のドライバ (robot.service) が起動しているか管理者に確認")
    topic = topics[0]
    s = ru.sample_topic(topic, ctx.duration)
    if s.count == 0:
        return fail(f"{topic} はあるがデータが来ない", HINT_NETWORK, **s.summary_details())
    if not s.decoded:
        return warn(f"{topic} の型 {s.msg_type} をこのコンテナで解読できない", "Dockerfile に型のパッケージを追加",
                    **s.summary_details())
    flags = ru.bool_fields(s.last)
    details = dict(s.summary_details(), flags=flags)
    if flags.get("runstopped"):
        return warn("ランストップ中 (モーターが止まっている)", "ランストップを解除すると動く", **details)
    if flags.get("faulted"):
        return fail("ドライバが異常 (faulted)", "Fetch を再起動するか管理者に相談", **details)
    if "runstopped" not in flags:
        return warn("runstopped のフィールドが見つからない (型の違い?)", **details)
    return ok("ランストップは解除されている", **details)


@check("sys.battery", 0, "バッテリー残量",
       "BatteryState (power_msgs / sensor_msgs) を読む。30% 未満で WARN、15% 未満で FAIL")
def battery(ctx):
    topics = ru.find_topics_by_type("BatteryState")
    if not topics:
        return ctx.missing("BatteryState のトピックが無い", "/battery_state があるか rostopic list で確認")
    topic = "/battery_state" if "/battery_state" in topics else topics[0]
    s = ru.sample_topic(topic, ctx.duration)
    if s.count == 0:
        return fail(f"{topic} はあるがデータが来ない", HINT_NETWORK, **s.summary_details())
    if not s.decoded:
        return warn(f"{topic} の型 {s.msg_type} を解読できない", **s.summary_details())
    m = s.last
    # power_msgs: charge_level (0-1), is_charging / sensor_msgs: percentage (0-1), power_supply_status
    level = getattr(m, "charge_level", None)
    if level is None:
        level = getattr(m, "percentage", None)
    charging = getattr(m, "is_charging", None)
    details = dict(s.summary_details(), level=level, charging=charging)
    if level is None:
        return warn("残量のフィールドが見つからない", **details)
    pct = level * 100 if level <= 1.0 else level
    text = f"{pct:.0f}%" + (" (充電中)" if charging else "")
    if pct < 15:
        return fail(f"残量 {text}。動かす前に充電する", **details)
    if pct < 30:
        return warn(f"残量 {text}。長い作業の前に充電を", **details)
    return ok(f"残量 {text}", **details)


@check("sys.controllers", 0, "コントローラ (腕・胴・首・グリッパー・台車)",
       "動かすための窓口 (アクション) があるか。robot_controllers に状態も問い合わせる (動かしはしない)")
def controllers(ctx):
    published = ru.published_topics()
    _, subs, _ = ru.system_state()
    present = {k: ru.action_server_exists(ns, published) for k, ns in CONTROLLER_ACTIONS.items()}
    base_topics = [t for t in BASE_CMD_TOPICS if subs.get(t)]
    details = {"actions": {CONTROLLER_ACTIONS[k]: v for k, v in present.items()}, "base_cmd_subscribed": base_topics}

    states = _query_controller_states()
    if states is not None:
        details["controller_states"] = states

    missing = [k for k, v in present.items() if not v]
    if not base_topics:
        missing.append("base")
    if len(missing) == len(present) + 1:
        return ctx.missing("コントローラが 1 つも見つからない", "Fetch のドライバが起動しているか確認", **details)
    errors = [n for n, st in (states or {}).items() if st == "error"]
    if errors:
        return fail(f"エラー状態のコントローラ: {', '.join(errors)}", "Fetch の再起動 / 管理者に相談", **details)
    if missing:
        return ctx.missing(f"見つからない: {', '.join(missing)}", **details)
    return ok(f"すべてある (台車は {', '.join(base_topics)})", **details)


def _query_controller_states():
    """robot_controllers の /query_controller_states に「何も変えない」問い合わせをする。無ければ None"""
    try:
        from robot_controllers_msgs.msg import ControllerState, QueryControllerStatesAction, QueryControllerStatesGoal
    except ImportError:
        return None
    client = actionlib.SimpleActionClient("/query_controller_states", QueryControllerStatesAction)
    if not client.wait_for_server(rospy.Duration(1.5)):
        return None
    client.send_goal(QueryControllerStatesGoal())  # updates が空 = 状態を読むだけ
    if not client.wait_for_result(rospy.Duration(3.0)):
        client.cancel_goal()
        return None
    names = {ControllerState.STOPPED: "stopped", ControllerState.RUNNING: "running", ControllerState.ERROR: "error"}
    return {c.name: names.get(c.state, str(c.state)) for c in client.get_result().state}


@check("sys.diagnostics", 0, "診断 (/diagnostics)",
       "ドライバが出す自己診断のうち ERROR / WARN のものを集める (モーター温度・ボードの通信など)")
def diagnostics(ctx):
    published = ru.published_topics()
    topic = next((t for t in ("/diagnostics_agg", "/diagnostics") if t in published), None)
    if topic is None:
        return ctx.missing("/diagnostics が無い")
    from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
    s = ru.sample_topic(topic, max(ctx.duration, 3.0), DiagnosticArray, keep_all=True)
    if s.count == 0:
        return fail(f"{topic} はあるがデータが来ない", HINT_NETWORK, topic=topic)
    latest = {}
    for arr in s.last:
        for st in arr.status:
            latest[st.name] = st
    level = lambda v: v if isinstance(v, int) else ord(v)  # noqa: E731  byte は環境で bytes / int になる
    errs = {n: st.message for n, st in latest.items() if level(st.level) >= DiagnosticStatus.ERROR}
    warns = {n: st.message for n, st in latest.items() if level(st.level) == DiagnosticStatus.WARN}
    details = {"topic": topic, "items": len(latest), "errors": errs, "warnings": warns}
    if errs:
        return fail(f"ERROR {len(errs)} 件: {', '.join(list(errs)[:3])}", "details の errors を見る", **details)
    if warns:
        return warn(f"WARN {len(warns)} 件: {', '.join(list(warns)[:3])}", **details)
    return ok(f"{len(latest)} 項目すべて OK", **details)


@check("sys.planners", 0, "MoveIt / Navigation が起動しているか",
       "move_group, move_base, amcl, 地図 (/map) の有無。無くても壊れてはいない (起動していないだけ) ので WARN")
def planners(ctx):
    published = ru.published_topics()
    items = {
        "move_group (MoveIt)": ru.action_server_exists("/move_group", published),
        "move_base (Navigation)": ru.action_server_exists("/move_base", published),
        "amcl (自己位置推定)": "/amcl_pose" in published,
        "/map (地図)": "/map" in published,
    }
    running = [k for k, v in items.items() if v]
    stopped = [k for k, v in items.items() if not v]
    if not running:
        return warn("どれも起動していない", "MoveIt: roslaunch fetch_moveit_config move_group.launch / "
                    "Navigation: roslaunch fetch_navigation fetch_nav.launch map_file:=...", items=items)
    if stopped:
        return warn(f"起動していない: {', '.join(stopped)}", items=items)
    return ok("すべて起動している", items=items)
