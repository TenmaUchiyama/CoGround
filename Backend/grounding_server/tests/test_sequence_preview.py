"""シーケンスの編集と、検証済みの予測（motion.preview）。受け入れテスト（家庭内片づけロボットの UX・実装 Plan §5）。

場面（ROS の座標）: 机（x = 2）に手前からマグ（x = 1.95）・皿（x = 2.2）・グラス（割れ物、y = 0.3）。棚（x = 8）に下段と上段。
机の止まる位置は 1 か所（x = 1.4）なので、そこから見てマグは皿の手前にある（マグのほうが背が高く、皿をつかむ手の通り道をふさぐ）。
ロボットは ROS なしの代役（FakeRobot）。
"""

from __future__ import annotations

import asyncio

import pytest

from coground_server.eventlog import EventLog
from coground_server.executor import ExecError
from coground_server.models import SceneRegion, SceneSnapshot
from coground_server.norms import NormRule
from coground_server.robot import FakeRobot
from coground_server.services import Services
from coground_server.state import StateStore

DISHES = NormRule.model_validate({
    "id": "R1", "original_text": "Dishes go on the lower shelf", "norm": "obligation",
    "target": {"kind": "object", "where": {"attribute": "group", "equals": "dish"}},
    "requirement": {"window": "at_place_complete", "predicate": "placed_in", "args": {"region": "shelf_lower"}},
})
FRAGILE = NormRule.model_validate({
    "id": "N1", "original_text": "Don't touch fragile things", "norm": "prohibition",
    "target": {"kind": "object", "where": {"attribute": "fragile", "equals": True}},
    "requirement": {"window": "whole", "predicate": "contact"},
})
BETWEEN = [(4.5, -1.0), (5.5, -1.0), (5.5, 1.0), (4.5, 1.0)]     # 机と棚の間の禁止区域（迂回できる）
SEALED = [(4.5, -30.0), (5.5, -30.0), (5.5, 30.0), (4.5, 30.0)]  # 迂回路もふさぐ


def unity(points):
    return [[-y, 0.0, x] for x, y in points]


def zone(points) -> SceneRegion:
    return SceneRegion(id="zone_no", label="no-entry", polygon=unity(points))


NO_ENTRY = NormRule.model_validate({
    "id": "R2", "original_text": "Don't go into this area", "norm": "prohibition",
    "target": {"kind": "zone", "id": "zone_no"},
    "requirement": {"window": "during_base_motion", "predicate": "footprint_overlaps",
                    "transition": {"from": False, "to": True}},
})


def scene(*, shelf_full: bool = False, items=("mug", "plate", "glass")) -> SceneSnapshot:
    def item(oid, category, x, y, size, **attrs):
        return {"id": oid, "category": category, "position": [-y, 0.9, x], "size": size, "attributes": attrs}

    objects = [
        {"id": "table_01", "category": "table", "position": [0, 0.7, 2.0], "size": [1, 0.1, 1],
         "place_zone": {"center": [0, 0.9, 2.0], "size": [1, 0.3, 1]},
         "approach_poses": [{"position": [0, 0, 1.4]}]},
        {"id": "shelf_lower", "category": "shelf", "position": [0, 0.4, 8.0], "size": [0.4, 0.05, 0.4],
         "place_zone": {"center": [0, 0.5, 8.0], "size": [0.3, 0.2, 0.3] if shelf_full else [1, 0.3, 1]},
         "approach_poses": [{"position": [0, 0, 7.3]}]},
        {"id": "shelf_upper", "category": "shelf", "position": [0, 1.2, 8.0], "size": [0.4, 0.05, 0.4],
         "place_zone": {"center": [0, 1.3, 8.0], "size": [1, 0.3, 1]},
         "approach_poses": [{"position": [0, 0, 7.3]}]},
    ]
    all_items = {
        "mug": item("mug", "mug", 1.95, 0.0, [0.08, 0.1, 0.08], fragile=False),
        "plate": item("plate", "plate", 2.2, 0.0, [0.2, 0.03, 0.2], fragile=False),
        "glass": item("glass", "glass", 2.0, 0.3, [0.07, 0.12, 0.07], fragile=True),
    }
    objects += [all_items[i] for i in items]
    if shelf_full:  # 下段は、置いてある箱でいっぱい
        objects.append({"id": "box", "category": "small_box", "position": [0, 0.45, 8.0], "size": [0.28, 0.1, 0.28]})
    return SceneSnapshot.model_validate({"objects": objects})


def make(norms, targets, *, zones=(), **scene_kw) -> Services:
    state = StateStore()
    state.set_scene(scene(**scene_kw))
    for z in zones:
        state.define_zone(z)
    state.set_norms(norms)
    s = Services(state=state, robot=FakeRobot(phase_delay=0.0), events=EventLog(), auto_motion_plan=False)
    state.open_task("Clear the desk", list(targets), source_region="table_01")
    return s


def states(s: Services) -> dict[str, str]:
    return {x["object_id"]: x["state"] for x in s.motion.preview()["steps"]}


