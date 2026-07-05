import io
import os
import pytest
from PIL import Image
from app import app as flask_app

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "iOS Assets", "Bezel iPhone")


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def _make_png(w: int = 400, h: int = 800) -> bytes:
    img = Image.new("RGB", (w, h), (100, 149, 237))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_devices_returns_200_json(client):
    resp = client.get("/api/devices")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert "iPhone 17 Pro" in data


def test_composite_missing_screenshot_returns_400(client):
    resp = client.post("/api/composite", data={
        "model": "iPhone 17 Pro",
        "color": "Deep Blue",
        "orientation": "Portrait",
    })
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_composite_missing_fields_returns_400(client):
    resp = client.post(
        "/api/composite",
        data={"screenshot": (io.BytesIO(_make_png()), "ss.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_composite_invalid_frame_returns_400(client):
    resp = client.post(
        "/api/composite",
        data={
            "screenshot": (io.BytesIO(_make_png()), "ss.png"),
            "model": "iPhone 99 Fake",
            "color": "Invisible",
            "orientation": "Portrait",
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_composite_returns_png(client):
    resp = client.post(
        "/api/composite",
        data={
            "screenshot": (io.BytesIO(_make_png()), "ss.png"),
            "model": "iPhone 17 Pro",
            "color": "Deep Blue",
            "orientation": "Portrait",
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    assert resp.content_type == "image/png"
    out = Image.open(io.BytesIO(resp.data))
    assert out.mode == "RGBA"
