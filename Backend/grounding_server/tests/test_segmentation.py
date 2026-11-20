"""detector の POST /segment（YOLOE-seg）。モデルは代役（GPU も重みも使わない）。make detect-test で動かす。"""

import io
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from coground_server.detect_app import create_app
from coground_server.detection import Vocabulary
from coground_server.segmentation import Segmenter


class Tensor:
    def __init__(self, value):
        self.value = value

    def cpu(self):
        return self

    def tolist(self):
        return self.value


def result(boxes, scores, classes, polygons):
    return SimpleNamespace(
        boxes=SimpleNamespace(xyxy=Tensor(boxes), conf=Tensor(scores), cls=Tensor(classes)),
        masks=SimpleNamespace(xy=[Tensor(p) for p in polygons]) if polygons is not None else None)


@pytest.fixture
def segmenter():
    s = Segmenter.__new__(Segmenter)
    s.lock = threading.Lock()
    s.device, s.conf, s.imgsz, s.model_name = "cpu", 0.25, 640, "/models/yoloe-11s-seg.pt"
    s.vocabulary = Vocabulary(entries=[{"prompt": "cup", "label": "cup"}, {"prompt": "mug", "label": "mug"}])
    s.classes_set = []
    # 右の物体（mug）が先に出てくる。答えは左から並べ直す
    answer = result([[60, 10, 90, 40], [10, 20, 40.26, 50]], [0.9, 0.81234], [1, 0],
                    [[[60, 10], [90, 10], [90, 40]], [[10.04, 20], [40, 20], [40, 50]]])
    s.model = SimpleNamespace(predict=lambda *a, **k: [answer],
                              get_text_pe=lambda names: names,
                              set_classes=lambda names, pe: s.classes_set.append(names))
    return s


@pytest.fixture
def client(segmenter, monkeypatch):
    monkeypatch.setenv("COGROUND_DETECT_ENABLED", "0")
    monkeypatch.setenv("COGROUND_SEGMENT_ENABLED", "0")
    with TestClient(create_app()) as client:
        client.app.state.segmenter = segmenter
        yield client


def jpeg():
    buffer = io.BytesIO()
    Image.new("RGB", (100, 80)).save(buffer, "JPEG")
    return buffer.getvalue()


def post(client, data=None):
    return client.post("/segment", content=data or jpeg(), headers={"Content-Type": "image/jpeg"})


def test_contract_sorted_left_to_right(client):
    body = post(client).json()
    assert body["image"] == {"width": 100, "height": 80} and body["model"] == "yoloe-11s-seg.pt"
    assert body["detections"] == [
        {"detection_id": 1, "class": "cup", "bbox": [10, 20, 40.3, 50], "confidence": 0.8123,
         "mask": [[10.0, 20], [40, 20], [40, 50]]},
        {"detection_id": 2, "class": "mug", "bbox": [60, 10, 90, 40], "confidence": 0.9,
         "mask": [[60, 10], [90, 10], [90, 40]]}]


def test_no_objects_and_no_masks(client, segmenter):
    segmenter.model.predict = lambda *a, **k: [SimpleNamespace(boxes=None, masks=None)]
    assert post(client).json()["detections"] == []
    segmenter.model.predict = lambda *a, **k: [result([[1, 2, 3, 4]], [0.5], [0], None)]
    assert post(client).json()["detections"][0]["mask"] == []


def test_invalid_input(client, segmenter):
    assert client.post("/segment", content=jpeg()).status_code == 415
    assert post(client, b"bad").status_code == 400
    assert not segmenter.lock.locked()


def test_status_and_disabled(client):
    assert client.get("/segment/status").json() == {
        "enabled": True, "model": "yoloe-11s-seg.pt", "device": "cpu", "conf": 0.25, "imgsz": 640, "classes": ["cup", "mug"],
        "embedding": False}
    assert client.get("/health").json()["segmenter"] is True
    client.app.state.segmenter = None
    assert post(client).status_code == 503
    assert client.get("/segment/status").json() == {"enabled": False}


def test_vocabulary_update_reaches_segmenter(client, segmenter):
    """PUT /detect/vocabulary は、/detect と /segment の両方の語彙を替える。"""
    client.app.state.detector = SimpleNamespace(lock=threading.Lock(), update=lambda v: v.model_dump())
    entries = [{"prompt": "wine glass", "label": "glass"}]
    assert client.put("/detect/vocabulary", json={"entries": entries}).status_code == 200
    assert segmenter.classes_set == [["wine glass"]]
    segmenter.model.predict = lambda *a, **k: [result([[1, 2, 3, 4]], [0.5], [0], None)]
    assert post(client).json()["detections"][0]["class"] == "glass"


def test_embeddings(client, segmenter):
    """?embed=1 で、物体ごとの特徴量を返す。特徴量のモデルが無ければ null。"""
    assert "embedding" not in post(client).json()["detections"][0]
    response = client.post("/segment", params={"embed": 1}, content=jpeg(), headers={"Content-Type": "image/jpeg"})
    assert [d["embedding"] for d in response.json()["detections"]] == [None, None]
    seen = []
    segmenter.embedder = SimpleNamespace(embed=lambda image, boxes: seen.append(boxes) or [[1.0, 0.0], [0.0, 1.0]])
    response = client.post("/segment", params={"embed": 1}, content=jpeg(), headers={"Content-Type": "image/jpeg"})
    assert [d["embedding"] for d in response.json()["detections"]] == [[1.0, 0.0], [0.0, 1.0]]
    assert seen == [[[10, 20, 40.3, 50], [60, 10, 90, 40]]]  # 左から並べ直した後の矩形
