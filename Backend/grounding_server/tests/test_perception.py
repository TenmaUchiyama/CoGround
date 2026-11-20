"""perception（画像 → 検出 → VLM → 物体の記憶）。検出器と VLM は代役（ネットワークも GPU も使わない）。

確かめること（Milestone 1 の完了条件）:
- 同じ object_id を何度解析させても、VLM を呼ぶのは初回の 1 回だけ
- VLM の答えを待っている間（pending）に同じ物体の依頼が来ても、重ねて呼ばない
- 新しい object_id が来たら、その物体のぶんだけ VLM を呼ぶ
"""

from __future__ import annotations

import asyncio
import io
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from coground_server.llm import FakeLlm, LlmError
from coground_server.main import create_app
from coground_server.perception import ObjectMemory, Perception, PerceptionError, Segmentation
from coground_server.perception import som
from coground_server.perception.schema import Detection
from coground_server.perception.segment_client import SegmentError


def jpeg(size=(320, 240)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 200, 200)).save(buffer, "JPEG")
    return buffer.getvalue()


def detection(n: int, cls: str = "cup") -> dict:
    x = 20 + 90 * (n - 1)
    return {"detection_id": n, "class": cls, "bbox": [x, 60, x + 70, 180], "confidence": 0.9,
            "mask": [[x, 60], [x + 70, 60], [x + 70, 180], [x, 180]]}


class FakeSegmenter:
    """決めた検出を返す。classes を変えると、次の画像で見える物体が変わる。"""

    def __init__(self, classes=("mug", "cup", "glass")):
        self.classes = list(classes)
        self.calls = 0

    async def segment(self, data: bytes, embed: bool = False) -> Segmentation:
        self.calls += 1
        return Segmentation.model_validate({
            "image": {"width": 320, "height": 240}, "model": "fake", "infer_ms": 1.0,
            "detections": [detection(n, c) for n, c in enumerate(self.classes, start=1)]})


ATTRS = {
    1: {"category": "mug", "material": "ceramic", "fragility": "likely_fragile", "appearance": "white mug"},
    2: {"category": "cup", "material": "plastic", "fragility": "not_fragile", "appearance": "blue cup"},
    3: {"category": "glass", "material": "glass", "fragility": "likely_fragile", "appearance": "clear glass"},
    4: {"category": "cup", "material": "unknown", "fragility": "uncertain", "appearance": "dark cup"},
}


def answer_requested(system: str, prompt: str) -> dict:
    """頼まれた番号（プロンプトの JSON）にだけ答える VLM の代役。"""
    marks = json.loads(prompt.split("\n", 1)[1])
    return {"objects": [{"mark_id": m["mark_id"], **ATTRS[m["mark_id"]]} for m in marks]}


def make(tmp_path=None, answer=answer_requested, classes=("mug", "cup", "glass")):
    llm = FakeLlm({"analyze_objects": answer})
    perception = Perception(lambda: llm, segmenter=FakeSegmenter(classes),
                            memory=ObjectMemory(tmp_path / "memory.json" if tmp_path else None),
                            runs_dir=tmp_path / "runs" if tmp_path else None)
    return perception, llm


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- VLM を呼ぶ回数


def test_first_analysis_calls_vlm_once_for_all_objects():
    perception, llm = make()
    result = run(perception.analyze(jpeg()))
    assert len(llm.calls) == 1 and llm.calls[0]["images"] == 2  # 元の画像と番号つき画像
    assert result.vlm.calls == 1 and result.vlm.analyzed == ["obj_001", "obj_002", "obj_003"]
    first = result.objects[0]
    assert (first.detection_id, first.object_id, first.cls, first.category) == (1, "obj_001", "mug", "mug")
    assert first.attributes == {"material": "ceramic", "fragility": "likely_fragile", "appearance": "white mug"}
    assert (first.vlm_status, first.attribute_version, first.source) == ("completed", 1, "vlm")


def test_same_ids_ten_times_call_vlm_only_once():
    perception, llm = make()

    async def ten():
        return [await perception.analyze(jpeg()) for _ in range(10)]

    results = run(ten())
    assert len(llm.calls) == 1
    assert [r.vlm.calls for r in results] == [1] + [0] * 9
    assert all(o.source == "memory" and o.attribute_version == 1 for r in results[1:] for o in r.objects)
    assert results[-1].objects[0].attributes == results[0].objects[0].attributes
    stats = perception.memory.stats()
    assert (stats["vlm_calls"], stats["cache_hits"]) == (1, 27)
    assert perception.memory.get("obj_001").vlm_calls == 1


