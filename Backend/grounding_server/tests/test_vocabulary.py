"""語彙の登録簿（norms/vocabulary.py）と、その上に載るもの:

  - ロボットが変えられる状態のすべてについて、内容が書ける
  - 内容は 7 つとも登録でき、判定できる（「入る」と「中にいる」は別の内容）
  - 条件は AND / NOT でつなげる。「満杯なら別の箱」
  - 収納先を決めるとき、条件（Scope）も見る。「…には置くな」は計画した置き先で判定する
  - 語彙に無い内容は、近いもので代用せず「未対応」として返す
  - 内容を足すのは、登録簿に 1 件足すだけ
  - VLM への質問は、ルールが使っている属性から作る
  - レポートは、非該当の照合結果も出す
"""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta

import pytest

from coground_server.llm import FakeLlm
from coground_server.llm.compile_rule import compile_norms, norm_system
from coground_server.models import SceneSnapshot
from coground_server.norms import NormRule, WorldSample, attribute_defs, contact_trace, evaluate, placement_trace, questions
from coground_server.norms import vocabulary
from coground_server.norms.monitors import build_monitors, is_zone_entry, monitored
from coground_server.norms.predicates import PersonAt
from coground_server.norms.report import build_report, judgments
from coground_server.perception import ObjectMemory, Perception
from coground_server.perception.schema import AttributeQuestion
from coground_server.state import StateStore

from test_norms import CUP, PLATE_FRAGILE, R1, R3A, R3B, at, obj
from test_perception import ATTRS, FakeSegmenter, jpeg

SQUARE = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]


def rule(rid: str, norm: str, predicate: str, *, target: dict | None = None, args: dict | None = None,
         scope: dict | None = None, text: str | None = None) -> NormRule:
    return NormRule.model_validate({
        "id": rid, "original_text": text or rid, "norm": norm, "scope": scope or {},
        "target": target or {"kind": "object"}, "requirement": {"predicate": predicate, "args": args or {}}})


def base_trace(points: list[tuple[float, float]], *, speed: float = 0.4, people=None, holding=None) -> list[WorldSample]:
    return [WorldSample(t=at("18:30") + timedelta(seconds=i), phase="base_motion", base=(x, y, 0.0), base_speed=speed,
                        zones={"zone_play": SQUARE}, people=people, holding=holding)
            for i, (x, y) in enumerate(points)]


# ---------------------------------------------------------------- 登録簿


def test_every_state_the_robot_can_change_has_a_content():
    coverage = vocabulary.coverage()
    assert set(coverage) == set(vocabulary.ROBOT_STATES)
    assert all(coverage.values()), coverage
    names = {e.name for e in vocabulary.CONTENTS.values() if not e.legacy}
    assert names == {"contact", "holding", "placed_in", "enter_zone", "in_zone", "base_stopped", "speed_below"}


def test_window_comes_from_the_content_when_not_written():
    assert rule("a", "obligation", "placed_in", args={"region": "shelf"}).requirement.window == "at_place_complete"
    assert rule("b", "prohibition", "enter_zone", target={"kind": "zone", "id": "z"}).requirement.window == "during_base_motion"
    assert rule("c", "prohibition", "contact").requirement.window == "whole"
    # 書いてあれば、そのまま使う（前からあるルール）
    assert R1.requirement.window == "whole" and R3A.requirement.window == "at_place_complete"


def test_prompt_lists_contents_and_conditions_from_the_registry():
    system = norm_system()
    for name in ("contact", "holding", "placed_in", "enter_zone", "in_zone", "base_stopped", "speed_below",
                 "near_person", "holding_something", "base_in_zone", "region_full"):
        assert f"- {name} " in system
    assert "footprint_overlaps" not in system and "- near_child" not in system  # 前の名前は見せない


# ---------------------------------------------------------------- 内容


