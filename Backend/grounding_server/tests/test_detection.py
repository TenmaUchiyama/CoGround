import io
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from coground_server.detection import Detector, Vocabulary
from coground_server.detect_app import create_app


class Tensor:
    def __init__(self, value):
        self.value = value

    def cpu(self):
        return self

    def tolist(self):
        return self.value


@pytest.fixture
def detector():
    d = Detector.__new__(Detector)
    d.lock = threading.Lock()
    d.device, d.conf, d.imgsz, d.debug_dir = "cpu", 0.25, 640, None
    d.vocabulary = Vocabulary(entries=[{"prompt": "plastic bottle", "label": "plastic_bottle"}])
    boxes = SimpleNamespace(xyxy=Tensor([[10, 20, 80, 90]]), conf=Tensor([0.82]), cls=Tensor([0]))
    d.model = SimpleNamespace(predict=lambda *a, **k: [SimpleNamespace(boxes=boxes)],
                              set_classes=lambda names: None)
    return d


@pytest.fixture
def client(detector, monkeypatch):
    monkeypatch.setenv("COGROUND_DETECT_ENABLED", "0")
    with TestClient(create_app()) as client:
        client.app.state.detector = detector
        yield client


def jpeg():
    buffer = io.BytesIO()
    Image.new("RGB", (100, 100)).save(buffer, "JPEG")
    return buffer.getvalue()


def test_contract(client):
    response = client.post("/detect", content=jpeg(), headers={"Content-Type": "image/jpeg"})
    assert response.status_code == 200
    assert response.json() == {"predictions": [
        {"label": "plastic_bottle", "score": 0.82, "box": [10, 20, 80, 90]}]}


def test_invalid_and_busy(client, detector):
    assert client.post("/detect", content=jpeg()).status_code == 415
    assert client.post("/detect", content=b"bad", headers={"Content-Type": "image/jpeg"}).status_code == 400
    assert not detector.lock.locked()
    with detector.lock:
        assert client.post("/detect", content=jpeg(), headers={"Content-Type": "image/jpeg"}).status_code == 429
        assert client.put("/detect/vocabulary", json=detector.vocabulary.model_dump()).status_code == 429


def test_limit(client):
    assert client.post("/detect", content=b"x" * (10 * 1024 * 1024 + 1),
                       headers={"Content-Type": "image/jpeg"}).status_code == 413


def test_vocabulary(client):
    entries = [{"prompt": "mug", "label": "mug"}]
    assert client.put("/detect/vocabulary", json={"entries": entries}).status_code == 200
    assert client.get("/detect/vocabulary").json() == {"entries": entries}
    assert client.post("/detect", content=jpeg(), headers={"Content-Type": "image/jpeg"}).json()["predictions"][0]["label"] == "mug"
    assert client.put("/detect/vocabulary", json={"entries": []}).status_code == 422
    assert client.put("/detect/vocabulary", json={"entries": entries * 2}).status_code == 422


def test_debug_and_empty(client, detector, tmp_path):
    detector.debug_dir = str(tmp_path)
    detector.model.predict = lambda *a, **k: [SimpleNamespace(boxes=None)]
    assert client.post("/detect", content=jpeg(), headers={"Content-Type": "image/jpeg"}).json() == {"predictions": []}
    assert len(list(tmp_path.glob("*.jpg"))) == 2
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_disabled(monkeypatch):
    monkeypatch.setenv("COGROUND_DETECT_ENABLED", "0")
    with TestClient(create_app()) as client:
        assert client.post("/detect", content=jpeg(), headers={"Content-Type": "image/jpeg"}).status_code == 503
        assert client.get("/health").status_code == 200


def test_model_failure_releases_lock(client, detector):
    def fail(*a, **k):
        raise RuntimeError("model failure")
    detector.model.predict = fail
    with pytest.raises(RuntimeError):
        client.post("/detect", content=jpeg(), headers={"Content-Type": "image/jpeg"})
    assert not detector.lock.locked()


def test_browser_ui_and_status(client):
    page = client.get('/detect/ui')
    assert page.status_code == 200
    assert 'Detection Lab' in page.text
    assert client.get('/detect/assets/detect.js').status_code == 200
    assert client.get('/detect/assets/detect.css').status_code == 200
    assert client.get('/detect/status').json() == {
        'enabled': True, 'device': 'cpu', 'conf': 0.25, 'imgsz': 640, 'mode': 'vocab'}


def test_browser_ui_when_disabled(monkeypatch):
    monkeypatch.setenv('COGROUND_DETECT_ENABLED', '0')
    with TestClient(create_app()) as client:
        assert client.get('/detect/ui').status_code == 200
        assert client.get('/detect/status').json() == {'enabled': False}


def test_live_reports_last_frame(client):
    assert client.get("/detect/live").json()["clients"] == []
    assert client.get("/detect/live.jpg").status_code == 404
    data = jpeg()
    client.post("/detect", content=data, headers={"Content-Type": "image/jpeg"})
    client.post("/detect", content=b"bad", headers={"Content-Type": "image/jpeg"})
    live = client.get("/detect/live").json()
    [c] = live["clients"]
    assert (c["requests"], c["ok"], c["errors"], c["last_status"]) == (2, 1, 1, 400)
    assert live["last"]["size"] == [100, 100]
    assert live["last"]["predictions"][0]["label"] == "plastic_bottle"
    image = client.get("/detect/live.jpg")
    assert image.headers["content-type"] == "image/jpeg" and image.content == data


def test_open_mode(client, detector):
    """open: 内蔵クラスの名前をラベルにし、画像の大部分を覆う箱（机など）は捨てる。モードは動いたまま切り替えられる。"""
    seen = {}

    def predict(*a, **k):
        seen.update(k)
        boxes = SimpleNamespace(xyxy=Tensor([[10, 20, 30, 40], [0, 0, 100, 90]]), conf=Tensor([0.8, 0.7]), cls=Tensor([0, 1]))
        return [SimpleNamespace(boxes=boxes, names={0: "laptop keyboard", 1: "office desk"})]

    detector.open_model = SimpleNamespace(predict=predict)
    detector.open_conf, detector.open_max_area = 0.25, 0.25
    assert client.put("/detect/mode", json={"mode": "open"}).json() == {"mode": "open"}
    body = client.post("/detect", content=jpeg(), headers={"Content-Type": "image/jpeg"}).json()
    assert body == {"predictions": [{"label": "laptop_keyboard", "score": 0.8, "box": [10, 20, 30, 40]}]}
    assert seen["agnostic_nms"] is True
    assert client.get("/detect/mode").json() == {"mode": "open"}
    assert client.put("/detect/mode", json={"mode": "other"}).status_code == 422
    assert client.put("/detect/mode", json={"mode": "vocab"}).json() == {"mode": "vocab"}
    assert client.post("/detect", content=jpeg(), headers={"Content-Type": "image/jpeg"}).json()["predictions"][0]["label"] == "plastic_bottle"