def test_new_id_calls_vlm_only_for_that_object():
    perception, llm = make()
    run(perception.analyze(jpeg(), object_ids=["a", "b", "c"]))
    result = run(perception.analyze(jpeg(), object_ids=["a", "b", "new"]))
    assert len(llm.calls) == 2
    assert result.vlm.analyzed == ["new"] and result.vlm.reused == ["a", "b"]
    assert json.loads(llm.calls[1]["prompt"].split("\n", 1)[1]) == [{"mark_id": 3, "detector_class": "glass"}]
    assert [o.source for o in result.objects] == ["memory", "memory", "vlm"]


def test_concurrent_requests_do_not_duplicate_vlm_calls(monkeypatch):
    """VLM の答えを待っている間（pending）に同じ物体の依頼が来ても、重ねて呼ばない。"""
    from coground_server.perception import pipeline

    # 画像を描く時間で順番が変わらないように、描かない
    monkeypatch.setattr(pipeline, "_render", lambda data, detections: (data, data, data))
    calls = 0

    async def scenario():
        started, gate = asyncio.Event(), asyncio.Event()

        class SlowLlm:
            async def generate(self, *, name, system, prompt, output, images=None):
                nonlocal calls
                calls += 1
                started.set()
                await gate.wait()
                return output.model_validate(answer_requested(system, prompt))

        slow = SlowLlm()
        perception = Perception(lambda: slow, segmenter=FakeSegmenter())
        tasks = [asyncio.create_task(perception.analyze(jpeg())) for _ in range(5)]
        await started.wait()
        await asyncio.sleep(0.3)  # 残りの 4 つが「待つ」ところまで進む
        assert perception.memory.stats()["pending"] == 3  # 答えを待っている間は pending
        gate.set()
        return await asyncio.gather(*tasks)

    results = run(scenario())
    assert calls == 1
    assert sorted(r.vlm.calls for r in results) == [0, 0, 0, 0, 1]
    assert {o.source for r in results if r.vlm.calls == 0 for o in r.objects} == {"waited"}
    assert all(o.vlm_status == "completed" and o.attributes["material"] for r in results for o in r.objects)


def test_reanalyze_bumps_attribute_version():
    perception, llm = make()
    run(perception.analyze(jpeg()))
    result = run(perception.analyze(jpeg(), reanalyze=True))
    assert len(llm.calls) == 2
    assert [o.attribute_version for o in result.objects] == [2, 2, 2]


# ---------------------------------------------------------------- VLM の答えが足りない・失敗


def test_unknown_material_is_kept_as_unknown():
    perception, _ = make(classes=("mug", "cup", "glass", "cup"))
    result = run(perception.analyze(jpeg()))
    assert result.objects[3].attributes["material"] == "unknown"
    assert result.objects[3].attributes["fragility"] == "uncertain"
    assert result.objects[3].vlm_status == "completed"


def test_missing_mark_fails_only_that_object_and_is_retried():
    def skip_second(system, prompt):
        answer = answer_requested(system, prompt)
        if len(answer["objects"]) == 3:
            # 頼んでいない番号（99）は捨てられ、2 番は答えが無い
            answer["objects"][1] = {"mark_id": 99, **ATTRS[2]}
        return answer

    perception, llm = make(answer=skip_second)
    first = run(perception.analyze(jpeg()))
    assert [o.vlm_status for o in first.objects] == ["completed", "failed", "completed"]
    assert first.objects[1].error and first.objects[1].attribute_version == 0
    second = run(perception.analyze(jpeg()))  # 失敗した物体だけ、もう一度聞く
    assert second.vlm.analyzed == ["obj_002"] and len(llm.calls) == 2
    assert [o.vlm_status for o in second.objects] == ["completed"] * 3


def test_vlm_error_marks_failed_then_retry_succeeds():
    perception, llm = make(answer=LlmError("no auth"))
    failed = run(perception.analyze(jpeg()))
    assert failed.vlm.error == "no auth"
    assert {o.vlm_status for o in failed.objects} == {"failed"}
    assert perception.memory.stats()["pending"] == 0
    llm.answers["analyze_objects"] = answer_requested
    ok = run(perception.analyze(jpeg()))
    assert {o.vlm_status for o in ok.objects} == {"completed"} and ok.vlm.calls == 1