def test_entering_and_being_inside_are_different_contents():
    zone = {"kind": "zone", "id": "zone_play"}
    enter, inside = rule("enter", "prohibition", "enter_zone", target=zone), rule("inside", "prohibition", "in_zone", target=zone)
    crossing = base_trace([(-1.0, 1.0), (-0.2, 1.0), (1.0, 1.0)])
    staying = base_trace([(1.0, 1.0), (1.1, 1.0)])   # 最初から中にいる
    outside = base_trace([(-2.0, 1.0), (-1.5, 1.0)])
    assert evaluate(enter, crossing, basis="predicted").value == "violated"
    assert evaluate(enter, staying, basis="predicted").value == "compliant"   # 中にいるだけでは「入る」ではない
    assert evaluate(inside, staying, basis="predicted").value == "violated"
    assert evaluate(inside, outside, basis="predicted").value == "compliant"
    # 前の書き方（footprint_overlaps + transition）は「入る」と同じ判定
    old = NormRule.model_validate({"id": "old", "original_text": "", "norm": "prohibition", "target": zone, "requirement": {
        "window": "during_base_motion", "predicate": "footprint_overlaps", "transition": {"from": False, "to": True}}})
    for trace in (crossing, staying, outside):
        assert evaluate(old, trace, basis="predicted").value == evaluate(enter, trace, basis="predicted").value
    assert is_zone_entry(enter) and is_zone_entry(inside) and is_zone_entry(old)


def test_speed_limit_and_stop():
    near = {"when": {"predicate": "near_person", "args": {"kind": "child", "distance": 2.0}}}
    slow = rule("slow", "obligation", "speed_below", target={"kind": "robot"}, args={"limit": 0.2}, scope=near)
    stop = rule("stop", "obligation", "base_stopped", target={"kind": "robot"}, scope=near)
    child = [PersonAt(id="p1", kind="child", xy=(0.5, 0.0))]
    far = [PersonAt(id="p1", kind="child", xy=(9.0, 0.0))]
    assert evaluate(slow, base_trace([(0, 0)], speed=0.4, people=child), basis="predicted").value == "violated"
    assert evaluate(slow, base_trace([(0, 0)], speed=0.1, people=child), basis="predicted").value == "compliant"
    assert evaluate(stop, base_trace([(0, 0)], speed=0.1, people=child), basis="predicted").value == "violated"
    assert evaluate(slow, base_trace([(0, 0)], speed=0.4, people=far), basis="predicted").value == "not_applicable"
    # 人の位置が観測できていなければ未確定（足りない事実を挙げる）
    v = evaluate(slow, base_trace([(0, 0)], speed=0.4, people=None), basis="predicted")
    assert v.value == "undetermined" and [m.key for m in v.missing] == ["person_pose"]
    # 台車が動く間に見張る。応答は内容の登録が決める（止まれば速度の上限も守れる）
    assert [(m.rule_id, m.response, m.entities) for m in build_monitors([slow, stop, R1])] == [
        ("slow", "hold", ["child"]), ("stop", "hold", ["child"])]


def test_holding_and_touching():
    no_carry = rule("carry", "prohibition", "holding", target={"kind": "object", "where": {"attribute": "fragile", "equals": True}})
    assert evaluate(no_carry, contact_trace(PLATE_FRAGILE), PLATE_FRAGILE, basis="predicted").value == "violated"
    assert evaluate(no_carry, contact_trace(CUP), CUP, basis="predicted").value == "not_applicable"
    assert evaluate(R1, contact_trace(PLATE_FRAGILE), PLATE_FRAGILE, basis="predicted").value == "violated"


def test_placing_can_be_forbidden():
    no_bin = rule("nobin", "prohibition", "placed_in", args={"region": "trash_bin"},
                  target={"kind": "object", "where": {"attribute": "fragile", "equals": True}})
    assert evaluate(no_bin, placement_trace(PLATE_FRAGILE, "trash_bin"), PLATE_FRAGILE, basis="predicted").value == "violated"
    assert evaluate(no_bin, placement_trace(PLATE_FRAGILE, "shelf"), PLATE_FRAGILE, basis="predicted").value == "compliant"


# ---------------------------------------------------------------- 条件（AND / NOT）


