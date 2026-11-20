"""動作計画（Plan ボタン）: Plan の step を、ロボットが実際にどう動くか（移動 → ピック → 移動 → プレース）まで計画して持つ。

    summary = await motion.plan(step_ids=None, on_progress=...)   # ロボット（ROS）に計画を頼み、結果を持つ
    motion.entry_for(step)     # 実行に使う計画（無い / 古い なら None）
    motion.timeline()          # 通しで再生するための時間軸（Web UI が motion.get で読む）

計画は「その時の Plan とシーン」に対するもの。あとで物体が動いたり行き先が変わったりした step は「古い」(stale) になる。
step は id ではなく「物体 -> 行き先の領域」で覚える（Plan はシーンが変わるたびに作り直され、step の id が変わるため）。

止まる位置:
  家具（机・箱・ごみ箱など）に、Unity で「止まる位置」（approach_poses、CoGroundApproachPoint）を置いておくと、
  そこから取る・そこに置くとき、ロボットはまずその位置を試す（だめなときだけ、物体のまわりから自動で選ぶ）。
  どちらを使ったかは、計画の結果の stop_source（pick / place ごとに approach / auto / stay）に入る。

家庭ルール（領域への進入の禁止。R2）:
  計画した台車の経路を、計画を始めた時刻 + t で家の時計の時刻に直して判定する（norms/monitors.py の route_verdicts）。
    1. まず、領域を避けずに計画する（17:58 に通るなら、18 時からの禁止には反しない。遠回りさせない）
    2. 違反が出たら、その領域を避ける範囲（keepout_zones）に入れて計画し直す
    3. それでも通れない step は外して計画し直し、依頼の行を保留にする（state.set_route_block）。
       探した条件（計画した時刻、避けた領域、回ごとの結果）は、行の route と summary の attempts に残る
  経路による保留は、動作計画をやり直す（この plan をもう一度呼ぶ）か、ルール・領域・時計が変わると解ける。
  実行のときは、計画で避けた領域を navigate にも渡す（executor.py）。出発が遅れて通る時刻がずれる分は、
  実行中の監視（monitor.py）が境界の手前で止めて計画し直す。

プレビュー（summary の preview）:
  ステップ別の予測・最終 After・実行の 3 つが、同じ版の検証結果を見るためのもの。step ごとに
    move（検証できた。この順番で運べる） / stay_rule（家庭ルールにより残す） / stay_infeasible（動作が成立せず残す）/
    checking（確認中） / unverified（未確認。計画の失敗・タイムアウト、検証のあとで状況が変わった）
  と理由を持つ。id は中身が変わるたびに変わる。実行（exec.start）は、住人が見た preview の id を渡し、
  いまの id と違えば始めない。シーケンスを編集したら invalidate で、影響を受ける step 以降を未確認に戻す。
  step は順に、前の step を終えた状態から検証する（計画できなかった物は元の場所に残った状態で、次を検証する）。

置き方:
  行き先の領域の持ち主が receptacle（ごみ箱・箱・シンクなど）なら「落とす」: 領域の上面の少し上で離す。
  落ちたあとの位置（rest）は、Plan の置き位置（領域の底）とする。
  それ以外（机・棚など）は、Plan の置き位置にそっと置く。
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from typing import Any, Awaitable, Callable

from .eventlog import EventLog
from .models import MissingFact, Plan, Pose, SceneSnapshot, Step, Verdict
from .norms.monitors import build_monitors, is_zone_entry, monitored, route_verdicts
from .norms.task import RouteBlock
from .robot import ProgressCallback, Robot, unity_pose_to_ros, unity_to_ros
from .state import StateStore

log = logging.getLogger(__name__)

DROP_HEIGHT = 0.05      # 落とすとき、物体の底を領域の上面からどれだけ上で離すか [m]
STALE_OBJECT = 0.02     # 計画したときから物体がこれ以上動いていたら古い [m]
STALE_TARGET = 0.01     # 置き位置がこれ以上変わっていたら古い [m]
MAX_ROUNDS = 5          # 家庭ルールに合わせて計画し直す回数の上限


def step_key(step: Step) -> str:
    return f"{step.object_id}->{step.to.region_id if step.to else None}"


def step_key_of(item: dict[str, Any]) -> str:
    """preview の step から、step_key と同じ鍵を作る"""
    return f"{item['object_id']}->{item['to_region']}"


def _dist(a: list[float] | tuple[float, ...], b: list[float] | tuple[float, ...]) -> float:
    return math.dist(a, b)


def approach_stops(scene: SceneSnapshot, object_id: str | None) -> list[list[float]]:
    """その家具の止まる位置（ROS の [x, y, yaw]）。家具が無い・止まる位置が無ければ []"""
    owner = next((o for o in scene.objects if o.id == object_id), None) if object_id else None
    if owner is None:
        region = next((r for r in scene.regions if r.id == object_id), None) if object_id else None
        owner = next((o for o in scene.objects if region is not None and o.id == region.object_id), None)
    out = []
    for p in owner.approach_poses if owner is not None else []:
        x, y, _ = unity_to_ros(p.position)
        qx, qy, qz, qw = p.rotation
        # Unity の正面（+Z）を回した向き -> ROS の座標にして、水平の向きだけ取る
        fx, fz = 2 * (qx * qz + qw * qy), 1 - 2 * (qx * qx + qy * qy)
        fwd = unity_to_ros((fx, 0.0, fz))
        out.append([round(x, 4), round(y, 4), round(math.atan2(fwd[1], fwd[0]), 4)])
    return out


def place_for(scene: SceneSnapshot, step: Step) -> tuple[dict[str, Any], dict[str, Any] | None, str]:
    """step の置き方。(離すときの物体の姿勢, 落ちたあとの姿勢 or None, "drop" | "place")。どれも ROS の座標。"""
    assert step.to is not None
    to = step.to.pose
    region = next((r for r in scene.regions if r.id == step.to.region_id), None)
    owner = next((o for o in scene.objects if region is not None and o.id == region.object_id), None)
    if region is not None and region.box is not None and owner is not None and owner.role == "receptacle":
        obj = next((o for o in scene.objects if o.id == step.object_id), None)
        height = obj.size[1] if obj is not None and obj.size is not None else 0.1
        top = region.box.center[1] + region.box.size[1] / 2
        release = Pose(position=(to.position[0], top + height / 2 + DROP_HEIGHT, to.position[2]), rotation=to.rotation)
        return unity_pose_to_ros(release), unity_pose_to_ros(to), "drop"
    return unity_pose_to_ros(to), None, "place"


class MotionStore:
    def __init__(self, state: StateStore, robot: Robot, events: EventLog,
                 publish: Callable[[], Awaitable[None]]) -> None:
        self.state = state
        self.robot = robot
        self.events = events
        self._publish = publish
        self.status = "none"          # none / planning / ready / failed
        self.error = ""
        self.progress = ""
        self.version = 0              # 計画を頼むたびに上げる（ROS に渡す plan_version）
        self.plan_id: str | None = None  # 計画したときの Plan の id
        self.result: dict[str, Any] | None = None  # ロボットが返した結果（timeline を含む）
        self.entries: dict[str, dict[str, Any]] = {}  # step_key -> 計画したときの step と結果
        self.keepout: list[str] = []     # 計画で避けた領域（実行のときも避ける）
        self.attempts: list[dict[str, Any]] = []  # 家庭ルールに合わせて計画した回ごとの結果（探した条件）
        self.planned_at: str | None = None        # 計画を始めた時刻（家の時計）。経路を通る時刻は、これ + t
        self.epoch = 0                # シーケンスの編集のたびに上げる（計画の途中で編集されたら、その結果は使わない）
        self.notice = ""              # 実行前の再検証で予測が変わったときの説明（住人に見せる）

    # ------------------------------------------------------------------ 見せる

    @property
    def timeline_id(self) -> str | None:
        if self.result is None or self.result.get("timeline") is None:
            return None
        return f"{self.result['plan_id']}/v{self.result['plan_version']}"

    def summary(self) -> dict[str, Any]:
        """state.updated に入れる要約（時間軸そのものは大きいので入れない。motion.get で読む）。"""
        steps: dict[str, dict[str, Any]] = {}
        plan = self.state.plan
        for s in plan.steps if plan else []:
            entry = self.entries.get(step_key(s))
            if entry is None:
                continue
            res = entry["result"]
            stale = self._stale_reason(s, entry)
            steps[s.id] = {
                "status": "stale" if stale else res["status"],
                "reason": stale or res.get("reason", ""),
                "t0": res.get("t0"), "t1": res.get("t1"), "mode": entry["mode"],
                "stop_source": res.get("stop_source") or {},
            }
        timeline = self.result.get("timeline") if self.result else None
        return {
            "status": self.status, "error": self.error, "progress": self.progress,
            "plan_id": self.plan_id, "timeline_id": self.timeline_id,
            "duration": timeline["duration"] if timeline else None,
            "steps": steps,
            "keepout": list(self.keepout), "attempts": list(self.attempts), "planned_at": self.planned_at,
            # 実行中に見張る条件（いまのルールから。監視そのものは monitor.py）
            "monitors": [m.model_dump(mode="json") for m in build_monitors(self.state.all_norms())],
            "preview": self.preview(),
        }

    def preview(self) -> dict[str, Any]:
        """検証済みの予測（ステップ別・最終 After・実行が共通で見る版）。"""
        plan = self.state.plan
        labels = {o.id: o.category for o in self.state.scene.objects}
        planning = self.status == "planning"
        steps: list[dict[str, Any]] = []
        for s in plan.steps if plan else []:
            entry = self.entries.get(step_key(s))
            state, reason, blocked_by = "move", "", []
            if s.status == "infeasible":
                state, reason = "stay_infeasible", s.message or "Can't be placed"
            elif s.status != "ok" or s.to is None:
                state, reason = "stay_rule", s.message or s.status
            else:
                stale = self._stale_reason(s, entry) if entry is not None else ""
                if planning and (entry is None or stale):
                    state = "checking"
                elif entry is None:
                    state, reason = "unverified", (self.error if self.status == "failed" else "") or "Not checked yet"
                elif stale:
                    state, reason = "unverified", stale
                elif entry["result"]["status"] != "ok":
                    state, reason = "stay_infeasible", entry["result"].get("reason") or "Can't plan the motion"
                    blocked_by = list(entry["result"].get("blocked_by") or [])
            steps.append({"step_id": s.id, "index": s.index, "object_id": s.object_id, "label": labels.get(s.object_id, ""),
                          "from_region": s.from_.region_id, "to_region": s.to.region_id if s.to else None,
                          "to_position": list(s.to.pose.position) if s.to else None,
                          "state": state, "reason": reason, "blocked_by": blocked_by})
        if not steps:
            status = "checking" if planning else "none"
        elif planning:
            status = "checking"
        elif any(x["state"] in ("checking", "unverified") for x in steps):
            status = "unverified"
        else:
            status = "ready"
        digest = hashlib.sha1(json.dumps([self.timeline_id, status, steps], sort_keys=True).encode()).hexdigest()[:10]
        return {
            "id": f"pv_{digest}", "status": status, "plan_id": plan.id if plan else None,
            "executable": status == "ready" and any(x["state"] == "move" for x in steps),
            "steps": steps, "suggestion": self._suggestion(steps) if status == "ready" else None,
            "notice": self.notice,
        }

    def outcome(self) -> list[tuple[str, str | None, str]]:
        """予測の要点（順序どおりの 物体・置き先・動くか）。実行前の再検証の前後を比べるのに使う。"""
        return [(x["object_id"], x["to_region"], x["state"]) for x in self.preview()["steps"]]

    def _suggestion(self, steps: list[dict[str, Any]]) -> dict[str, Any] | None:
        """順序を変えれば成立しそうな step があれば、並べ替えを提案する（採用するかは住人が決める。採用したら検証し直す）。"""
        order = [x["object_id"] for x in steps]
        index = {x["object_id"]: i for i, x in enumerate(steps)}
        for i, x in enumerate(steps):
            if x["state"] != "stay_infeasible" or x["object_id"] in self.state.route_blocks:
                continue
            later = [y for y in steps[i + 1:] if y["state"] == "move"]
            blockers = [b for b in x["blocked_by"] if b in index]
            if blockers and all(index[b] > i and steps[index[b]]["state"] == "move" for b in blockers):
                after = max(index[b] for b in blockers)
                message = (f"{x['object_id']} can't be grasped because {', '.join(blockers)} is in the way. "
                           f"Moving {', '.join(blockers)} first may make it work.")
            elif not x["blocked_by"] and step_key_of(x) in self.entries and any(y["from_region"] == x["from_region"] for y in later):
                after = max(index[y["object_id"]] for y in later if y["from_region"] == x["from_region"])
                message = (f"{x['object_id']} can't be moved at this point in the order ({x['reason']}). "
                           "It may work after the objects around it have been moved.")
            else:
                continue
            new_order = [o for o in order if o != x["object_id"]]
            new_order.insert(new_order.index(order[after]) + 1, x["object_id"])
            return {"kind": "reorder", "object_id": x["object_id"], "order": new_order, "message": message}
        return None

    def invalidate(self, from_index: int = 0, reason: str = "The sequence changed") -> None:
        """シーケンスが変わった: from_index 以降の step の検証結果を未確認に戻す（検証し直すまで実行できない）。"""
        self.epoch += 1
        self.notice = ""
        plan = self.state.plan
        current = {step_key(s): s.index for s in (plan.steps if plan else [])}
        for key, entry in self.entries.items():
            if current.get(key, from_index) >= from_index:
                entry["stale"] = reason

    def timeline(self) -> dict[str, Any] | None:
        """時間軸と、計画した step の結果（Web UI 用）。"""
        if self.result is None or self.result.get("timeline") is None:
            return None
        key_of = {e["result"]["step_id"]: k for k, e in self.entries.items()}
        current = {step_key(s): s.id for s in (self.state.plan.steps if self.state.plan else [])}
        return {
            "timeline_id": self.timeline_id,
            "timeline": self.result["timeline"],
            # 計画したときの step id -> いまの Plan の step id（Plan が作り直されて id が変わっていても対応が分かる）
            "step_ids": {sid: current.get(k) for sid, k in key_of.items()},
            "steps": self.result.get("steps", []),
        }

    # ------------------------------------------------------------------ 計画

    def clear(self) -> None:
        self.status, self.error, self.progress, self.result, self.entries, self.plan_id = "none", "", "", None, {}, None
        self.keepout, self.attempts, self.planned_at = [], [], None

    async def plan(self, step_ids: list[str] | None = None, actor: str = "user",
                   on_progress: ProgressCallback | None = None) -> dict[str, Any]:
        plan: Plan | None = self.state.plan
        if plan is None:
            raise ValueError("No Plan (add rules or manual destinations)")
        if self.status == "planning":
            raise ValueError("Planning in progress")
        if self.state.route_blocks:
            # 経路による保留は、計画し直すと変わりうる（時刻が進んだ、など）。解いてから計画する
            asked = {s.object_id for s in plan.steps if not step_ids or s.id in step_ids}
            self.state.clear_route_blocks([o for o in self.state.route_blocks if o in asked])
            plan = self.state.plan
            assert plan is not None
        steps = [s for s in plan.steps if s.status == "ok" and s.to is not None]
        if step_ids:
            by_id = {s.id: s for s in plan.steps}
            missing = [i for i in step_ids if i not in by_id]
            if missing:
                raise ValueError(f"Steps not in the Plan: {missing}")
            steps = [by_id[i] for i in step_ids if by_id[i].status == "ok" and by_id[i].to is not None]
        if not steps:
            raise ValueError("No steps can be planned (no ok steps)")

        scene = self.state.scene
        objects = {o.id: o for o in scene.objects}
        placed: dict[str, tuple[Any, ...]] = {}
        request_steps: dict[str, dict[str, Any]] = {}
        for s in steps:
            release, rest, mode = place_for(scene, s)
            obj = objects.get(s.object_id)
            request_steps[s.id] = {
                "step_id": s.id, "object": s.object_id, "place": release, "rest": rest, "mode": mode,
                "to_region": s.to.region_id if s.to else None,
                "start": unity_pose_to_ros(obj.pose) if obj is not None else None,
                # 止まる位置（Unity で家具に置いたもの）。pick は今ある場所の家具、place は行き先の家具
                "approach": {"pick": approach_stops(scene, obj.region_id if obj is not None else None),
                             "place": approach_stops(scene, s.to.region_id if s.to else None)},
            }
            placed[s.id] = (s, release, rest, mode, obj.position if obj is not None else None)

        log.info("motion: %s を %s に頼む: %s", plan.id, self.robot.kind, ", ".join(
            f"{r['step_id']} {r['object']} -> {placed[r['step_id']][0].to.region_id} ({r['mode']}"
            + ("" if r["start"] else ", 物体の位置が無い")
            + f", 止まる位置 pick {len(r['approach']['pick'])} / place {len(r['approach']['place'])} か所)"
            for r in request_steps.values()))
        # シーンの物体（計画の中での位置を追うのに使う。代役のロボットが読む。ROS は自分の Planning Scene を使う）
        world = [{"id": o.id, "position": unity_to_ros(o.position), "role": o.role, "region": o.region_id,
                  "radius": (max(o.size[0], o.size[2]) / 2) if o.size is not None else 0.05,
                  "height": o.size[1] if o.size is not None else 0.1} for o in scene.objects]
        epoch = self.epoch
        self.notice = ""
        self.status, self.error, self.progress, self.plan_id = "planning", "", "Planning requested", plan.id
        self.events.add("motion", actor, action="plan", plan_id=plan.id, version=self.version + 1,
                        steps=[s.id for s in steps])
        await self._publish()

        async def progress(data: dict[str, Any]) -> None:
            self.progress = f"{data.get('step_id') or ''} {data.get('detail') or ''}".strip()
            log.info("motion: 計画中 %s", self.progress)
            if on_progress is not None:
                await on_progress({"step_id": data.get("step_id"), "detail": data.get("detail")})
            await self._publish()

        # 家庭ルール（領域への進入の禁止）に合うまで、避ける領域を足して計画し直す
        norms = self.state.all_norms()
        zone_rules = {r.id: r for r in monitored(norms) if is_zone_entry(r)}
        task = self.state.active_task
        requester = task.requester if task is not None else None
        keepout: list[str] = []
        blocked: dict[str, RouteBlock] = {}       # step id -> 経路が無い理由
        judged: dict[str, list[Verdict]] = {}     # step id -> 経路の判定（最後に計画した回）
        first_ok: set[str] = set()                # 領域を避けずに計画できた step
        attempts: list[dict[str, Any]] = []
        result: dict[str, Any] = {}
        started = self.state.clock.now()
        for round_no in range(1, MAX_ROUNDS + 1):
            self.version += 1
            active = [r for sid, r in request_steps.items() if sid not in blocked]
            if not active:
                result = {"plan_id": plan.id, "plan_version": self.version, "error": "", "steps": [], "timeline": None}
                break
            request: dict[str, Any] = {"plan_id": plan.id, "plan_version": self.version, "steps": active, "world": world}
            if zone_rules:
                request["keepout_zones"] = self.state.keepout_payload(keepout)
            started = self.state.clock.now()
            try:
                result = await self.robot.plan_motion(request, progress)
            except Exception as e:
                log.exception("motion: 計画に失敗")
                result = {"plan_id": plan.id, "plan_version": self.version, "error": f"{type(e).__name__}: {e}",
                          "steps": [], "timeline": None}
            if result.get("error") or not zone_rules:
                break
            judged = self._judge(result, norms, started, requester)
            statuses = {r["step_id"]: r for r in result.get("steps", [])}
            if round_no == 1:
                first_ok = {sid for sid, r in statuses.items() if r.get("status") == "ok"}
            bad = {sid: vs for sid, vs in judged.items() if any(v.value in ("violated", "undetermined") for v in vs)}
            attempt = {
                "round": round_no, "planned_at": started.isoformat(), "keepout": list(keepout),
                "steps": {sid: {"status": r.get("status"), "reason": r.get("reason") or "",
                                "verdicts": {v.rule_id: v.value for v in judged.get(sid, [])},
                                "enters_at": {v.rule_id: v.t.isoformat() for v in judged.get(sid, []) if v.t is not None}}
                          for sid, r in statuses.items()},
            }
            attempts.append(attempt)
            # 領域を避けたら計画できなくなった step: 禁止に反しない経路が無い
            for sid, r in statuses.items():
                if keepout and r.get("status") != "ok" and sid in first_ok and sid not in blocked:
                    rules = [zone_rules[i] for i in zone_rules if zone_rules[i].target.id in keepout]
                    blocked[sid] = self._block(rules, [], attempts, f"Can't plan while avoiding the zones: {r.get('reason') or ''}", started)
            if not bad:
                break
            violated = {v.rule_id for vs in bad.values() for v in vs if v.value == "violated"}
            known = self.state.zone_polygons()
            more = [zone_rules[i].target.id for i in sorted(violated)
                    if zone_rules[i].target.id not in keepout and zone_rules[i].target.id in known]
            if more:
                keepout.extend(z for z in more if z is not None)
                self.progress = f"Replanning to avoid no-entry zones ({', '.join(keepout)})"
                await self._publish()
                continue
            # 避けても反する（または、判定する情報が足りない）step は外して、残りを計画し直す
            for sid, vs in bad.items():
                rules = [zone_rules[v.rule_id] for v in vs if v.value in ("violated", "undetermined")]
                blocked[sid] = self._block(rules, vs, attempts, "", started)
        else:
            result = dict(result, error=result.get("error") or "Couldn't find a path that complies with household rules (too many replans)")

        if result.get("error"):
            log.warning("motion: %s v%d は計画できなかった: %s", plan.id, self.version, result["error"])
        else:
            tl = result.get("timeline") or {}
            log.info("motion: %s v%d の計画が届いた（%.1f 秒、避けた領域 %s）", plan.id, self.version,
                     tl.get("duration") or 0.0, keepout or "なし")
            for r in result.get("steps", []):
                (log.info if r.get("status") == "ok" else log.warning)(
                    "motion:   %s %s: %s%s%s%s", r.get("step_id"), r.get("object"), r.get("status"),
                    f" stops={r.get('stops')}" if r.get("stops") else "",
                    f" stop_source={r.get('stop_source')}" if r.get("stop_source") else "", f" reason: {r.get('reason')}" if r.get("reason") else "")
        if result.get("error"):
            self.status, self.error, self.progress = "failed", str(result["error"]), ""
            self.result, self.entries = None, {}
            self.keepout, self.attempts, self.planned_at = [], attempts, None
        else:
            self.status, self.error, self.progress = "ready", "", ""
            self.result = result
            self.entries = {}
            self.keepout, self.attempts, self.planned_at = list(keepout), attempts, started.isoformat()
            searched = {"planned_at": started.isoformat(), "keepout": list(keepout), "attempts": attempts}
            outcomes = list(result.get("steps", []))
            for sid, block in blocked.items():  # 外した step も、理由つきで結果に入れる
                step = placed[sid][0]
                outcomes.append({"step_id": sid, "object": step.object_id, "status": "infeasible", "reason": block.reason,
                                 "t0": None, "t1": None, "stops": {}})
            result["steps"] = outcomes
            for r in outcomes:
                step, release, rest, mode, start = placed.get(r["step_id"], (None,) * 5)
                if step is None:
                    continue
                self.entries[step_key(step)] = {
                    "result": r, "place": release, "rest": rest, "mode": mode, "start": start,
                    "target": step.to.pose.position if step.to else None, "keepout": list(keepout),
                    "ref": {"plan_id": result["plan_id"], "plan_version": result["plan_version"], "step_id": r["step_id"]},
                }
                if r["step_id"] not in blocked and r.get("status") == "ok":
                    self.state.record_route(step.object_id, judged.get(r["step_id"], []), searched)
            for sid, block in blocked.items():
                self.state.set_route_block(placed[sid][0].object_id, block)
            if self.epoch != epoch:
                # 計画している間にシーケンスが編集された: この結果は前の順序のものなので、使わない
                for entry in self.entries.values():
                    entry["stale"] = "The sequence changed during the check"
        self.events.add("motion", "system", action="result", plan_id=plan.id, version=self.version,
                        error=self.error, steps={r["step_id"]: r["status"] for r in result.get("steps", [])},
                        reasons={r["step_id"]: r.get("reason") for r in result.get("steps", []) if r.get("reason")},
                        keepout=keepout, rounds=len(attempts))
        await self._publish()
        return self.summary()

    def _judge(self, result: dict[str, Any], norms: list[Any], started: Any, requester: str | None) -> dict[str, list[Verdict]]:
        """計画した step ごとに、台車が動く区間を、領域への進入の禁止で判定する。"""
        timeline = result.get("timeline") or {}
        track = timeline.get("base") or []
        zones = self.state.zone_polygons()
        out: dict[str, list[Verdict]] = {}
        for r in result.get("steps", []):
            if r.get("status") != "ok":
                continue
            spans = [(p["t0"], p["t1"]) for p in timeline.get("phases", [])
                     if p.get("step_id") == r["step_id"] and p.get("phase") == "navigating"]
            out[r["step_id"]] = route_verdicts(norms, track, started, zones, requester=requester,
                                               now=self.state.clock.now(), spans=spans)
        return out

    @staticmethod
    def _block(rules: list[Any], verdicts: list[Verdict], attempts: list[dict[str, Any]], detail: str, started: Any) -> RouteBlock:
        names = ", ".join(f"\"{r.original_text}\" ({r.id})" for r in rules) or "household rules"
        missing: dict[tuple[str | None, str], MissingFact] = {}
        for v in verdicts:
            for m in v.missing:
                missing.setdefault((m.entity_id, m.key), m)
        violated = any(v.value == "violated" for v in verdicts) or not missing
        reason = (f"No path that doesn't violate {names}" if violated else f"Not enough information to evaluate {names}") + (f" ({detail})" if detail else "")
        if not verdicts:  # 領域を避けたら計画できなかった: その領域の禁止に反する、という予測として残す
            verdicts = [Verdict(rule_id=r.id, value="violated", basis="predicted", entity_id=r.target.id,
                                detail="No path that avoids the zone") for r in rules]
        bad = [v for v in verdicts if v.value in ("violated", "undetermined")]
        return RouteBlock(reason=reason, verdicts=bad, missing=[] if violated else list(missing.values()),
                          searched={"planned_at": started.isoformat(), "attempts": list(attempts)})

    # ------------------------------------------------------------------ 実行で使う

    def _stale_reason(self, step: Step, entry: dict[str, Any]) -> str:
        if entry.get("stale"):
            return str(entry["stale"])
        obj = next((o for o in self.state.scene.objects if o.id == step.object_id), None)
        if obj is not None and entry["start"] is not None and _dist(obj.position, entry["start"]) > STALE_OBJECT:
            return f"After planning, {step.object_id} moved {_dist(obj.position, entry['start']) * 100:.0f} cm"
        if step.to is not None and entry["target"] is not None and _dist(step.to.pose.position, entry["target"]) > STALE_TARGET:
            return "After planning, the placement changed"
        return ""

    def entry_for(self, step: Step, holding: bool = False) -> dict[str, Any] | None:
        """実行に使える計画（ok で古くない）。holding（もう持っている）なら、物体の位置は確かめない。"""
        entry = self.entries.get(step_key(step))
        if entry is None or entry["result"]["status"] != "ok":
            return None
        reason = self._stale_reason(step, entry)
        if reason and not (holding and reason.startswith("After planning, " + step.object_id)):
            return None
        return entry

    def infeasible_reason(self, step: Step) -> str | None:
        """検証して「動作が成立しない」と分かった step なら、その理由（古い結果は数えない）。そうでなければ None"""
        entry = self.entries.get(step_key(step))
        if entry is None or entry["result"]["status"] == "ok" or self._stale_reason(step, entry):
            return None
        return entry["result"].get("reason") or "Can't plan the motion"

    def missing(self, steps: list[Step], skip_infeasible: bool = False) -> list[str]:
        """実行に使える計画が無い step と理由。skip_infeasible なら、検証して成立しないと分かった step は数えない
        （実行の対象から外すだけで、ほかの step は実行できる）。"""
        out = []
        for s in steps:
            entry = self.entries.get(step_key(s))
            if entry is None:
                out.append(f"{s.id}: not planned")
            elif skip_infeasible and self.infeasible_reason(s) is not None:
                continue
            elif entry["result"]["status"] != "ok":
                out.append(f"{s.id}: couldn't be planned ({entry['result'].get('reason', '')})")
            elif self._stale_reason(s, entry):
                out.append(f"{s.id}: stale ({self._stale_reason(s, entry)})")
        return out

    def forget(self, step: Step) -> None:
        """実行し終わった step の計画を捨てる。"""
        self.entries.pop(step_key(step), None)


__all__ = ["MotionStore", "approach_stops", "place_for", "step_key", "unity_to_ros"]