def test_object_ids_must_match_detections():
    perception, llm = make()
    with pytest.raises(PerceptionError):
        run(perception.analyze(jpeg(), object_ids=["a", "b"]))
    with pytest.raises(PerceptionError):
        run(perception.analyze(jpeg(), object_ids=["a", "a", "b"]))
    assert llm.calls == [] and perception.memory.objects == {}


def test_no_detections_does_not_call_vlm():
    perception, llm = make(classes=())
    result = run(perception.analyze(jpeg()))
    assert result.objects == [] and result.vlm.calls == 0 and llm.calls == []


# ---------------------------------------------------------------- 記憶のファイルと run の記録


def test_memory_survives_restart_without_new_vlm_call(tmp_path):
    perception, llm = make(tmp_path)
    run(perception.analyze(jpeg()))
    saved = json.loads((tmp_path / "memory.json").read_text(encoding="utf-8"))
    assert saved["objects"][0] == {**saved["objects"][0], "object_id": "obj_001", "category": "mug",
                                   "vlm_status": "completed", "attribute_version": 1}
    again, llm2 = make(tmp_path)  # サーバーを起動し直した
    result = run(again.analyze(jpeg()))
    assert llm2.calls == [] and result.objects[0].attributes["material"] == "ceramic"


def test_pending_in_file_is_retried_after_restart(tmp_path):
    path = tmp_path / "memory.json"
    path.write_text(json.dumps({"objects": [{"object_id": "obj_001", "vlm_status": "pending"}]}), encoding="utf-8")
    memory = ObjectMemory(path)
    assert memory.get("obj_001").vlm_status == "failed"
    assert memory.claim(["obj_001"]).new == ["obj_001"]