def test_conditions_combine_with_and_and_not():
    zone = {"kind": "zone", "id": "zone_play"}
    carrying = {"when": {"predicate": "holding_something"}}
    empty_handed = {"when": {"predicate": "holding_something", "negate": True}}
    both = {"when": {"all": [{"predicate": "holding_something"},
                             {"predicate": "near_person", "args": {"distance": 3.0}, "negate": True}]}}
    crossing = [(-1.0, 1.0), (1.0, 1.0)]
    nobody, somebody = [], [PersonAt(id="p", kind="adult", xy=(1.0, 1.5))]

    def value(scope: dict, **state) -> str:
        return evaluate(rule("r", "prohibition", "enter_zone", target=zone, scope=scope),
                        base_trace(crossing, **state), basis="predicted").value

    assert value(carrying, holding={"cup_B"}) == "violated"
    assert value(carrying, holding=set()) == "not_applicable"
    assert value(empty_handed, holding={"cup_B"}) == "not_applicable"
    assert value(empty_handed, holding=set()) == "violated"
    assert value(both, holding={"cup_B"}, people=nobody) == "violated"
    assert value(both, holding={"cup_B"}, people=somebody) == "not_applicable"   # 人がいれば効かない
    assert value(both, holding=set(), people=None) == "not_applicable"           # False ∧ 不明 = False
    v = evaluate(rule("r", "prohibition", "enter_zone", target=zone, scope=carrying), base_trace(crossing), basis="predicted")
    assert v.value == "undetermined" and [m.key for m in v.missing] == ["holding"]
    with pytest.raises(ValueError):
        rule("bad", "prohibition", "contact", scope={"when": {"args": {}}})  # 述語も all も無い


def test_condition_on_where_the_base_is():
    in_kitchen = {"when": {"predicate": "base_in_zone", "args": {"zone": "zone_play"}}}
    slow = rule("slow", "obligation", "speed_below", target={"kind": "robot"}, args={"limit": 0.2}, scope=in_kitchen)
    assert evaluate(slow, base_trace([(1.0, 1.0)], speed=0.4), basis="predicted").value == "violated"
    assert evaluate(slow, base_trace([(-3.0, 1.0)], speed=0.4), basis="predicted").value == "not_applicable"
    assert [r.id for r in monitored([slow])] == ["slow"]


# ---------------------------------------------------------------- 計画: 収納先と条件


def shelves(*, pens: int = 2, white_size: float = 0.12, extra_attrs: dict | None = None) -> SceneSnapshot:
    def furniture(oid: str, category: str, y: float, size: float, attrs: dict | None = None) -> dict:
        return {"id": oid, "category": category, "position": [0, y, 0], "size": [size, 0.1, size], "attributes": attrs or {},
                "place_zone": {"center": [0, y + 0.2, 0], "size": [size, 0.3, size]}}

    items = [{"id": f"pen_{i}", "category": "pen", "position": [-0.3 + 0.2 * i, 0.9, 0], "size": [0.1, 0.02, 0.1],
              "attributes": {"stationery": True}} for i in range(pens)]
    return SceneSnapshot.model_validate({"objects": [
        furniture("table_01", "table", 0.7, 1.0), furniture("box_white", "shelf", 1.7, white_size, extra_attrs),
        furniture("box_red", "shelf", 2.7, 1.0), *items]})


STATIONERY = {"kind": "object", "where": {"attribute": "stationery", "equals": True}}
WHITE_FULL = {"predicate": "region_full", "args": {"region": "box_white"}}
TO_WHITE = rule("W", "obligation", "placed_in", target=STATIONERY, args={"region": "box_white"},
                scope={"when": {**WHITE_FULL, "negate": True}}, text="Stationery goes in the white box")
TO_RED = rule("Rd", "obligation", "placed_in", target=STATIONERY, args={"region": "box_red"},
              scope={"when": WHITE_FULL}, text="If it's full, put it in the red box")


def planned(scene: SceneSnapshot, norms: list[NormRule], ids: list[str], requester: str | None = None) -> StateStore:
    state = StateStore()
    state.set_scene(scene)
    state.set_norms(norms)
    state.open_task("tidy", ids, requester=requester)
    return state


def test_if_the_white_box_is_full_use_the_red_box():
    # 白い箱にはペンが 1 本しか入らない。1 本目は白、2 本目は「満杯なら赤」
    state = planned(shelves(), [TO_WHITE, TO_RED], ["pen_0", "pen_1"])
    assert [(s.object_id, s.status, s.to.region_id, s.rule_id) for s in state.plan.steps] == [
        ("pen_0", "ok", "box_white", "W"), ("pen_1", "ok", "box_red", "Rd")]
    rows = {r.object_id: r for r in state.task.rows}
    assert rows["pen_0"].region_full == {"box_white": False} and rows["pen_1"].region_full == {"box_white": True}
    assert rows["pen_1"].verdicts["Rd"].value == "compliant"   # 条件に使った事実で、置いたあとも判定できる


