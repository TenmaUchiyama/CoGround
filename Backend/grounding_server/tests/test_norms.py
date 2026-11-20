"""家庭ルールの判定（norms/）。設計ガイド Documents/CoGround_Home_Rules.md の R1・R3 と、依頼の記録。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from coground_server.models import Rule, SceneObject, SceneSnapshot
from coground_server.norms import (
    HomeClock, NormRule, TaskRecord, TaskRow, WorldSample, affected_by, candidates, contact_trace, depends_on,
    evaluate, placement_trace,
)
from coground_server.norms.model import Scope, and3, not3, or3
from coground_server.state import StateStore

R1 = NormRule.model_validate({
    "id": "R1", "original_text": "Don't touch fragile things", "norm": "prohibition",
    "target": {"kind": "object", "where": {"attribute": "fragile", "equals": True}},
    "requirement": {"window": "whole", "predicate": "contact"},
})
R3A = NormRule.model_validate({
    "id": "R3a", "original_text": "Plates on the upper shelf of the cupboard, cups on the lower shelf", "norm": "obligation",
    "target": {"kind": "object", "where": {"attribute": "category", "equals": "plate"}},
    "requirement": {"window": "at_place_complete", "predicate": "placed_in", "args": {"region": "shelf_upper"}},
})
R3B = NormRule.model_validate({
    "id": "R3b", "original_text": "Plates on the upper shelf of the cupboard, cups on the lower shelf", "norm": "obligation",
    "target": {"kind": "object", "where": {"attribute": "category", "equals": "cup"}},
    "requirement": {"window": "at_place_complete", "predicate": "placed_in", "args": {"region": "shelf_lower"}},
})
R2 = NormRule.model_validate({
    "id": "R2", "original_text": "After 6 pm the kids play around here, so don't go into this area of the living room",
    "norm": "prohibition", "scope": {"from": "18:00", "until": None},
    "target": {"kind": "zone", "id": "zone_play"},
    "requirement": {"window": "during_base_motion", "predicate": "footprint_overlaps",
                    "transition": {"from": False, "to": True}},
    "reason": "Because the kids play around",
})
RULES = [R1, R2, R3A, R3B]


def obj(oid: str, category: str, **attributes) -> SceneObject:
    return SceneObject(id=oid, category=category, position=(0, 0, 0), attributes=attributes)


PLATE_FRAGILE = obj("plate_A", "plate", fragile=True)
PLATE_UNKNOWN = obj("plate_X", "plate")
CUP = obj("cup_B", "cup", fragile=False, material="plastic")


def at(hhmm: str) -> datetime:
    h, m = hhmm.split(":")
    return datetime(2026, 11, 18, int(h), int(m), tzinfo=timezone(timedelta(hours=9)))


# ---------------------------------------------------------------- 3 値


def test_three_valued_logic():
    assert and3(True, None) is None and and3(False, None) is False and and3(True, True) is True
    assert or3(True, None) is True and or3(False, None) is None and or3(False, False) is False
    assert not3(None) is None and not3(True) is False


# ---------------------------------------------------------------- R1: 接触の禁止


def test_r1_fragile_plate_is_predicted_violation():
    v = evaluate(R1, contact_trace(PLATE_FRAGILE), PLATE_FRAGILE, basis="predicted")
    assert (v.value, v.basis, v.entity_id) == ("violated", "predicted", "plate_A")


def test_r1_unknown_fragility_is_undetermined_and_names_the_missing_fact():
    v = evaluate(R1, contact_trace(PLATE_UNKNOWN), PLATE_UNKNOWN, basis="predicted")
    assert v.value == "undetermined"
    assert [(m.entity_id, m.key) for m in v.missing] == [("plate_X", "attr:fragile")]


def test_r1_not_fragile_is_not_applicable():
    assert evaluate(R1, contact_trace(CUP), CUP, basis="predicted").value == "not_applicable"


def test_r1_without_contact_is_compliant():
    # 触れずに残した皿は、実行時の違反ではない
    trace = [WorldSample(phase="other")]
    assert evaluate(R1, trace, PLATE_FRAGILE, basis="observed").value == "compliant"


# ---------------------------------------------------------------- R3: 収納先の義務


def test_r3_destination_comes_from_obligation():
    assert (R3A.destination, R3B.destination, R1.destination) == ("shelf_upper", "shelf_lower", None)


@pytest.mark.parametrize("seen, expected", [("shelf_lower", "compliant"), ("shelf_upper", "violated")])
def test_r3_observed_placement(seen: str, expected: str):
    v = evaluate(R3B, placement_trace(CUP, seen), CUP, basis="observed")
    assert (v.value, v.basis) == (expected, "observed")


def test_r3_no_observation_is_undetermined():
    trace = [WorldSample(phase="place_complete")]  # 配置は終わったが、どこにあるか見えていない
    v = evaluate(R3B, trace, CUP, basis="observed")
    assert v.value == "undetermined"
    assert [(m.entity_id, m.key) for m in v.missing] == [("cup_B", "object_region")]


def test_r3_is_not_violated_before_place_completes():
    # つかんだ直後に、まだ上段に無いことは違反にならない（評価するのは配置完了時）
    trace = [WorldSample(phase="contact", contact={"plate_A"}, object_regions={"plate_A": None})]
    assert evaluate(R3A, trace, PLATE_FRAGILE, basis="predicted").value == "not_applicable"


def test_r3_does_not_apply_to_other_category():
    assert evaluate(R3A, placement_trace(CUP, "shelf_lower"), CUP, basis="observed").value == "not_applicable"


def test_unknown_plate_still_has_a_destination():
    # 材質不明の皿も、指定先は上段と分かる（R3a は category を見る。R1 だけが未確定）
    assert R3A.target.matches(PLATE_UNKNOWN) is True
    assert R1.target.matches(PLATE_UNKNOWN) is None


# ---------------------------------------------------------------- Scope と例外


def test_scope_time_window():
    evening = Scope.model_validate({"from": "18:00"})
    assert evening.active(at("17:58")) is False and evening.active(at("18:02")) is True
    assert evening.active(None) is None  # 時刻が分からなければ不明
    night = Scope.model_validate({"from": "22:00", "until": "06:00"})
    assert night.active(at("23:00")) is True and night.active(at("05:00")) is True and night.active(at("12:00")) is False
    with pytest.raises(ValueError):
        Scope.model_validate({"from": "6pm"})


def exception_for(requester: str) -> NormRule:
    return NormRule.model_validate({
        "id": "P1", "original_text": "You may touch it only when I instruct you to", "norm": "permission", "author": requester,
        "scope": {"requester": requester}, "target": {"kind": "object", "id": "plate_A"},
        "requirement": {"window": "whole", "predicate": "contact"}, "exception_of": "R1",
    })


def test_exception_narrows_prohibition_only_for_that_requester():
    p1 = exception_for("user_01")
    trace = contact_trace(PLATE_FRAGILE)

    def run(requester: str | None):
        return evaluate(R1, trace, PLATE_FRAGILE, basis="predicted", requester=requester, exceptions=[p1])

    assert run("user_01").value == "not_applicable"
    assert run("user_02").value == "violated"
    unknown = run(None)  # 共有端末で依頼者が分からない: 例外の成立は未確定
    assert unknown.value == "undetermined"
    assert [(m.entity_id, m.key) for m in unknown.missing] == [(None, "requester")]


def test_exception_requires_permission():
    with pytest.raises(ValueError):
        NormRule.model_validate({**R1.model_dump(by_alias=True), "exception_of": "R9"})


def test_permission_alone_is_never_violated():
    v = evaluate(exception_for("user_01"), contact_trace(PLATE_FRAGILE), PLATE_FRAGILE, basis="predicted")
    assert v.value == "not_applicable"


def test_transition_ignores_first_sample():
    # 変化（立ち上がり）を見るルール: 最初の時点ですでに成り立っていても、変化ではない
    rule = NormRule.model_validate({
        "id": "T1", "original_text": "", "norm": "prohibition", "target": {"kind": "object", "id": "cup_B"},
        "requirement": {"window": "whole", "predicate": "contact", "transition": {"from": False, "to": True}},
    })
    inside = [WorldSample(contact={"cup_B"}), WorldSample(contact={"cup_B"})]
    entering = [WorldSample(), WorldSample(contact={"cup_B"})]
    assert evaluate(rule, inside, CUP, basis="predicted").value == "compliant"
    assert evaluate(rule, entering, CUP, basis="predicted").value == "violated"


def test_r2_without_base_pose_or_zone_shape_is_undetermined():
    trace = [WorldSample(t=at("18:02"), phase="base_motion"), WorldSample(t=at("18:03"), phase="base_motion")]
    assert evaluate(R2, trace, None, basis="predicted").value == "undetermined"
    early = [WorldSample(t=at("17:58"), phase="base_motion"), WorldSample(t=at("17:59"), phase="base_motion")]
    assert evaluate(R2, early, None, basis="predicted").value == "not_applicable"  # 時間外は、述語が不明でも非適用


# ---------------------------------------------------------------- 旧 Rule からの変換


def test_legacy_rule_becomes_placement_obligation():
    legacy = Rule(id="r1", text="Dishes in the sink", condition={"attribute": "group", "equals": "dish"}, target_region="sink_1")
    norm = NormRule.from_legacy(legacy)
    assert (norm.norm, norm.destination, norm.original_text) == ("obligation", "sink_1", "Dishes in the sink")
    assert norm.target.matches(PLATE_UNKNOWN) is True and norm.target.matches(obj("fork_1", "fork")) is False

    by_attr = NormRule.from_legacy(Rule(id="r2", text="", condition={"attribute": "trash", "equals": True}, target_region="bin"))
    assert by_attr.target.matches(CUP) is False  # 旧 Rule は、属性が無ければ「合わない」

    fallback = NormRule.from_legacy(Rule(id="r3", text="Everything else in the box", target_region="box"))
    assert fallback.target.fallback and fallback.target.matches(CUP) is True


# ---------------------------------------------------------------- 依存（再評価の候補）


def test_depends_on_and_candidates():
    assert depends_on(R1) == {"contact", "attr:fragile"}
    assert depends_on(R2) == {"base_pose", "zone_shape", "clock"}
    assert depends_on(R3A) == {"object_region", "attr:category"}
    assert [r.id for r in candidates("navigate", RULES)] == ["R2"]
    assert [r.id for r in candidates("pick", RULES)] == ["R1"]
    assert [r.id for r in candidates("place", RULES)] == ["R1", "R3a", "R3b"]


def test_attribute_correction_affects_only_rules_that_read_it():
    assert [r.id for r in affected_by("attr:fragile", RULES)] == ["R1"]
    assert [r.id for r in affected_by("attr:category", RULES)] == ["R3a", "R3b"]
    # 例外（許可）が読む項目が変われば、元の禁止も評価し直す
    assert [r.id for r in affected_by("requester", [*RULES, exception_for("user_01")])] == ["R1", "P1"]


# ---------------------------------------------------------------- 時計


def test_clock_set_freeze_advance_reset():
    real = [datetime(2026, 11, 18, 3, 0, tzinfo=timezone.utc)]  # 家の時計（Asia/Tokyo）では 12:00
    clock = HomeClock(tz="Asia/Tokyo", source=lambda: real[0])
    assert clock.now().strftime("%H:%M") == "12:00" and not clock.overridden

    clock.set(clock.at("17:55"))
    assert clock.now().strftime("%H:%M") == "17:55" and clock.overridden
    real[0] += timedelta(minutes=7)  # 合わせたあとは、実時間と同じ速さで進む
    assert clock.now().strftime("%H:%M") == "18:02"

    clock.freeze(datetime(2026, 11, 18, 17, 59))  # タイムゾーンが無ければ、家の時計の時刻
    real[0] += timedelta(hours=1)
    assert clock.now().strftime("%H:%M") == "17:59"
    clock.advance(60)
    assert clock.now().strftime("%H:%M") == "18:00"
    assert Scope.model_validate({"from": "18:00"}).active(clock.now()) is True

    clock.reset()
    assert not clock.overridden


# ---------------------------------------------------------------- 依頼の記録


def scene(*, cup_region: str | None = "table_01") -> SceneSnapshot:
    def furniture(oid: str, category: str, y: float) -> dict:
        return {"id": oid, "category": category, "position": [0, y, 0], "size": [1, 0.1, 1],
                "place_zone": {"center": [0, y + 0.2, 0], "size": [1, 0.3, 1]}}

    y = {"table_01": 0.9, "shelf_lower": 1.9, None: 5.0}[cup_region]
    return SceneSnapshot.model_validate({"objects": [
        furniture("table_01", "table", 0.7), furniture("shelf_lower", "shelf", 1.7), furniture("shelf_upper", "shelf", 2.7),
        {"id": "plate_A", "category": "plate", "position": [-0.2, 0.9, 0], "attributes": {"fragile": True}},
        {"id": "cup_B", "category": "cup", "position": [0.2, y, 0], "attributes": {"fragile": False}},
    ]})


def test_task_rows_survive_scene_updates():
    state = StateStore()
    state.set_scene(scene())
    task = state.open_task("Clear everything off the desk", ["plate_A", "cup_B"], requester="user_01",
                           source_region="table_01", created_at=at("18:10"))
    assert (task.id, task.object_ids, task.counts()["total"]) == ("task_1", ["plate_A", "cup_B"], 2)
    assert [r.label for r in task.rows] == ["plate", "cup"]

    # コップを下段に収納した（机から無くなった）あとも、分母は 2 のまま
    state.set_scene(scene(cup_region="shelf_lower"))
    assert state.task is task and state.task.counts()["total"] == 2
    # シーンから物体そのものが消えても、行は残る
    state.set_scene(SceneSnapshot())
    assert state.task.object_ids == ["plate_A", "cup_B"]
    assert state.snapshot()["task"]["rows"][1]["object_id"] == "cup_B"


def test_open_task_rejects_unknown_or_duplicate_objects():
    state = StateStore()
    state.set_scene(scene())
    with pytest.raises(ValueError):
        state.open_task("x", ["nope"])
    with pytest.raises(ValueError):
        state.open_task("x", ["cup_B", "cup_B"])
    assert state.task is None and state.snapshot()["task"] is None


def test_row_keeps_destination_predicted_violation_and_deferral_together():
    # 皿の行: 「指定先は上段」「把持候補は R1 違反の予測」「実行は保留」を同時に持つ
    row = TaskRow(object_id="plate_A", destination=R3A.destination, destination_rule_ids=["R3a"])
    grasp = evaluate(R1, contact_trace(PLATE_FRAGILE), PLATE_FRAGILE, basis="predicted", now=at("18:10"))
    assert row.record(grasp) is True
    row.set_state("deferred", "Deferred due to the agreement not to touch fragile things (R1)")
    assert (row.destination, row.verdicts["R1"].value, row.verdicts["R1"].basis, row.exec_state) == (
        "shelf_upper", "violated", "predicted", "deferred")

    # 同じ判定をもう一度記録しても、履歴は増えない（判定した時刻だけが違う）
    again = evaluate(R1, contact_trace(PLATE_FRAGILE), PLATE_FRAGILE, basis="predicted", now=at("18:11"))
    assert row.record(again) is False and len(row.history) == 1

    # 「割れ物ではない」と訂正すると、R1 の判定だけが変わり、履歴に積まれる。指定先はそのまま
    corrected = obj("plate_A", "plate", fragile=False)
    after = evaluate(R1, contact_trace(corrected), corrected, basis="predicted", now=at("18:12"))
    assert row.record(after) is True
    assert [v.value for v in row.history] == ["violated", "not_applicable"]
    assert row.destination == "shelf_upper"


def test_task_counts_by_exec_state():
    task = TaskRecord(id="task_1", text="", rows=[TaskRow(object_id="plate_A"), TaskRow(object_id="cup_B")])
    task.row("plate_A").set_state("deferred", "R1")
    task.row("cup_B").set_state("placed_unverified")
    assert task.counts() == {"total": 2, "done": 0, "deferred": 1, "placed_unverified": 1}
    task.row("cup_B").set_state("done")
    assert task.counts()["done"] == 1 and task.counts()["total"] == 2
    assert task.row("nope") is None
