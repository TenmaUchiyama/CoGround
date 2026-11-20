"""訂正の種類を広げる（rules.update / zones.update / rules.add_exception）と、言葉からのルール登録（norms.compile、
rules.confirm）、依頼の解釈（task.request の interpret）。LLM は FakeLlm。"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from coground_server.llm import FakeLlm
from coground_server.llm.compile_rule import compile_norms, interpret_task
from coground_server.main import create_app
from coground_server.norms import NormRule

from test_home_rules import R2, R3, WALL, ZONE, Rig, run, unity, zone
from test_norms import R1, R3A, R3B
from test_task import TEXT, call, request, scene, scene_json, store
from test_websocket import connect


def changes(correction) -> list[tuple[str, str, object, object]]:
    return [(c.object_id, c.what, c.before, c.after) for c in correction.changes]


# ---------------------------------------------------------------- 訂正


def test_rules_update_scope_reopens_the_route_and_reports_the_difference():
    async def main() -> None:
        rig = Rig([R3, R2], "18:05", zones=[zone(WALL)])
        await rig.motion.plan()
        assert rig.cup.exec_state == "deferred"  # 18 時からの禁止で、棚へ行く道が無い

        c = rig.state.update_norm("R2", lambda r: r.model_copy(update={
            "scope": r.scope.model_validate({**r.scope.model_dump(by_alias=True), "from": "19:00"})}))
        assert (c.kind, c.entity_id, c.key, c.object_id) == ("rule", "R2", "scope", None)
        assert (c.before["from"], c.after["from"]) == ("18:00", "19:00") and c.affected_rule_ids == ["R2"]
        assert changes(c) == [
            ("cup_B", "exec_state", "deferred", "pending"),
            ("cup_B", "verdict:R2", "violated (predicted)", "undetermined (predicted)"),  # 経路を計画し直すまで未確定
        ]
        assert rig.task.corrections == [c]
        summary = await rig.motion.plan()  # 19 時からなら、いまは通れる
        assert summary["steps"]["s1"]["status"] == "ok" and summary["keepout"] == []
        assert rig.cup.verdicts["R2"].value == "not_applicable"
        with pytest.raises(ValueError):
            rig.state.update_norm("nope", lambda r: r)
        await rig.ex.close()

    run(main())


def test_zones_update_shape_reopens_the_route():
    async def main() -> None:
        rig = Rig([R3, R2], "18:05", zones=[zone(WALL)])
        await rig.motion.plan()
        assert rig.cup.exec_state == "deferred"
        c = rig.state.update_zone(zone(ZONE))  # 範囲を、棚の手前だけに狭める
        assert (c.kind, c.entity_id, c.key, c.affected_rule_ids) == ("zone", "zone_play", "shape", ["R2"])
        assert ("cup_B", "exec_state", "deferred", "pending") in changes(c)
        summary = await rig.motion.plan()
        assert summary["steps"]["s1"]["status"] == "ok" and summary["keepout"] == ["zone_play"]
        with pytest.raises(ValueError):
            rig.state.update_zone(zone(ZONE, "nowhere"))
        await rig.ex.close()

    run(main())


def exception(requester: str | None, **kw) -> NormRule:
    return NormRule.model_validate({
        "id": "P1", "original_text": "You may touch it when I ask", "norm": "permission", "author": "user_01",
        "scope": {"requester": requester}, "target": {"kind": "object", "id": "plate_A"},
        "requirement": R1.requirement.model_dump(), "exception_of": "R1", **kw})


def test_add_exception_changes_only_the_original_prohibition_for_that_requester():
    state = store()
    task = request(state, requester="user_01")
    assert task.row("plate_A").exec_state == "deferred"
    c = state.add_exception(exception("user_01"))
    assert (c.kind, c.entity_id, c.key, c.affected_rule_ids) == ("exception", "R1", "exception", ["R1", "P1"])
    assert c.after["exception_of"] == "R1" and c.before is None
    assert changes(c) == [
        ("plate_A", "exec_state", "deferred", "pending"),
        ("plate_A", "verdict:R1", "violated (predicted)", "not_applicable (predicted)"),
        ("plate_A", "verdict:R3a", None, "compliant (predicted)"),
    ]
    with pytest.raises(ValueError):
        state.add_exception(exception("user_01"))  # ID が重なる
    with pytest.raises(ValueError):
        state.add_exception(exception("user_01", id="P2", exception_of="R3a"))  # 元が禁止ではない

    other = store()
    task = request(other, requester="user_02")
    assert other.add_exception(exception("user_01")).changes == []  # ほかの人の依頼には効かない
    assert task.row("plate_A").exec_state == "deferred"


# ---------------------------------------------------------------- 言葉からの登録

R2_TEXT = "After 6 pm the kids play around here, so don't go into this area of the living room"
COMPILED = {
    "rules": [
        {"original_text": R2_TEXT, "norm": "prohibition", "scope": {"from": "18:00", "until": None},
         "target": {"kind": "zone", "id": "zone_ref_1"},
         "requirement": {"window": "during_base_motion", "predicate": "footprint_overlaps",
                         "transition": {"from": False, "to": True}},
         "reason": "Because the kids play around",
         "pending_refs": [{"ref": "zone_ref_1", "kind": "zone", "phrase": "this area of the living room"}]},
        {"original_text": "Plates on the upper shelf of the cupboard", "norm": "obligation",
         "target": {"kind": "object", "where": {"attribute": "category", "equals": "plate"}},
         "requirement": {"window": "at_place_complete", "predicate": "placed_in", "args": {"region": "shelf_upper"}}},
        {"original_text": "Chopsticks in the drawer", "norm": "obligation",
         "target": {"kind": "object", "where": {"attribute": "category", "equals": "chopsticks"}},
         "requirement": {"window": "at_place_complete", "predicate": "placed_in", "args": {"region": "drawer_9"}}},
        {"original_text": "You may touch it when I ask", "norm": "permission", "scope": {"requester": "author"},
         "target": {"kind": "object", "id": "plate_A"}, "requirement": {"window": "whole", "predicate": "contact"},
         "exception_of": "R1"},
        {"original_text": "Fly through the sky", "norm": "obligation", "target": {"kind": "robot"},
         "requirement": {"window": "whole", "predicate": "flying"}},
    ],
    "unresolved": ["\"Take care of the rest\" can't become a rule"],
}


def test_compile_norms_separates_confirmed_pending_and_unresolved():
    state = store([R1])
    llm = FakeLlm({"compile_norm": COMPILED})
    rules, pending, unresolved = asyncio.run(compile_norms(
        llm, R2_TEXT, state.scene, zone_ids={r.id: r.label for r in state.scene.regions}, existing=state.all_norms(),
        author="user_01", new_id=lambda taken: state.new_norm_id("N", taken)))

    # すぐ確定するもの: 収納先の義務と、依頼者つきの例外（「私」は登録者に置き換わる）
    assert [(r.id, r.norm, r.author) for r in rules] == [("N2", "obligation", "user_01"), ("N4", "permission", "user_01")]
    assert rules[0].destination == "shelf_upper" and rules[1].scope.requester == "user_01" and rules[1].exception_of == "R1"
    # 範囲が言葉だけでは決まらず、解除時刻も言われていないルールは、登録の途中
    (p,) = pending
    assert (p.rule.id, p.rule.target.id, p.rule.scope.from_, p.rule.scope.until) == ("N1", "zone_ref_1", "18:00", None)
    assert [(r.ref, r.kind, r.phrase) for r in p.pending_refs] == [("zone_ref_1", "zone", "this area of the living room")]
    assert p.unresolved == ["scope.until"] and len(p.notes) == 2
    assert p.rule.original_text == R2_TEXT and p.rule.reason == "Because the kids play around"
    # ルールにできなかったもの: LLM が言った分、シーンに無い行き先、知らない述語
    assert len(unresolved) == 3 and "drawer_9" in unresolved[1] and "flying" in unresolved[2]
    prompt = llm.calls[0]["prompt"]
    assert '"id": "R1"' in prompt and '"id": "shelf_upper"' in prompt and prompt.endswith("# Resident's words\n" + R2_TEXT)


def test_pending_rule_is_not_used_until_confirmed_and_nothing_is_filled_in():
    state = store([R1])
    llm = FakeLlm({"compile_norm": {"rules": COMPILED["rules"][:1]}})
    _, pending, _ = asyncio.run(compile_norms(llm, R2_TEXT, state.scene, zone_ids={}, existing=state.all_norms(),
                                              author=None, new_id=lambda taken: state.new_norm_id("N", taken)))
    state.add_norms([], pending)
    assert [n.id for n in state.norms] == ["R1"] and state.snapshot()["pending_rules"][0]["rule"]["id"] == "N1"

    with pytest.raises(ValueError, match="Unresolved references"):
        state.confirm_pending("N1", {})
    with pytest.raises(ValueError, match="No such zones"):
        state.confirm_pending("N1", {"zone_ref_1": "zone_1"})
    state.define_zone(zone(ZONE, "zone_1"))  # Quest で囲んだ範囲が届いた
    with pytest.raises(ValueError, match="Expiry time"):
        state.confirm_pending("N1", {"zone_ref_1": "zone_1"})  # 解除時刻は勝手に補わない
    assert [n.id for n in state.norms] == ["R1"]

    rule = state.confirm_pending("N1", {"zone_ref_1": "zone_1"}, until="21:00")
    assert (rule.target.id, rule.scope.from_, rule.scope.until) == ("zone_1", "18:00", "21:00")
    assert [n.id for n in state.norms] == ["R1", "N1"] and state.pending_rules == []

    # 「決めない」と住人が決めたときは、until は null のまま確定する
    state.add_norms([], [pending[0].model_copy(update={"rule": pending[0].rule.model_copy(update={"id": "N9"})})])
    kept = state.confirm_pending("N9", {"zone_ref_1": "zone_1"}, keep_open=True)
    assert kept.scope.until is None


def test_interpret_task_keeps_only_known_items():
    llm = FakeLlm({"interpret_task": {"object_ids": ["cup_B", "table_01", "ghost", "cup_B"], "source_region": "table_01"}})
    answer = asyncio.run(interpret_task(llm, "Just tidy the cups", scene()))
    assert (answer.object_ids, answer.source_region) == (["cup_B"], "table_01")
    assert len(answer.unresolved) == 2  # 机（運ぶ物ではない）と、シーンに無い物体


# ---------------------------------------------------------------- WebSocket 経由


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("COGROUND_FAKE_PHASE_DELAY", "0")
    monkeypatch.delenv("COGROUND_ROSBRIDGE_URL", raising=False)
    with TestClient(create_app()) as c:
        yield c


def test_registration_and_corrections_over_websocket(client):
    services = client.app.state.services
    services.llm = FakeLlm({"compile_norm": {"rules": COMPILED["rules"][:2]},
                            "interpret_task": {"object_ids": ["plate_A"], "unresolved": ["Unclear what \"that\" is"]}})
    with connect(client) as (ws, _w, _s):
        assert call(ws, "1", "scene.update", scene_json())["ok"]
        assert call(ws, "2", "norms.set", {"norms": [R1.model_dump(mode="json", by_alias=True)]})["ok"]

        res = call(ws, "3", "norms.compile", {"text": R2_TEXT, "author": "user_01"})["result"]
        assert res["applied"] and [n["id"] for n in res["norms"]] == ["N2"]
        assert res["pending"][0]["pending_refs"][0]["ref"] == "zone_ref_1" and res["pending"][0]["unresolved"] == ["scope.until"]
        assert res["pending"][0]["rule"]["scope"]["until"] is None  # 仕様の JSON の形（from / until）
        assert [n["id"] for n in call(ws, "4", "state.get")["result"]["norms"]] == ["R1", "N2"]

        bad = call(ws, "5", "rules.confirm", {"rule_id": "N1", "refs": {}})
        assert bad["ok"] is False and bad["error"]["code"] == "invalid_params"
        z = call(ws, "6", "zones.define", {"label": "play area", "polygon": unity(ZONE)})["result"]
        assert z["zone"]["id"] == "zone_1" and z["pending_rules"][0]["rule"]["id"] == "N1"
        ok = call(ws, "7", "rules.confirm", {"rule_id": "N1", "refs": {"zone_ref_1": "zone_1"}, "keep_open": True})["result"]
        assert ok["rule"]["target"]["id"] == "zone_1" and ok["pending_rules"] == []

        # 依頼の解釈を LLM に任せる
        task = call(ws, "8", "task.request", {"text": "Tidy that and the plate", "requester": "user_02", "interpret": True})["result"]
        assert [r["object_id"] for r in task["task"]["rows"]] == ["plate_A"] and task["unresolved"] == ["Unclear what \"that\" is"]
        assert task["task"]["rows"][0]["exec_state"] == "deferred"

        # 訂正: 例外（user_02 が頼んだときは、この皿に触ってよい）
        exc = call(ws, "9", "rules.add_exception", {"exception_of": "R1", "requester": "user_02", "object_id": "plate_A",
                                                     "original_text": "You may touch it when user_02 asks"})["result"]
        assert exc["rule"]["id"] == "P1" and exc["correction"]["kind"] == "exception"
        assert {"object_id": "plate_A", "what": "exec_state", "before": "deferred", "after": "pending"} in exc["correction"]["changes"]
        # 訂正: Scope（19 時からにして）と、範囲
        upd = call(ws, "10", "rules.update", {"rule_id": "N1", "from": "19:00", "until": "21:00"})["result"]["correction"]
        assert (upd["kind"], upd["before"]["from"], upd["after"]["from"], upd["after"]["until"]) == ("rule", "18:00", "19:00", "21:00")
        assert call(ws, "11", "rules.update", {"rule_id": "N1"})["error"]["code"] == "invalid_params"
        moved = call(ws, "12", "zones.update", {"id": "zone_1", "polygon": unity(WALL)})["result"]["correction"]
        assert (moved["kind"], moved["affected_rule_ids"]) == ("zone", ["N1"])
        assert call(ws, "13", "zones.update", {"id": "nowhere", "polygon": unity(WALL)})["error"]["code"] == "invalid_params"

        # 人の位置と監視
        people = call(ws, "14", "people.update", {"people": [{"id": "kid_1", "kind": "child", "position": [0, 0, 3]}]})["result"]
        assert people == {"version": people["version"], "people": 1, "held": False}
        state = call(ws, "15", "state.get")["result"]
        assert state["people"] == {"observed": True, "people": [{"id": "kid_1", "kind": "child", "position": [0, 0, 3],
                                                                 "observed_at": None}]}
        assert state["scene"]["people"][0]["id"] == "kid_1" and [z["id"] for z in state["zones"]] == ["zone_1"]
        monitor = call(ws, "16", "monitor.get")["result"]
        assert monitor["held"] is False and [m["rule_id"] for m in monitor["monitors"]] == ["N1"]
        assert state["motion"]["monitors"] == monitor["monitors"] and state["execution"]["monitor"]["holds"] == []
        report = call(ws, "17", "task.report")["result"]
        assert [c["kind"] for c in report["corrections"]] == ["exception", "rule", "zone"]
        assert call(ws, "18", "zones.remove", {"id": "zone_1"})["ok"]


def test_r2_plan_and_execution_over_websocket(client):
    from test_home_rules import scene as nav_scene

    with connect(client) as (ws, _w, _s):
        assert call(ws, "1", "scene.update", nav_scene().model_dump(mode="json"))["ok"]
        assert call(ws, "2", "zones.define", {"id": "zone_play", "polygon": unity(ZONE)})["ok"]
        norms = [n.model_dump(mode="json", by_alias=True) for n in (R3, R2)]
        assert call(ws, "3", "norms.set", {"norms": norms})["ok"]
        assert call(ws, "4", "clock.set", {"time": "18:05", "freeze": True})["ok"]
        assert call(ws, "5", "task.request", {"text": TEXT, "object_ids": ["cup_B"]})["ok"]
        planned = call(ws, "6", "motion.plan")["result"]
        assert planned["keepout"] == ["zone_play"] and [a["keepout"] for a in planned["attempts"]] == [[], ["zone_play"]]
        assert call(ws, "7", "exec.start")["ok"]
        for i in range(200):
            state = call(ws, f"s{i}", "state.get")["result"]
            if state["execution"]["mode"] != "running":
                break
        assert state["execution"]["reason"] == "finished" and state["task"]["rows"][0]["exec_state"] == "done"
        assert state["task"]["rows"][0]["verdicts"]["R2"]["basis"] == "observed"