def test_full_can_be_stated_as_an_attribute_and_corrected():
    # 箱が満杯かどうかを属性で言える（VLM の答えや住人の訂正）。空きの計算より先に使う
    state = planned(shelves(white_size=1.0, extra_attrs={"full": True}), [TO_WHITE, TO_RED], ["pen_0"])
    assert state.plan.steps[0].to.region_id == "box_red"
    correction = state.set_attribute("box_white", "full", False)
    assert state.plan.steps[0].to.region_id == "box_white"
    assert [(c.object_id, c.what, c.before, c.after) for c in correction.changes if c.what == "destination"] == [
        ("pen_0", "destination", "box_red", "box_white")]


def test_destination_rules_respect_scope():
    # 「私が頼んだときだけ上段に」: ほかの人の依頼では、この義務で収納先を決めない
    mine = rule("M", "obligation", "placed_in", target=STATIONERY, args={"region": "box_red"}, scope={"requester": "papa"})
    assert planned(shelves(pens=1), [mine], ["pen_0"], requester="papa").plan.steps[0].to.region_id == "box_red"
    other = planned(shelves(pens=1), [mine], ["pen_0"], requester="mama")
    assert other.plan.steps[0].status == "deferred" and other.plan.steps[0].to is None
    # 時間で分ける: 夜は赤い箱
    night = rule("N", "obligation", "placed_in", target=STATIONERY, args={"region": "box_red"}, scope={"from": "20:00", "until": "23:00"})
    day = rule("D", "obligation", "placed_in", target=STATIONERY, args={"region": "box_white"}, scope={"from": "06:00", "until": "20:00"})
    state = StateStore()
    state.clock.set(at("21:00"))
    state.set_scene(shelves(pens=1, white_size=1.0))
    state.set_norms([night, day])
    state.open_task("tidy", ["pen_0"])
    assert [(s.to.region_id, s.rule_id) for s in state.plan.steps] == [("box_red", "N")]


def test_forbidden_placement_defers_the_object():
    no_red = rule("X", "prohibition", "placed_in", target={"kind": "object", "id": "pen_0"}, args={"region": "box_red"},
                  text="Don't put this pen in the red box")
    to_red = rule("Rd", "obligation", "placed_in", target=STATIONERY, args={"region": "box_red"})
    state = planned(shelves(), [to_red, no_red], ["pen_0", "pen_1"])
    first, second = state.plan.steps
    assert (first.status, second.status) == ("deferred", "ok") and "Don't put this pen" in first.message
    assert state.task.row("pen_0").verdicts["X"].value == "violated"
    assert state.task.row("pen_1").verdicts["X"].value == "not_applicable"


# ---------------------------------------------------------------- 登録: 未対応と属性


def compile_(compiled: dict, state: StateStore | None = None, existing: list[NormRule] | None = None):
    state = state or planned(shelves(), [], [])
    llm = FakeLlm({"compile_norm": compiled})
    zones = {r.id: r.label for r in state.scene.regions}
    out = asyncio.run(compile_norms(llm, "words", state.scene, zone_ids=zones, existing=existing or [], author=None,
                                    new_id=lambda taken: state.new_norm_id("N", taken)))
    return (*out, llm)


def test_unsupported_content_is_reported_not_approximated():
    rules, pending, unresolved, _ = compile_({"rules": [
        {"original_text": "Carry it quietly", "norm": "obligation", "requirement": {"predicate": "quiet"}},
        {"original_text": "Slow down", "norm": "obligation", "target": {"kind": "robot"}, "requirement": {"predicate": "speed_below"}},
        {"original_text": "Don't enter the pen", "norm": "prohibition", "target": {"kind": "object", "id": "pen_0"},
         "requirement": {"predicate": "enter_zone"}},
        {"original_text": "When the drawer is full", "norm": "obligation", "target": STATIONERY,
         "scope": {"when": {"predicate": "region_full", "args": {"region": "drawer_9"}}},
         "requirement": {"predicate": "placed_in", "args": {"region": "box_red"}}},
        {"original_text": "When it rains", "norm": "prohibition", "scope": {"when": {"predicate": "raining"}},
         "requirement": {"predicate": "contact"}},
    ]})
    assert rules == [] and pending == []
    assert "not supported: no content named 'quiet'" in unresolved[0] and "speed_below" in unresolved[0]  # 書ける内容も伝える
    assert "speed_below needs limit" in unresolved[1]
    assert "enter_zone is about a zone, not a object" in unresolved[2]
    assert "drawer_9" in unresolved[3]
    assert "no condition named 'raining'" in unresolved[4]


