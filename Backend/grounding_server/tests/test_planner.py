from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from coground_server.main import create_app
from coground_server.models import Rule, Scenario, SceneSnapshot
from coground_server.planner import plan_steps
from coground_server.state import StateStore

FIXTURES = Path(__file__).parent / "fixtures"
TABLETOP = json.loads((FIXTURES / "tabletop_scene.json").read_text())


def rule(rid: str, attribute: str, equals, target: str) -> Rule:
    return Rule(id=rid, text=rid, condition={"attribute": attribute, "equals": equals}, target_region=target)


def tabletop() -> SceneSnapshot:
    return SceneSnapshot.model_validate(TABLETOP)


def test_shelf_scenario_matches_ground_truth():
    scenario = Scenario.model_validate_json((FIXTURES / "shelf_scenario.json").read_text())
    steps = plan_steps(scenario.initial_scene, scenario.rules)
    expected = scenario.ground_truth_plan.steps
    assert [s.model_dump(exclude={"message"}) for s in steps] == [s.model_dump(exclude={"message"}) for s in expected]


def test_no_rules_no_steps():
    assert plan_steps(tabletop(), []) == []


def test_dishes_go_to_sink_without_overlap():
    scene = tabletop()
    steps = plan_steps(scene, [rule("r1", "group", "dish", "sink_1")])
    assert [s.object_id for s in steps] == ["plate_1", "mug_1", "glass_1", "cup_det_7"]
    assert [s.id for s in steps] == ["s1", "s2", "s3", "s4"]
    assert all(s.status == "ok" and s.rule_id == "r1" and s.to.region_id == "sink_1" for s in steps)
    assert all(s.from_.region_id == "table_1" for s in steps)

    sink = next(r for r in scene.regions if r.id == "sink_1").box
    sizes = {o.id: o.size for o in scene.objects}
    placed = []
    for s in steps:
        p, size = s.to.pose.position, sizes[s.object_id]
        assert sink.contains(p)
        assert p[1] == pytest.approx(sink.center[1] - sink.size[1] / 2 + size[1] / 2)  # 底に置く
        placed.append((p, max(size[0], size[2]) / 2))
    for i, (a, ra) in enumerate(placed):
        for b, rb in placed[i + 1:]:
            assert ((a[0] - b[0]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5 >= ra + rb


def test_object_already_in_target_is_skipped():
    scene = tabletop()
    assert plan_steps(scene, [rule("r1", "group", "dish", "table_1")]) == []


def test_conflicting_rules_are_ambiguous():
    steps = plan_steps(tabletop(), [
        rule("r1", "category", "mug", "sink_1"),
        rule("r2", "fragile", True, "trash_bin_burnable"),
    ])
    mug = next(s for s in steps if s.object_id == "mug_1")
    assert mug.status == "ambiguous" and mug.to is None and mug.rule_id is None
    assert mug.candidate_rule_ids == ["r1", "r2"]
    plate = next(s for s in steps if s.object_id == "plate_1")
    assert plate.status == "ok" and plate.rule_id == "r2"


def test_missing_target_region_is_unmatched():
    steps = plan_steps(tabletop(), [rule("r1", "category", "fork", "drawer_1")])
    assert len(steps) == 1
    assert steps[0].status == "unmatched" and steps[0].to is None and steps[0].rule_id == "r1"
    assert "drawer_1" in steps[0].message


def test_full_region_falls_back_to_center_with_message():
    scene = SceneSnapshot.model_validate({
        "objects": [
            {"id": "a", "category": "cup", "position": [0, 0.05, 0], "size": [0.1, 0.1, 0.1]},
            {"id": "b", "category": "cup", "position": [1, 0.05, 0], "size": [0.1, 0.1, 0.1]},
        ],
        "regions": [{"id": "tray", "label": "tray", "box": {"center": [5, 0.1, 0], "size": [0.12, 0.2, 0.12]}}],
    })
    a, b = plan_steps(scene, [rule("r1", "category", "cup", "tray")])
    assert a.to.pose.position == (5.0, 0.05, 0.0) and a.message is None
    assert b.to.pose.position == (5.0, 0.05, 0.0) and b.message is not None


def test_rotated_region_places_inside():
    s = 2 ** -0.5  # Y 軸まわりに 90 度
    scene = SceneSnapshot.model_validate({
        "objects": [
            {"id": "blocker", "category": "cup", "position": [0, 0.05, 0], "size": [0.1, 0.1, 0.1], "region_id": "long"},
            {"id": "a", "category": "fork", "position": [3, 0.05, 0], "size": [0.1, 0.1, 0.1]},
        ],
        "regions": [{"id": "long", "label": "long",
                     "box": {"center": [0, 0.1, 0], "size": [1.0, 0.2, 0.1], "rotation": [0, s, 0, s]}}],
    })
    (step,) = plan_steps(scene, [rule("r1", "category", "fork", "long")])
    p = step.to.pose.position
    assert scene.regions[0].box.contains(p)
    assert abs(p[0]) < 1e-6 and abs(p[2]) >= 0.1  # 長い軸はワールドの Z を向く


def test_state_replans_and_keeps_unchanged_plan():
    state = StateStore()
    assert state.set_scene(tabletop()) == 1
    assert state.plan is None

    state.set_rules([rule("r1", "waste_type", "burnable", "trash_bin_burnable")])
    plan = state.plan
    assert plan.id == "plan_1" and plan.version == 1 and plan.base_scene_version == 2
    assert [s.object_id for s in plan.steps] == ["tissue_1"]

    state.set_scene(tabletop())  # 同じシーンを送り直しても Plan は変わらない
    assert state.version == 3 and state.plan is plan

    moved = json.loads(json.dumps(TABLETOP))
    next(o for o in moved["objects"] if o["id"] == "tissue_1")["position"] = [-1.0, 0.1, 1.0]  # ごみ箱に入った
    state.set_scene(SceneSnapshot.model_validate(moved))
    assert state.plan.id == "plan_2" and state.plan.steps == [] and state.plan.base_scene_version == 4

    state.set_rules([])
    assert state.plan is None


def test_rules_set_over_websocket():
    with TestClient(create_app()) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json(), ws.receive_json()  # welcome, state.updated

        def call(rid, method, params):
            ws.send_json({"type": "request", "id": rid, "method": method, "params": params})
            msgs = []
            while not msgs or msgs[-1]["type"] != "response":
                msgs.append(ws.receive_json())
            return msgs

        call("u-1", "scene.update", TABLETOP)
        rules = [
            {"id": "r1", "text": "Dishes to the sink", "condition": {"attribute": "group", "equals": "dish"}, "target_region": "sink_1"},
            {"id": "r2", "text": "Forks to the drawer", "condition": {"attribute": "category", "equals": "fork"}, "target_region": "drawer_1"},
        ]
        *events, response = call("u-2", "rules.set", {"rules": rules})
        assert response["ok"] is True
        assert response["result"] == {"version": 2, "rules": 2, "steps": 5, "unknown_regions": ["drawer_1"]}
        plan = events[-1]["data"]["plan"]
        assert plan["id"] == "plan_1" and plan["base_scene_version"] == 2
        assert plan["steps"][0]["from"]["region_id"] == "table_1" and plan["steps"][0]["to"]["region_id"] == "sink_1"

        *_, response = call("u-3", "rules.set", {"rules": [rules[0], rules[0]]})
        assert response["ok"] is False and response["error"]["code"] == "invalid_params"


# ---------------------------------------------------------------- 手で指定した行き先（plan.place）


def test_manual_placement_ignores_rules():
    # ルールは「食器はシンクへ」。手では皿をごみ箱へ（ルールに合わないが、確かめない）
    steps = plan_steps(tabletop(), [rule("r1", "group", "dish", "sink_1")], {"plate_1": "trash_bin_burnable"})
    by = {s.object_id: s for s in steps}
    plate = by["plate_1"]
    assert plate.status == "ok" and plate.to.region_id == "trash_bin_burnable"
    assert plate.rule_id is None and plate.locked is True
    assert by["mug_1"].rule_id == "r1" and by["mug_1"].locked is False  # ほかの物はルールのまま


def test_manual_placement_to_missing_region_is_unmatched():
    (step,) = plan_steps(tabletop(), [], {"plate_1": "drawer_1"})
    assert step.status == "unmatched" and step.to is None and step.locked is True


def test_state_manual_placement_without_rules_and_cleared_on_arrival():
    state = StateStore()
    state.set_scene(tabletop())
    state.set_placement("tissue_1", "trash_bin_plastic")
    assert [(s.object_id, s.to.region_id) for s in state.plan.steps] == [("tissue_1", "trash_bin_plastic")]
    assert state.snapshot()["placements"] == [{"object_id": "tissue_1", "target_region": "trash_bin_plastic"}]

    state.set_placement("tissue_1", "trash_bin_burnable")  # 指定し直す
    assert [(s.object_id, s.to.region_id) for s in state.plan.steps] == [("tissue_1", "trash_bin_burnable")]

    moved = json.loads(json.dumps(TABLETOP))
    next(o for o in moved["objects"] if o["id"] == "tissue_1")["position"] = [-1.0, 0.1, 1.0]  # ごみ箱に入った
    state.set_scene(SceneSnapshot.model_validate(moved))
    assert state.placements == {} and state.plan is None  # 運び終わったら指定は消える

    state.set_placement("plate_1", "sink_1")
    state.set_placement("mug_1", "sink_1")
    state.clear_placements("plate_1")
    assert [s.object_id for s in state.plan.steps] == ["mug_1"]
    state.clear_placements()
    assert state.plan is None


def test_plan_place_over_websocket():
    with TestClient(create_app()) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json(), ws.receive_json()  # welcome, state.updated

        def call(rid, method, params):
            ws.send_json({"type": "request", "id": rid, "method": method, "params": params})
            msgs = []
            while not msgs or msgs[-1]["type"] != "response":
                msgs.append(ws.receive_json())
            return msgs

        call("u-1", "scene.update", TABLETOP)
        *events, response = call("u-2", "plan.place", {"object_id": "plate_1", "target_region": "trash_bin_burnable"})
        assert response["ok"] is True and response["result"]["already_there"] is False
        assert response["result"]["step"]["to"]["region_id"] == "trash_bin_burnable"
        data = events[-1]["data"]
        assert data["placements"] == [{"object_id": "plate_1", "target_region": "trash_bin_burnable"}]
        assert data["plan"]["steps"][0]["locked"] is True and data["plan"]["steps"][0]["rule_id"] is None

        *_, response = call("u-3", "plan.place", {"object_id": "plate_1", "target_region": "table_1"})
        assert response["ok"] is True and response["result"] == {"version": 3, "already_there": True, "step": None}

        *_, response = call("u-4", "plan.place", {"object_id": "nope", "target_region": "sink_1"})
        assert response["ok"] is False and response["error"]["code"] == "invalid_params"
        *_, response = call("u-5", "plan.place", {"object_id": "plate_1", "target_region": "nope"})
        assert response["ok"] is False and response["error"]["code"] == "invalid_params"

        call("u-6", "plan.place", {"object_id": "mug_1", "target_region": "sink_1"})
        *events, response = call("u-7", "plan.unplace", {})
        assert response["ok"] is True and response["result"]["placements"] == 0
        assert events[-1]["data"]["plan"] is None


def fallback(rid: str, target: str) -> Rule:
    return Rule(id=rid, text=rid, condition=None, target_region=target)


def test_fallback_rule_takes_items_no_other_rule_matches():
    scene = tabletop()
    steps = plan_steps(scene, [rule("dish", "group", "dish", "sink_1"), fallback("rest", "trash_bin_burnable")])
    objs = {o.id: o for o in scene.objects}
    items = [o for o in scene.objects if o.role == "item"]
    assert {s.object_id for s in steps} == {o.id for o in items if o.region_id not in ("sink_1", "trash_bin_burnable")}
    for s in steps:
        assert s.status == "ok"
        expected = "dish" if objs[s.object_id].group == "dish" else "rest"
        assert s.rule_id == expected
        assert s.to.region_id == ("sink_1" if expected == "dish" else "trash_bin_burnable")


def test_fallback_rule_alone_moves_every_item():
    scene = tabletop()
    steps = plan_steps(scene, [fallback("rest", "sink_1")])
    assert {s.object_id for s in steps} == {o.id for o in scene.objects if o.role == "item" and o.region_id != "sink_1"}


def test_two_fallback_rules_with_different_targets_are_ambiguous():
    steps = plan_steps(tabletop(), [fallback("a", "sink_1"), fallback("b", "trash_bin_burnable")])
    assert steps and all(s.status == "ambiguous" and s.candidate_rule_ids == ["a", "b"] for s in steps)


def test_rule_condition_null_is_fallback():
    r = Rule.model_validate({"id": "r", "text": "Otherwise", "condition": None, "target_region": "sink_1"})
    assert r.is_fallback
    assert not rule("x", "group", "dish", "sink_1").is_fallback
