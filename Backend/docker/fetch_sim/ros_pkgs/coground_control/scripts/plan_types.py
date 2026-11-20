"""Robot 側 (ROS / MoveIt) が Plan の動作計画・実行で扱うデータの型。

グラウンディングサーバーの Plan (grounding_server/coground_server/models.py) のうち、ロボットに必要な
部分だけを受け取り、step ごとの計画結果 (ok / infeasible) と軌道を返す。
ルール・属性・領域などの「意味」はここには来ない。

ほかの /coground/* と同じく、自前の .msg は作らず std_msgs/String に JSON を入れて送る
(Unity 側でメッセージ生成をしなくてよい)。

  向き          トピック                    型 (JSON)        内容
  → ROS        /coground/plan/request      PlanRequest      Plan の全 step を順に計画する (実行はしない)
  ROS →        /coground/plan/result       PlanResult       step ごとの ok / infeasible と trajectory_id (latch)
  ROS →        /coground/plan/trajectory   StepTrajectory   step 1 つ分の軌道。計画できた step ごとに 1 通
  → ROS        /coground/plan/execute      ExecuteRequest   承認された Plan を実行する
  ROS →        /coground/plan/status       ExecutionStatus  実行の進み具合 (latch)

サーバーの型との対応:
  Plan.id / Plan.version       -> plan_id / plan_version (古い版の結果を捨てるために必ず付けて返す)
  Step.id                      -> step_id
  Step.object_id               -> object (Planning Scene の id は "unity/<object>")
  Step.to.pose                 -> place (下の座標変換をしたもの)
  Step.status / trajectory_id  <- StepResult.status / trajectory_id

座標: サーバーは Unity のワールド座標 (左手系、Y 上、回転 [x, y, z, w])。
ここは ROS の座標 (右手系、Z 上、frame_id 既定 world = Unity の World)。ROS に渡す側が変換する
(Unity の To<FLU>() と同じ: 位置 (x, y, z) -> (z, -x, y)、回転 (x, y, z, w) -> (z, -x, y, -w))。
position は置いたときの物体の中心 (pick_place_server と同じ)。

Python 3.8 (ROS Noetic) で動かすため、標準ライブラリだけを使う。
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

TOPIC_REQUEST = "/coground/plan/request"
TOPIC_RESULT = "/coground/plan/result"
TOPIC_TRAJECTORY = "/coground/plan/trajectory"
TOPIC_EXECUTE = "/coground/plan/execute"
TOPIC_STATUS = "/coground/plan/status"

STEP_OK = "ok"
STEP_INFEASIBLE = "infeasible"
STEP_STATUSES = (STEP_OK, STEP_INFEASIBLE)

# 軌道の区切り。pick_place_server の status と同じ名前・同じ順番
PHASES = ("navigating", "opening", "approaching", "descending", "grasping", "lifting",
          "moving", "lowering", "releasing", "retreating")

EXEC_STATES = ("accepted", "rejected", "executing", "succeeded", "failed", "stopped")


class _Json:
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError(f"{cls.__name__}: not a JSON object")
        return cls.from_dict(data)


def _need(d: Dict[str, Any], key: str, what: str) -> Any:
    if not isinstance(d, dict) or key not in d or d[key] is None:
        raise ValueError(f"{what}: missing {key}")
    return d[key]


def _floats(value: Any, n: int, what: str) -> List[float]:
    try:
        out = [float(v) for v in value]
    except (TypeError, ValueError):
        raise ValueError(f"{what}: not an array of {n} numbers")
    if len(out) != n:
        raise ValueError(f"{what}: not an array of {n} numbers")
    return out


def _one_of(value: Any, allowed, what: str) -> str:
    if value not in allowed:
        raise ValueError(f"{what}: {value!r} is none of {list(allowed)}")
    return value


# ---------------------------------------------------------------- 計画の依頼


@dataclass
class PlacePose(_Json):
    position: List[float]                      # 置いたときの物体の中心 [x, y, z]
    orientation: Optional[List[float]] = None  # [x, y, z, w]。None なら今の向きの yaw のまま

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PlacePose":
        orientation = d.get("orientation") if isinstance(d, dict) else None
        return cls(
            position=_floats(_need(d, "position", "place"), 3, "place.position"),
            orientation=_floats(orientation, 4, "place.orientation") if orientation is not None else None,
        )


@dataclass
class StepRequest(_Json):
    step_id: str
    object: str        # Unity の物体 ID (Planning Scene の id は unity/<object>)
    place: PlacePose

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StepRequest":
        return cls(
            step_id=str(_need(d, "step_id", "step")),
            object=str(_need(d, "object", "step")),
            place=PlacePose.from_dict(_need(d, "place", "step")),
        )


@dataclass
class PlanRequest(_Json):
    """steps を並び順に計画する。前の step を終えた状態 (腕の姿勢、動かした物体) から次を計画する。

    計画できない step は infeasible にして飛ばし、その物体は動かなかったものとして続ける。
    """
    plan_id: str
    plan_version: int
    steps: List[StepRequest] = field(default_factory=list)
    frame_id: str = "world"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PlanRequest":
        steps = [StepRequest.from_dict(s) for s in _need(d, "steps", "request")]
        ids = [s.step_id for s in steps]
        if len(set(ids)) != len(ids):
            raise ValueError(f"request: duplicate step_id: {ids}")
        return cls(
            plan_id=str(_need(d, "plan_id", "request")),
            plan_version=int(_need(d, "plan_version", "request")),
            steps=steps,
            frame_id=str(d.get("frame_id") or "world"),
        )


# ---------------------------------------------------------------- 計画の結果


@dataclass
class StepResult(_Json):
    step_id: str
    status: str                          # STEP_OK / STEP_INFEASIBLE
    trajectory_id: Optional[str] = None  # ok のときだけ
    reason: str = ""                     # infeasible の理由 (人が読む文)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StepResult":
        return cls(
            step_id=str(_need(d, "step_id", "result")),
            status=_one_of(_need(d, "status", "result"), STEP_STATUSES, "result.status"),
            trajectory_id=d.get("trajectory_id"),
            reason=str(d.get("reason") or ""),
        )


@dataclass
class PlanResult(_Json):
    plan_id: str
    plan_version: int
    steps: List[StepResult] = field(default_factory=list)
    error: str = ""  # 依頼そのものを受けられなかった理由 (形式が不正、busy など)。このとき steps は空

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PlanResult":
        return cls(
            plan_id=str(_need(d, "plan_id", "result")),
            plan_version=int(_need(d, "plan_version", "result")),
            steps=[StepResult.from_dict(s) for s in d.get("steps") or []],
            error=str(d.get("error") or ""),
        )


def trajectory_id_for(plan_id: str, plan_version: int, step_id: str) -> str:
    """版が変わると軌道も変わるので、ID に版を入れる。例: plan_1/v2/s1"""
    return f"{plan_id}/v{plan_version}/{step_id}"


# ---------------------------------------------------------------- 軌道


@dataclass
class TrajectoryPoint(_Json):
    t: float                 # この区切りの始まりからの秒
    positions: List[float]   # joint_names と同じ並び

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TrajectoryPoint":
        positions = _need(d, "positions", "point")
        return cls(t=float(_need(d, "t", "point")), positions=_floats(positions, len(positions), "point.positions"))


@dataclass
class TrajectorySegment(_Json):
    """Pick & Place の 1 区切り (腕の移動、または指の開閉)。"""
    phase: str               # PHASES のどれか
    joint_names: List[str]
    points: List[TrajectoryPoint] = field(default_factory=list)
    attached: bool = False   # この区切りの間、物体が手にくっついているか (Ghost が物体を追従させる)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TrajectorySegment":
        names = [str(n) for n in _need(d, "joint_names", "segment")]
        points = [TrajectoryPoint.from_dict(p) for p in d.get("points") or []]
        for p in points:
            if len(p.positions) != len(names):
                raise ValueError("segment: number of positions doesn't match joint_names")
        return cls(
            phase=_one_of(_need(d, "phase", "segment"), PHASES, "segment.phase"),
            joint_names=names,
            points=points,
            attached=bool(d.get("attached", False)),
        )


@dataclass
class StepTrajectory(_Json):
    """step 1 つ分の軌道。Unity はこれを trajectory_id で引いて Ghost Robot を動かす。"""
    trajectory_id: str
    plan_id: str
    plan_version: int
    step_id: str
    object: str
    segments: List[TrajectorySegment] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return sum(s.points[-1].t for s in self.segments if s.points)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StepTrajectory":
        return cls(
            trajectory_id=str(_need(d, "trajectory_id", "trajectory")),
            plan_id=str(_need(d, "plan_id", "trajectory")),
            plan_version=int(_need(d, "plan_version", "trajectory")),
            step_id=str(_need(d, "step_id", "trajectory")),
            object=str(_need(d, "object", "trajectory")),
            segments=[TrajectorySegment.from_dict(s) for s in d.get("segments") or []],
        )


# ---------------------------------------------------------------- 実行


@dataclass
class ExecuteRequest(_Json):
    """計画済みの版を実行する。版が最後に計画したものと違えば rejected。"""
    plan_id: str
    plan_version: int
    step_ids: List[str] = field(default_factory=list)  # 空 = ok の step を全部、計画した順に

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExecuteRequest":
        return cls(
            plan_id=str(_need(d, "plan_id", "execute")),
            plan_version=int(_need(d, "plan_version", "execute")),
            step_ids=[str(s) for s in d.get("step_ids") or []],
        )


@dataclass
class ExecutionStatus(_Json):
    plan_id: str
    plan_version: int
    state: str                     # EXEC_STATES のどれか
    step_id: Optional[str] = None  # いま実行している step (Plan 全体の状態なら None)
    phase: Optional[str] = None    # PHASES のどれか
    detail: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExecutionStatus":
        phase = d.get("phase")
        return cls(
            plan_id=str(_need(d, "plan_id", "status")),
            plan_version=int(_need(d, "plan_version", "status")),
            state=_one_of(_need(d, "state", "status"), EXEC_STATES, "status.state"),
            step_id=d.get("step_id"),
            phase=_one_of(phase, PHASES, "status.phase") if phase is not None else None,
            detail=str(d.get("detail") or ""),
        )