def test_registration_stores_how_to_recognise_the_attribute():
    fragile = {"original_text": "Don't touch breakable things", "norm": "prohibition",
               "target": {"kind": "object", "where": {"attribute": "fragile", "equals": True}},
               "requirement": {"predicate": "contact"},
               "attribute": {"name": "fragile", "how_to_tell": "Made of glass or ceramic, would break if dropped",
                             "values": ["true", "false"], "visual": True}}
    papa = {"original_text": "Don't touch papa's things", "norm": "prohibition",
            "target": {"kind": "object", "where": {"attribute": "owner", "equals": "papa"}},
            "requirement": {"predicate": "contact"},
            "attribute": {"name": "owner", "how_to_tell": "Who it belongs to", "values": ["papa"], "visual": False}}
    rules, _, unresolved, llm = compile_({"rules": [fragile, papa]}, existing=[R3A])
    assert unresolved == [] and rules[0].requirement.window == "whole"
    defs = {a.name: a for a in attribute_defs([*rules, R3A, R3B])}
    assert set(defs) == {"fragile", "owner"}                      # category は属性ではない（VLM が必ず答える）
    assert defs["fragile"].how_to_tell.startswith("Made of glass") and defs["fragile"].values == ["true", "false"]
    assert defs["fragile"].rule_ids == [rules[0].id] and defs["owner"].visual is False
    assert [q.name for q in questions(rules)] == ["fragile"]      # 画像から分からない属性は VLM に聞かない
    assert questions([R3A, R3B]) == [] and [q.name for q in questions([R1])] == ["fragile"]
    # 次の登録では、いまある属性の名前を LLM に見せる（同じ意味の属性に、同じ名前を使わせる）
    *_, llm2 = compile_({"rules": []}, existing=rules)
    vocabulary_part = llm2.calls[0]["prompt"].split("# Attribute vocabulary\n")[1].split("\n\n")[0]
    assert json.loads(vocabulary_part)["owner"] == "Who it belongs to"


# ---------------------------------------------------------------- 内容を足すのは、登録簿に 1 件


def test_adding_a_content_is_one_registry_entry():
    def arm_raised(sample, obj, args):
        return None if sample.base_speed is None else sample.base_speed > 99  # 何でもよい（代役）

    entry = vocabulary.Entry(name="arm_raised", reads=frozenset({"base_speed"}), evaluate=arm_raised, targets=("robot",),
                             window="whole", checked=frozenset({"motion"}), response="hold",
                             phrase="the arm is raised", description="the arm is raised above the base")
    vocabulary.register("content", entry)
    try:
        assert "- arm_raised " in norm_system()                                    # LLM に見える
        rules, _, unresolved, _ = compile_({"rules": [{"original_text": "Keep the arm up", "norm": "obligation",
                                                       "target": {"kind": "robot"}, "requirement": {"predicate": "arm_raised"}}]})
        assert unresolved == [] and len(rules) == 1                                # 登録できる
        assert evaluate(rules[0], base_trace([(0, 0)]), basis="predicted").value == "violated"   # 判定できる
        assert [m.response for m in build_monitors(rules)] == ["hold"]             # 実行中に見張る
        assert vocabulary.phrase("arm_raised") == "the arm is raised"              # 説明できる
    finally:
        vocabulary.unregister("content", "arm_raised")
    assert "arm_raised" not in vocabulary.PREDICATES and "arm_raised" not in norm_system()


# ---------------------------------------------------------------- VLM への質問はルールから作る