def reason(s: Services, object_id: str) -> str:
    return next(x["reason"] for x in s.motion.preview()["steps"] if x["object_id"] == object_id)


def region(s: Services, object_id: str) -> str | None:
    return s.state.region_of(object_id)


async def finish(s: Services) -> None:
    async def poll():
        while s.executor.mode == "running":
            await asyncio.sleep(0.002)
    await asyncio.wait_for(poll(), 5)


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- 禁止区域と迂回路


def test_detour_around_zone_moves_the_plate_and_blocked_detour_leaves_it():
    async def main():
        s = make([DISHES, NO_ENTRY], ["plate"], zones=[zone(BETWEEN)], items=("plate",))
        assert states(s) == {"plate": "unverified"}  # 作業の候補ができただけでは、移動予定にしない
        await s.motion.plan()
        assert states(s) == {"plate": "move"} and s.motion.keepout == ["zone_no"]
        await s.start_execution(preview_id=s.motion.preview()["id"])
        await finish(s)
        assert region(s, "plate") == "shelf_lower"

        # 迂回路もふさぐと、同じ依頼でも「皿を残す」になり、取りに行かない
        s = make([DISHES, NO_ENTRY], ["plate"], zones=[zone(SEALED)], items=("plate",))
        await s.motion.plan()
        assert states(s) == {"plate": "stay_rule"} and "No path" in reason(s, "plate")
        assert not s.motion.preview()["executable"]
        with pytest.raises(ExecError, match="Nothing to execute"):
            await s.start_execution(preview_id=s.motion.preview()["id"])
        assert region(s, "plate") == "table_01" and not s.executor.history
    run(main())


# ---------------------------------------------------------------- シーケンスの並べ替え


def test_order_changes_step_previews_final_after_and_execution():
    async def main():
        s = make([DISHES], ["mug", "plate"], items=("mug", "plate"))
        await s.motion.plan()
        assert states(s) == {"mug": "move", "plate": "move"}  # マグ → 皿 なら両方

        # 皿 → マグ: 皿は手前のマグにじゃまされて残り、マグだけ動く
        s.motion.invalidate(s.state.sequence_reorder(["plate", "mug"]))
        assert states(s) == {"plate": "unverified", "mug": "unverified"}
        with pytest.raises(ExecError):  # 検証し直すまで、古い After からは実行できない
            await s.start_execution(preview_id=s.motion.preview()["id"])
        await s.motion.plan()
        preview = s.motion.preview()
        assert [x["object_id"] for x in preview["steps"]] == ["plate", "mug"]
        assert states(s) == {"plate": "stay_infeasible", "mug": "move"} and "mug is in the way" in reason(s, "plate")
        assert preview["suggestion"]["order"] == ["mug", "plate"]  # 順序の変更を提案する（採用は住人が決める）

        await s.start_execution(preview_id=preview["id"])
        await finish(s)
        assert region(s, "mug") == "shelf_lower" and region(s, "plate") == "table_01"
        assert all(h["object_id"] != "plate" for h in s.executor.history)
    run(main())


def test_accepting_the_suggestion_moves_both():
    async def main():
        s = make([DISHES], ["plate", "mug"], items=("mug", "plate"))
        await s.motion.plan()
        order = s.motion.preview()["suggestion"]["order"]
        s.motion.invalidate(s.state.sequence_reorder(order))
        await s.motion.plan()
        assert states(s) == {"mug": "move", "plate": "move"} and s.motion.preview()["suggestion"] is None
    run(main())


# ---------------------------------------------------------------- ステップの追加・削除


def test_adding_a_fragile_glass_shows_the_reason_and_removing_updates_the_rest():
    async def main():
        s = make([DISHES, FRAGILE], ["mug", "plate"])
        await s.motion.plan()
        first = s.state.sequence_add("glass", "shelf_upper", index=1)
        s.motion.invalidate(first)
        assert first == 1 and [x["object_id"] for x in s.motion.preview()["steps"]] == ["mug", "glass", "plate"]
        # 前の step（マグ）の結果はそのまま。足した step 以降を確かめ直す
        assert states(s) == {"mug": "move", "glass": "stay_rule", "plate": "unverified"}
        assert "Don't touch fragile things" in reason(s, "glass")
        await s.motion.plan()
        assert states(s) == {"mug": "move", "glass": "stay_rule", "plate": "move"}

        s.motion.invalidate(s.state.sequence_remove("mug"))
        await s.motion.plan()
        # マグを外すと、皿は手前のマグにじゃまされる（残りの順序と予測が変わる）
        assert states(s) == {"glass": "stay_rule", "plate": "stay_infeasible"}
        assert s.state.task.removed == ["mug"]
    run(main())


def test_requested_destination_is_checked_against_storage_rules():
    async def main():
        s = make([DISHES], ["mug"], items=("mug", "plate"))
        s.state.sequence_add("plate", "shelf_upper")  # ルールは下段
        step = next(x for x in s.state.plan.steps if x.object_id == "plate")
        assert step.status == "deferred" and "belongs in shelf_lower" in step.message
        assert states(s)["plate"] == "stay_rule"
    run(main())


