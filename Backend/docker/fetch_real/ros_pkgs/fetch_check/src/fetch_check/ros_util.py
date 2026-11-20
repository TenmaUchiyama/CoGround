"""確認項目から使う ROS の小道具 (トピックの周期を測る、マスターに問い合わせる等)。"""
import threading
import time
import xmlrpc.client
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import rosgraph
import rospy
import rostopic

CALLER_ID = "/fetch_check"


def master() -> rosgraph.Master:
    return rosgraph.Master(rospy.get_name() if rospy.core.is_initialized() else CALLER_ID)


def published_topics() -> Dict[str, str]:
    """{トピック名: 型} (誰かが publish しているものだけ)"""
    return dict(master().getPublishedTopics(""))


def system_state():
    """(publishers, subscribers, services) をそれぞれ {名前: [ノード, ...]} で返す"""
    pubs, subs, srvs = master().getSystemState()
    return dict(pubs), dict(subs), dict(srvs)


def find_topics_by_type(type_suffix: str) -> List[str]:
    """型名の末尾で探す (例 'BatteryState' -> power_msgs/BatteryState も sensor_msgs/BatteryState も)"""
    return sorted(t for t, ty in published_topics().items() if ty.split("/")[-1] == type_suffix)


def action_server_exists(ns: str, published: Optional[Dict[str, str]] = None) -> bool:
    """アクションサーバーは <ns>/status と <ns>/result を publish している"""
    published = published if published is not None else published_topics()
    ns = ns.rstrip("/")
    return f"{ns}/status" in published and f"{ns}/result" in published


def msg_class_for(topic: str):
    """トピックの型のクラス。型のパッケージがこのコンテナに無ければ None"""
    try:
        cls, _, _ = rostopic.get_topic_class(topic, blocking=False)
        return cls
    except Exception:
        return None


@dataclass
class TopicSample:
    topic: str
    msg_type: str = ""
    count: int = 0
    duration: float = 0.0
    rate_hz: float = 0.0
    # 受信時刻 - header.stamp [s]。時計のずれ・遅延の目安 (header の無い型は空)
    stamp_ages: List[float] = field(default_factory=list)
    last: Any = None
    decoded: bool = True   # 型が分からず AnyMsg で数だけ数えたら False

    @property
    def mean_age(self) -> Optional[float]:
        return sum(self.stamp_ages) / len(self.stamp_ages) if self.stamp_ages else None

    def summary_details(self) -> Dict:
        d = {"topic": self.topic, "type": self.msg_type, "count": self.count, "rate_hz": self.rate_hz}
        if self.mean_age is not None:
            d["stamp_age_s"] = self.mean_age
        return d


def sample_topic(topic: str, duration: float = 2.0, msg_class=None, keep_all=False) -> TopicSample:
    """duration 秒だけ購読して、受信数・周期・最後のメッセージを返す。

    keep_all=True なら全メッセージを last にリストで入れる (diagnostics 等、送り元ごとに違うもの用)
    """
    s = TopicSample(topic, published_topics().get(topic, ""))
    cls = msg_class or msg_class_for(topic)
    if cls is None:
        cls = rospy.AnyMsg
        s.decoded = False
    times: List[float] = []
    kept: List[Any] = []
    lock = threading.Lock()

    def cb(msg):
        now = time.monotonic()
        with lock:
            times.append(now)
            if keep_all:
                kept.append(msg)
            else:
                s.last = msg
            hdr = getattr(msg, "header", None)
            if hdr is not None and not hdr.stamp.is_zero():
                s.stamp_ages.append((rospy.Time.now() - hdr.stamp).to_sec())

    sub = rospy.Subscriber(topic, cls, cb, queue_size=50, buff_size=2 ** 24)
    t0 = time.monotonic()
    try:
        time.sleep(duration)
    finally:
        sub.unregister()
    with lock:
        s.duration = time.monotonic() - t0
        s.count = len(times)
        if len(times) >= 2 and times[-1] > times[0]:
            s.rate_hz = (len(times) - 1) / (times[-1] - times[0])
        if keep_all:
            s.last = kept
    return s


class _TimeoutTransport(xmlrpc.client.Transport):
    """接続ごとのタイムアウト (socket.setdefaulttimeout はスレッド間で共有されるので使わない)"""

    def __init__(self, timeout):
        super().__init__()
        self._timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn


def ping_nodes(nodes: List[str], timeout: float = 1.5) -> Dict[str, Optional[str]]:
    """各ノードの XML-RPC に getPid を投げる。届かなかったノードだけ {ノード: エラー文} で返す

    rostopic list は見えるのにデータが来ない、の典型原因 (相手のホスト名が引けない) をここで見つける。
    """
    # マスターの ServerProxy はスレッド間で共有できないので、URI の問い合わせはここで順に済ませる
    m = master()
    uris, errors = {}, {}
    for node in nodes:
        try:
            uris[node] = m.lookupNode(node)
        except Exception as e:
            errors[node] = f"lookupNode 失敗: {e}"

    def one(item):
        node, uri = item
        try:
            proxy = xmlrpc.client.ServerProxy(uri, transport=_TimeoutTransport(timeout))
            code, msg, _ = proxy.getPid(CALLER_ID)
            return node, None if code == 1 else f"getPid code={code}: {msg}"
        except Exception as e:
            return node, f"{uri} に届かない: {type(e).__name__}: {e}"

    with ThreadPoolExecutor(max_workers=16) as ex:
        errors.update(ex.map(one, uris.items()))
    return errors


def bool_fields(msg) -> Dict[str, bool]:
    """メッセージの bool のフィールドだけ取り出す (RobotState の中身を型に依存せず見せる用)"""
    out = {}
    for name, ty in zip(getattr(msg, "__slots__", []), getattr(msg, "_slot_types", [])):
        if ty == "bool":
            out[name] = bool(getattr(msg, name))
    return out
