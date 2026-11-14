from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from coground_server.models import Correction, Plan, RegionBox, Rule, Scenario, SceneRegion, SceneSnapshot, TrialLog
from coground_server.state import StateStore

FIXTURES = Path(__file__).parent / "fixtures"
SCENARIO = json.loads((FIXTURES / "shelf_scenario.json").read_text())
TABLETOP = json.loads((FIXTURES / "tabletop_scene.json").read_text())


def test_scenario_loads_and_rule_matches():
    sc = Scenario.model_validate(SCENARIO)
    glass, plastic = sc.initial_scene.objects
    assert sc.rules[0].condition.matches(glass)
    assert not sc.rules[0].condition.matches(plastic)
    assert sc.presented_plan.step("s1").to.region_id == "shelf_upper"


def test_step_uses_from_on_the_wire():
    plan = Plan.model_validate(SCENARIO["presented_plan"])
    assert plan.steps[0].from_.region_id == "table_top"
    dumped = plan.model_dump(mode="json")
    assert "from" in dumped["steps"][0] and "from_" not in dumped["steps"][0]
    assert Plan.model_validate(dumped) == plan


def test_state_snapshot_has_scene_rules_plan():
    sc = Scenario.model_validate(SCENARIO)
    store = StateStore()
    assert store.snapshot()["plan"] is None
    store.set_scene(sc.initial_scene)
    store.set_rules(sc.rules)
    store.set_plan(sc.presented_plan)
    snap = store.snapshot()
    assert snap["version"] == 3
    assert snap["rules"][0]["id"] == "rule_2"
    assert snap["plan"]["steps"][1]["from"]["region_id"] == "table_top"
    assert "constraints" not in snap
    json.dumps(snap)


def test_scenario_rejects_dangling_references():
    bad = copy.deepcopy(SCENARIO)
    bad["injected_errors"][0]["step_id"] = "s9"
    bad["presented_plan"]["steps"][0]["object_id"] = "ghost"
    with pytest.raises(ValidationError) as e:
        Scenario.model_validate(bad)
    assert "s9" in str(e.value) and "ghost" in str(e.value)


def test_plan_rejects_bad_steps():
    steps = copy.deepcopy(SCENARIO["presented_plan"]["steps"])
    steps[1]["index"] = 5
    with pytest.raises(ValidationError):
        Plan(id="p", base_scene_version=0, steps=steps)
    no_to = {k: v for k, v in steps[0].items() if k != "to"}
    with pytest.raises(ValidationError):
        Plan(id="p", base_scene_version=0, steps=[no_to])
    Plan(id="p", base_scene_version=0, steps=[{**no_to, "rule_id": None, "status": "unmatched"}])


def test_region_needs_polygon_or_box():
    with pytest.raises(ValidationError):
        SceneRegion(id="r", label="r")


def test_correction_payload():
    base = {"id": "c1", "plan_id": "plan_1", "plan_version": 1, "step_id": "s1",
            "object_id": "glass_cup_1", "t": 12.5}
    Correction(**base, type="reject")
    Correction(**base, type="move", new_pose={"position": [-2.0, 0.36, 0.5]})
    with pytest.raises(ValidationError):
        Correction(**base, type="move")
    with pytest.raises(ValidationError):
        Correction(**base, type="reorder")


def test_trial_log_events():
    log = TrialLog.model_validate({
        "participant_id": "P01", "condition": "sequence_ghost", "scenario_id": "shelf_fragile_1",
        "events": [
            {"t": 1.0, "type": "view_toggle"},
            {"t": 2.0, "type": "step_select", "step_id": "s1"},
            {"t": 9.0, "type": "correction", "correction_id": "c1"},
            {"t": 15.0, "type": "approve"},
        ],
    })
    assert [e.type for e in log.events] == ["view_toggle", "step_select", "correction", "approve"]
    with pytest.raises(ValidationError):
        TrialLog.model_validate({**log.model_dump(), "events": [{"t": 1.0, "type": "step_select"}]})


# ---------------------------------------------------------------- Scene（片付けタスク、シミュレーションと検出）

def objects_by_id(scene: SceneSnapshot):
    return {o.id: o for o in scene.objects}