def test_vlm_is_asked_only_what_the_rules_use(tmp_path):
    asked: list[AttributeQuestion] = []

    def answer(system: str, prompt: str) -> dict:
        marks = json.loads(prompt.split("\n", 1)[1].split("\n\n")[0])
        extra = [{"name": "fragile", "value": "false", "evidence": "material: plastic"}] if "- fragile:" in prompt else []
        return {"objects": [{"mark_id": m["mark_id"], **ATTRS[m["mark_id"]], "answers": extra} for m in marks]}

    llm = FakeLlm({"analyze_objects": answer})
    perception = Perception(lambda: llm, segmenter=FakeSegmenter(("mug",)), memory=ObjectMemory(tmp_path / "m.json"),
                            get_questions=lambda: asked)
    first = asyncio.run(perception.analyze(jpeg()))
    assert "fragile" not in first.objects[0].attributes and "also depend on" not in llm.calls[0]["prompt"]

    # 「割れ物には触らない」を登録した: 次の解析から割れ物かを聞く。前に見た物体も、聞いていないので解析し直す
    asked[:] = [AttributeQuestion(name=q.name, how_to_tell=q.how_to_tell, values=q.values) for q in questions([R1])]
    second = asyncio.run(perception.analyze(jpeg()))
    assert second.vlm.calls == 1 and "- fragile:" in llm.calls[1]["prompt"] and "true | false | unknown" in llm.calls[1]["prompt"]
    assert second.objects[0].attributes["fragile"] == "false" and second.objects[0].evidence == {"fragile": "material: plastic"}
    third = asyncio.run(perception.analyze(jpeg()))
    assert third.vlm.calls == 0   # 聞いた属性が記憶にあれば、VLM を呼ばない


# ---------------------------------------------------------------- 非該当も見せる


def test_report_shows_judgments_that_did_not_match():
    cup = obj("cup_B", "cup", fragile={"value": False, "source": "vlm", "confidence": 0.9})
    plate = obj("plate_X", "plate")
    by_rule = {j["rule_id"]: j for j in judgments(cup, [R1, R3A, R3B])}
    assert (by_rule["R1"]["matches"], by_rule["R1"]["actual"], by_rule["R1"]["source"]) == (False, False, "vlm")
    assert "fragile is false (judged by the VLM), not true" in by_rule["R1"]["sentence"] and "doesn't apply" in by_rule["R1"]["sentence"]
    assert by_rule["R3a"]["matches"] is False and by_rule["R3b"]["matches"] is True
    unknown = {j["rule_id"]: j for j in judgments(plate, [R1])}["R1"]
    assert unknown["matches"] is None and "isn't known" in unknown["sentence"]

    # VLM が割れ物の皿を「割れ物ではない」と間違えた: レポートに非該当の理由が出て、住人が直すと判定が変わる
    from test_task import request, store
    state = store()
    state.set_scene(SceneSnapshot.model_validate({**state.scene.model_dump(mode="json"), "objects": [
        {**o.model_dump(mode="json"), "attributes": {"fragile": {"value": False, "source": "vlm"}}} if o.id == "plate_A"
        else o.model_dump(mode="json") for o in state.scene.objects]}))
    request(state)
    report = build_report(state.task, state.all_norms(), objects=state.scene.objects)
    row = next(r for r in report["rows"] if r["object_id"] == "plate_A")
    judged = next(j for j in row["judgments"] if j["rule_id"] == "R1")
    assert row["exec_state"] == "pending" and judged["matches"] is False and judged["source"] == "vlm"
    correction = state.set_attribute("plate_A", "fragile", True)
    assert ("plate_A", "exec_state", "pending", "deferred") in [(c.object_id, c.what, c.before, c.after) for c in correction.changes]
    report = build_report(state.task, state.all_norms(), objects=state.scene.objects)
    judged = next(j for r in report["rows"] if r["object_id"] == "plate_A" for j in r["judgments"] if j["rule_id"] == "R1")
    assert judged["matches"] is True and judged["source"] == "user"


def test_state_carries_what_the_display_needs():
    from test_task import store
    snapshot = store().snapshot()
    contents = {c["name"]: c for c in snapshot["vocabulary"]["contents"]}
    assert contents["enter_zone"]["event"] is True and contents["in_zone"]["event"] is False
    assert contents["enter_zone"]["response"] == "replan" and contents["placed_in"]["phrase"] == "it is placed in {region}"
    assert {c["name"] for c in snapshot["vocabulary"]["conditions"]} >= {"near_person", "region_full", "base_in_zone"}
    assert vocabulary.phrase("near_person", {"kind": "child"}) == "a person (child) is within 5.0 m of the base"
    assert [a["name"] for a in snapshot["attributes"]] == ["fragile"]
    assert set(snapshot["judgments"]) == {"plate_A", "cup_B"}   # 運ぶ物だけ
    cup = {j["rule_id"]: j["matches"] for j in snapshot["judgments"]["cup_B"]}
    assert cup == {"R1": False, "R3a": False, "R3b": True}