def test_run_artifacts_are_saved(tmp_path):
    perception, _ = make(tmp_path)
    first = run(perception.analyze(jpeg()))
    second = run(perception.analyze(jpeg()))
    directory = tmp_path / "runs" / first.run_id
    assert {p.name for p in directory.iterdir()} == {"input.jpg", "detections.json", "segmentation_overlay.jpg",
                                                     "som.jpg", "attributes.json", "result.json"}
    detections = json.loads((directory / "detections.json").read_text(encoding="utf-8"))
    assert detections["detections"][0]["class"] == "mug" and detections["detections"][0]["detection_id"] == 1
    assert not (tmp_path / "runs" / second.run_id / "attributes.json").exists()  # VLM を呼ばなかった run
    log = [json.loads(line) for line in (tmp_path / "runs" / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["vlm"]["calls"] for r in log] == [1, 0] and "total" in log[0]["timings_ms"]
    assert [r["run_id"] for r in perception.runs()] == [second.run_id, first.run_id]
    assert perception.run_file(first.run_id, "som.jpg") is not None
    assert perception.run_file(first.run_id, "../memory.json") is None
    assert perception.run_file("..", "input.jpg") is None


# ---------------------------------------------------------------- 画像


def test_som_images_are_drawn():
    image = som.load_image(jpeg())
    detections = [Detection.model_validate(detection(n)) for n in (1, 2)]
    marked = som.draw_marks(image, detections)
    assert marked.size == image.size and marked.tobytes() != image.tobytes()
    x, y = som.mark_position(detections[0])
    assert (round(x), round(y)) == (55, 120)  # マスクの重心
    no_mask = Detection.model_validate({**detection(1), "mask": []})
    assert som.mark_position(no_mask) == (55, 120)  # マスクが無ければ矩形の中心
    assert som.draw_overlay(image, detections).size == image.size
    small = som.load_image(som.to_jpeg(Image.new("RGB", (4000, 2000)), max_side=1568))
    assert small.size == (1568, 784)
    doubled = som.scale_detections(detections, 2.0)[0]
    assert doubled.bbox == [40, 120, 180, 360] and doubled.mask[0] == [40, 120]


def test_mark_is_on_big_objects_and_beside_small_ones():
    image = Image.new("RGB", (640, 480))
    big = Detection.model_validate({"detection_id": 1, "class": "cup", "bbox": [100, 100, 300, 300], "confidence": 0.9})
    small = Detection.model_validate({"detection_id": 2, "class": "cup", "bbox": [400, 200, 420, 220], "confidence": 0.9})
    corner = Detection.model_validate({"detection_id": 3, "class": "cup", "bbox": [0, 0, 15, 15], "confidence": 0.9})
    on = som._mark_box(big, 24, 24, image, [])
    assert on == (188, 188, 212, 212)  # 物体の真ん中
    beside = som._mark_box(small, 24, 24, image, [])
    assert beside[3] <= 200 and not som._overlaps(beside, (400, 200, 420, 220))  # 物体の上（隠さない）
    below = som._mark_box(small, 24, 24, image, [beside])
    assert below[1] >= 220  # 上がふさがっていれば下
    at_corner = som._mark_box(corner, 24, 24, image, [])
    assert at_corner[0] >= 0 and at_corner[1] >= 0 and not som._overlaps(at_corner, (0, 0, 15, 15))  # 画像からはみ出さない


# ---------------------------------------------------------------- REST


@pytest.fixture
def client(tmp_path):
    app = create_app()
    perception = app.state.services.perception
    perception.segmenter = FakeSegmenter()
    perception.memory = ObjectMemory()
    perception.runs_dir = tmp_path
    app.state.services.llm = FakeLlm({"analyze_objects": answer_requested})  # あとから差し替えても効く
    with TestClient(app) as client:
        yield client


def post(client, **params):
    return client.post("/perception/analyze", params=params, content=jpeg(), headers={"Content-Type": "image/jpeg"})


def test_rest_analyze_memory_and_runs(client):
    first = post(client).json()
    assert first["vlm"]["calls"] == 1
    assert first["objects"][0]["class"] == "mug" and first["objects"][0]["object_id"] == "obj_001"
    assert post(client).json()["vlm"]["calls"] == 0
    memory = client.get("/perception/memory").json()
    assert memory["stats"]["vlm_calls"] == 1 and len(memory["objects"]) == 3
    image = client.get(first["artifacts"]["som.jpg"])
    assert image.status_code == 200 and image.headers["content-type"] == "image/jpeg"
    assert len(client.get("/perception/runs").json()["runs"]) == 2
    assert client.get("/perception/runs/nope/som.jpg").status_code == 404

    assert client.delete("/perception/memory/obj_002").status_code == 200
    assert client.delete("/perception/memory/obj_002").status_code == 404
    again = post(client).json()
    assert again["vlm"]["analyzed"] == ["obj_002"]
    assert client.delete("/perception/memory").json()["stats"]["objects"] == 0


def test_rest_errors(client):
    assert client.post("/perception/analyze", content=jpeg()).status_code == 415
    assert post(client, object_ids="a,b").status_code == 422

    class Down:
        async def segment(self, data):
            raise SegmentError("Can't reach the detector")

    client.app.state.services.perception.segmenter = Down()
    response = post(client)
    assert response.status_code == 502 and "detector" in response.json()["detail"]


def test_ui_page(client):
    page = client.get("/perception/ui")
    assert page.status_code == 200 and "Perception Lab" in page.text


def test_rest_frame_endpoint(client, tmp_path):
    """POST /perception/frame（multipart）。中身の計算は test_frame.py。ここは受け口だけ。"""
    from test_frame import FRONT, SceneSegmenter, three, jpeg as frame_jpeg

    perception = client.app.state.services.perception
    segmenter = SceneSegmenter(three())
    segmenter.headset = FRONT
    perception.segmenter = segmenter
    perception.sequences_dir = tmp_path / "sequences"
    depth, _, _ = FRONT.depth.texture([b for b, _, _ in segmenter.objects.values()])
    files = {"rgb": ("rgb.jpg", frame_jpeg(), "image/jpeg"), "depth": ("depth.bin", depth, "application/octet-stream")}
    response = client.post("/perception/frame", params={"record": "demo"}, files=files, data={"meta": FRONT.meta(0)})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recorded"] == "demo/0001" and body["vlm"]["calls"] == 1
    assert {o["track"] for o in body["objects"]} == {"new"} and body["frame"]["located"] == 3
    only = client.post("/perception/frame", params={"record": "demo", "analyze": "false"}, files=files,
                       data={"meta": FRONT.meta(1)}).json()
    assert only == {"recorded": "demo/0002"}
    bad = client.post("/perception/frame", files=files, data={"meta": "{}"})
    assert bad.status_code == 422
    assert client.delete("/perception/memory").status_code == 200 and perception.tracker.objects == {}
