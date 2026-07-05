import io
import os
import pytest
from PIL import Image
from composite import list_devices, find_screen_rect, crop_to_fit, composite_screenshot

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "iOS Assets", "Bezel iPhone")
PORTRAIT_FRAME = os.path.join(
    ASSETS_DIR, "iPhone 17 Pro", "iPhone 17 Pro - Deep Blue - Portrait.png"
)
LANDSCAPE_FRAME = os.path.join(
    ASSETS_DIR, "iPhone 17 Pro", "iPhone 17 Pro - Deep Blue - Landscape.png"
)


def test_list_devices_returns_nonempty_dict():
    result = list_devices(ASSETS_DIR)
    assert isinstance(result, dict)
    assert len(result) > 0


def test_list_devices_structure():
    result = list_devices(ASSETS_DIR)
    for model, colors in result.items():
        assert isinstance(colors, dict), f"{model}: colors must be dict"
        for color, orientations in colors.items():
            assert isinstance(orientations, list), f"{model}/{color}: orientations must be list"
            for o in orientations:
                assert o in ("Portrait", "Landscape"), f"unexpected orientation: {o}"


@pytest.mark.skipif(not os.path.exists(PORTRAIT_FRAME), reason="real assets not installed")
def test_list_devices_known_model():
    result = list_devices(ASSETS_DIR)
    assert "iPhone 17 Pro" in result
    assert "Deep Blue" in result["iPhone 17 Pro"]
    assert "Portrait" in result["iPhone 17 Pro"]["Deep Blue"]


@pytest.mark.skipif(not os.path.exists(PORTRAIT_FRAME), reason="real assets not installed")
def test_find_screen_rect_portrait_within_bounds():
    frame = Image.open(PORTRAIT_FRAME).convert("RGBA")
    x, y, w, h = find_screen_rect(frame)
    assert x >= 0 and y >= 0
    assert w > 0 and h > 0
    assert x + w <= frame.width
    assert y + h <= frame.height


@pytest.mark.skipif(not os.path.exists(PORTRAIT_FRAME), reason="real assets not installed")
def test_find_screen_rect_portrait_is_tall():
    frame = Image.open(PORTRAIT_FRAME).convert("RGBA")
    _, _, w, h = find_screen_rect(frame)
    assert h > w, "portrait screen rect must be taller than wide"


@pytest.mark.skipif(not os.path.exists(LANDSCAPE_FRAME), reason="real assets not installed")
def test_find_screen_rect_landscape_is_wide():
    frame = Image.open(LANDSCAPE_FRAME).convert("RGBA")
    _, _, w, h = find_screen_rect(frame)
    assert w > h, "landscape screen rect must be wider than tall"


@pytest.mark.skipif(not os.path.exists(PORTRAIT_FRAME), reason="real assets not installed")
def test_find_screen_rect_screen_smaller_than_frame():
    frame = Image.open(PORTRAIT_FRAME).convert("RGBA")
    x, y, w, h = find_screen_rect(frame)
    assert w < frame.width
    assert h < frame.height


def _make_png(w: int = 400, h: int = 800, color=(100, 149, 237, 255)) -> bytes:
    img = Image.new("RGBA", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_crop_to_fit_returns_exact_size():
    img = Image.new("RGBA", (100, 200), (255, 0, 0, 255))
    result = crop_to_fit(img, 50, 80)
    assert result.size == (50, 80)


def test_crop_to_fit_upscale():
    img = Image.new("RGBA", (50, 100), (0, 255, 0, 255))
    result = crop_to_fit(img, 200, 400)
    assert result.size == (200, 400)


def test_crop_to_fit_landscape_to_portrait():
    img = Image.new("RGBA", (400, 200), (0, 0, 255, 255))
    result = crop_to_fit(img, 100, 300)
    assert result.size == (100, 300)


@pytest.mark.skipif(not os.path.exists(PORTRAIT_FRAME), reason="real assets not installed")
def test_composite_screenshot_returns_png_rgba():
    result = composite_screenshot(PORTRAIT_FRAME, _make_png())
    out = Image.open(io.BytesIO(result))
    assert out.format == "PNG"
    assert out.mode == "RGBA"


@pytest.mark.skipif(not os.path.exists(PORTRAIT_FRAME), reason="real assets not installed")
def test_composite_screenshot_has_transparent_background():
    result = composite_screenshot(PORTRAIT_FRAME, _make_png())
    out = Image.open(io.BytesIO(result)).convert("RGBA")
    # top-left corner is outside any device bezel — must be transparent
    assert out.getpixel((0, 0))[3] == 0, "top-left pixel must be transparent"


@pytest.mark.skipif(not os.path.exists(PORTRAIT_FRAME), reason="real assets not installed")
def test_composite_screenshot_output_matches_frame_size():
    frame = Image.open(PORTRAIT_FRAME)
    result = composite_screenshot(PORTRAIT_FRAME, _make_png())
    out = Image.open(io.BytesIO(result))
    assert out.size == frame.size


@pytest.mark.skipif(not os.path.exists(LANDSCAPE_FRAME), reason="real assets not installed")
def test_composite_screenshot_landscape_frame():
    # Verify composite works with landscape frames
    result = composite_screenshot(LANDSCAPE_FRAME, _make_png())
    out = Image.open(io.BytesIO(result))
    frame = Image.open(LANDSCAPE_FRAME)
    assert out.size == frame.size
    assert out.mode == "RGBA"