def test_tabletop_fills_role_group_regions():
    scene = SceneSnapshot.model_validate(TABLETOP)
    objs = objects_by_id(scene)
    assert (objs["table_1"].role, objs["table_1"].group) == ("surface", "surface")
    assert objs["sink_1"].role == "receptacle"
    assert (objs["mug_1"].role, objs["mug_1"].group) == ("item", "dish")
    assert objs["fork_1"].group == "cutlery" and objs["tissue_1"].group == "trash"
    # place_zone を持つ物体は、同じ ID の領域になる
    regions = {r.id: r for r in scene.regions}
    assert set(regions) == {"table_1", "sink_1", "trash_bin_burnable", "trash_bin_plastic"}
    assert regions["sink_1"].object_id == "sink_1" and regions["sink_1"].label == "sink"
    # 机の上の物は机の領域にある。シンク自身はどこにもない
    assert objs["mug_1"].region_id == "table_1"
    assert objs["sink_1"].region_id is None


def test_tabletop_round_trip_does_not_duplicate_regions():
    scene = SceneSnapshot.model_validate(TABLETOP)
    again = SceneSnapshot.model_validate(scene.model_dump(mode="json"))
    assert again == scene


def test_attribute_shorthand_and_observation():
    objs = objects_by_id(SceneSnapshot.model_validate(TABLETOP))
    fragile = objs["mug_1"].attributes["fragile"]
    assert (fragile.value, fragile.source) == (True, "ground_truth")
    assert objs["mug_1"].observation.source == "simulation"
    det = objs["cup_det_7"]
    assert (det.attributes["fragile"].source, det.attributes["fragile"].confidence) == ("vlm", 0.7)
    assert (det.observation.source, det.observation.tracking) == ("detection", "occluded")


def test_rule_matches_group_and_attributes():
    objs = objects_by_id(SceneSnapshot.model_validate(TABLETOP))
    dishes = Rule(id="r1", text="食器はシンクへ", condition={"attribute": "group", "equals": "dish"},
                  target_region="sink_1")
    plastic = Rule(id="r2", text="プラごみはプラのごみ箱へ",
                   condition={"attribute": "waste_type", "equals": "plastic"}, target_region="trash_bin_plastic")
    assert dishes.condition.matches(objs["plate_1"]) and not dishes.condition.matches(objs["tissue_1"])
    assert plastic.condition.matches(objs["plastic_bottle_1"]) and not plastic.condition.matches(objs["fork_1"])


def test_region_prefers_smallest_box():
    scene = SceneSnapshot.model_validate({"objects": [
        {"id": "table_1", "category": "table", "position": [0, 0.37, 0],
         "place_zone": {"center": [0, 0.9, 0], "size": [2, 0.4, 2]}},
        {"id": "sink_1", "category": "sink", "position": [0.5, 0.8, 0],
         "place_zone": {"center": [0.5, 0.85, 0], "size": [0.4, 0.2, 0.4]}},
        {"id": "plate_1", "category": "plate", "position": [0.5, 0.8, 0]},
    ]})
    assert objects_by_id(scene)["plate_1"].region_id == "sink_1"


def test_rotated_box_contains():
    s = math.sqrt(0.5)
    box = RegionBox(center=(0, 0, 0), rotation=(0, s, 0, s), size=(2.0, 1.0, 0.2))  # Y 軸まわり 90 度
    assert box.contains((0, 0, 0.9))
    assert not box.contains((0.9, 0, 0))


def test_unknown_category_is_item_other():
    scene = SceneSnapshot.model_validate({"objects": [{"id": "x", "category": "remote_control", "position": [0, 0, 0]}]})
    assert (scene.objects[0].role, scene.objects[0].group) == ("item", "other")


def test_region_id_collision_with_object_is_rejected():
    with pytest.raises(ValidationError, match="重複"):
        SceneSnapshot.model_validate({
            "objects": [{"id": "shelf_1", "category": "shelf", "position": [0, 0, 0]}],
            "regions": [{"id": "shelf_1", "label": "shelf", "box": {"center": [0, 0, 0], "size": [1, 1, 1]}}]})