# ---------------------------------------------------------------- 配置までの検証


def test_no_free_space_leaves_the_plate_with_a_reason():
    async def main():
        s = make([DISHES], ["plate"], items=("plate",), shelf_full=True)
        assert states(s) == {"plate": "stay_infeasible"} and "No free space" in reason(s, "plate")
        assert not s.motion.preview()["executable"]
    run(main())


# ---------------------------------------------------------------- プレビュー後の環境変化


def test_environment_change_after_preview_stops_the_old_plan():
    async def main():
        s = make([DISHES], ["mug", "plate"], items=("mug", "plate"))
        await s.motion.plan()
        confirmed = s.motion.preview()
        assert states(s) == {"mug": "move", "plate": "move"}

        # プレビューのあとで、棚への道を障害物でふさぐ
        s.robot.obstacles = [[[4.5, -30.0], [5.5, -30.0], [5.5, 30.0], [4.5, 30.0]]]
        with pytest.raises(ExecError, match="situation changed"):
            await s.start_execution(preview_id=confirmed["id"])
        assert s.executor.mode == "idle" and not s.executor.history  # 古い経路で動き出さない
        updated = s.motion.preview()
        assert updated["id"] != confirmed["id"] and "situation changed" in updated["notice"]
        assert states(s) == {"mug": "stay_infeasible", "plate": "stay_infeasible"}

        # 障害物をどけると、更新後の After を確認してから実行できる
        s.robot.obstacles = []
        await s.motion.plan()
        await s.start_execution(preview_id=s.motion.preview()["id"])
        await finish(s)
        assert region(s, "mug") == "shelf_lower" and region(s, "plate") == "shelf_lower"
    run(main())


def test_stale_preview_id_is_refused():
    async def main():
        s = make([DISHES], ["mug", "plate"], items=("mug", "plate"))
        await s.motion.plan()
        old = s.motion.preview()["id"]
        s.motion.invalidate(s.state.sequence_reorder(["plate", "mug"]))
        await s.motion.plan()
        with pytest.raises(ExecError, match="changed after you looked"):
            await s.start_execution(preview_id=old)
    run(main())


# ---------------------------------------------------------------- WebSocket（sequence.* / exec.start の preview_id）


def test_sequence_methods_over_websocket(monkeypatch):
    import time

    from fastapi.testclient import TestClient

    from coground_server.main import create_app

    monkeypatch.setenv("COGROUND_FAKE_PHASE_DELAY", "0")
    monkeypatch.setenv("COGROUND_AUTO_MOTION_PLAN", "1")
    monkeypatch.delenv("COGROUND_ROSBRIDGE_URL", raising=False)

    def call(ws, method, params=None):
        ws.send_json({"type": "request", "id": method + str(time.monotonic_ns()), "method": method, "params": params or {}})
        while True:
            msg = ws.receive_json()
            if msg["type"] == "response":
                return msg

    def preview(ws):
        for _ in range(200):  # 自動の検証が終わるのを待つ
            p = call(ws, "state.get")["result"]["motion"]["preview"]
            if p["status"] != "checking":
                return p
            time.sleep(0.01)
        raise AssertionError("still checking")

    with TestClient(create_app()) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json(), ws.receive_json()
        assert call(ws, "scene.update", scene(items=("mug", "plate")).model_dump(mode="json"))["ok"]
        assert call(ws, "norms.set", {"norms": [DISHES.model_dump(mode="json", by_alias=True)]})["ok"]
        assert call(ws, "task.request", {"text": "Clear the desk", "object_ids": ["mug", "plate"]})["ok"]
        first = preview(ws)
        assert [x["state"] for x in first["steps"]] == ["move", "move"]

        res = call(ws, "sequence.move", {"object_id": "plate", "index": 0})
        assert res["ok"] and res["result"]["first_affected"] == 0 and res["result"]["rechecking"]
        stale = call(ws, "exec.start", {"preview_id": first["id"]})  # 編集の前に見た After からは始められない
        assert not stale["ok"] and stale["error"]["code"] == "invalid_state"
        second = preview(ws)
        assert [(x["object_id"], x["state"]) for x in second["steps"]] == [("plate", "stay_infeasible"), ("mug", "move")]

        assert call(ws, "sequence.reorder", {"object_ids": second["suggestion"]["order"]})["ok"]
        assert call(ws, "sequence.remove", {"object_id": "plate"})["ok"]
        assert not call(ws, "sequence.remove", {"object_id": "plate"})["ok"]
        assert call(ws, "sequence.add", {"object_id": "plate", "index": 1})["ok"]
        third = preview(ws)
        assert [(x["object_id"], x["state"]) for x in third["steps"]] == [("mug", "move"), ("plate", "move")]
        assert call(ws, "exec.start", {"preview_id": third["id"]})["ok"]
