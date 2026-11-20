"""確認項目 (Check) の登録・実行・結果の型。

確認項目は「ctx を受け取って Result を返す関数」に @check を付けたもの:

    @check("sense.odom", level=0, title="オドメトリ")
    def odom(ctx):
        ...
        return ok("20 Hz", rate_hz=20.0)

level (危険度):
  0 読むだけ (ロボットは動かない)
  1 小さく動かす (1 関節ずつ、低速)   … 段階 B
  2 プランナー (MoveIt / move_base) … 段階 B
  3 組み合わせ (認識・把持)          … あと回し
level 1 以上は motion=True で、ctx.allow_motion が無いと実行しない。

Web UI (段階 C) も CLI と同じ REGISTRY / run_check を使う。
"""
import fnmatch
import time
import traceback
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional


class Status(str, Enum):
    PASS = "pass"
    WARN = "warn"   # 動くが気になる (周期が低い、地図がない等)
    FAIL = "fail"   # できない / 壊れている
    SKIP = "skip"   # このモードでは確かめられない (シムにバッテリーが無い等)


@dataclass
class Result:
    status: Status
    summary: str
    details: Dict = field(default_factory=dict)
    # 失敗したときに初心者が次に見るべきこと
    hint: str = ""


def ok(summary, hint="", **details):
    return Result(Status.PASS, summary, details, hint)


def warn(summary, hint="", **details):
    return Result(Status.WARN, summary, details, hint)


def fail(summary, hint="", **details):
    return Result(Status.FAIL, summary, details, hint)


def skip(summary, hint="", **details):
    return Result(Status.SKIP, summary, details, hint)


def worst(results: List[Result]) -> Status:
    """複数の小さな判定をまとめるとき用。FAIL > WARN > PASS > SKIP"""
    order = [Status.FAIL, Status.WARN, Status.PASS, Status.SKIP]
    present = {r.status for r in results}
    for s in order:
        if s in present:
            return s
    return Status.SKIP


@dataclass
class Context:
    mode: str = "real"            # "real" | "sim"
    duration: float = 2.0         # トピックを測る時間 [s]
    allow_motion: bool = False    # level 1 以上を実行してよいか (段階 B)

    @property
    def is_sim(self):
        return self.mode == "sim"

    def missing(self, summary, hint="", **details) -> Result:
        """実機にはあるはずのものが無いとき: 実機なら FAIL、シムなら SKIP"""
        if self.is_sim:
            return skip(summary + " (シムには無い)", **details)
        return fail(summary, hint, **details)


@dataclass
class CheckSpec:
    id: str
    level: int
    title: str
    description: str
    fn: Callable[[Context], Result]
    real_only: bool = False   # シムでは常に SKIP
    motion: bool = False      # ロボットが動く (allow_motion が要る)

    def info(self):
        return {"id": self.id, "level": self.level, "title": self.title,
                "description": self.description, "real_only": self.real_only, "motion": self.motion}


# id -> CheckSpec (登録順を保つ)
REGISTRY: Dict[str, CheckSpec] = {}


def check(id, level, title, description="", real_only=False, motion=None):
    def deco(fn):
        if id in REGISTRY:
            raise ValueError(f"確認項目 {id} が二重に登録された")
        REGISTRY[id] = CheckSpec(id, level, title, description or (fn.__doc__ or "").strip(), fn,
                                 real_only, level >= 1 if motion is None else motion)
        return fn
    return deco


def select(patterns: Optional[List[str]] = None, max_level: Optional[int] = None) -> List[CheckSpec]:
    """パターン (sense.* など fnmatch 形式) と level の上限で確認項目を選ぶ。登録順"""
    out = []
    for spec in REGISTRY.values():
        if max_level is not None and spec.level > max_level:
            continue
        if patterns and not any(fnmatch.fnmatch(spec.id, p) for p in patterns):
            continue
        out.append(spec)
    return out


@dataclass
class Record:
    """1 回の実行結果 (JSON に保存する単位)"""
    id: str
    title: str
    level: int
    status: Status
    summary: str
    details: Dict
    hint: str
    started_at: float
    duration_s: float

    def to_dict(self):
        d = asdict(self)
        d["status"] = self.status.value
        return d


def run_check(spec: CheckSpec, ctx: Context) -> Record:
    t0 = time.time()
    if spec.real_only and ctx.is_sim:
        res = skip("実機専用の確認 (シムでは確かめられない)")
    elif spec.motion and not ctx.allow_motion:
        res = skip("ロボットが動く確認。モーション許可 (--allow-motion) が無いので実行しない")
    else:
        try:
            res = spec.fn(ctx)
            if not isinstance(res, Result):
                res = fail(f"確認項目が Result を返さなかった: {res!r}")
        except Exception as e:  # 確認項目のバグや ROS の例外でツール全体を止めない
            res = fail(f"例外: {type(e).__name__}: {e}", traceback=traceback.format_exc())
    return Record(spec.id, spec.title, spec.level, res.status, res.summary, _jsonable(res.details), res.hint,
                  t0, time.time() - t0)


def _jsonable(x):
    """details に ROS の型などが紛れても JSON に出せるようにする"""
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [_jsonable(v) for v in x]
    if isinstance(x, float):
        return round(x, 4)
    if x is None or isinstance(x, (str, int, bool)):
        return x
    return str(x)
