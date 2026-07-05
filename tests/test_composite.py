import os
import pytest
from PIL import Image
from composite import list_devices, find_screen_rect

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


def test_list_devices_known_model():
    result = list_devices(ASSETS_DIR)
    assert "iPhone 17 Pro" in result
    assert "Deep Blue" in result["iPhone 17 Pro"]
    assert "Portrait" in result["iPhone 17 Pro"]["Deep Blue"]


def test_find_screen_rect_portrait_within_bounds():
    frame = Image.open(PORTRAIT_FRAME).convert("RGBA")
    x, y, w, h = find_screen_rect(frame)
    assert x >= 0 and y >= 0
    assert w > 0 and h > 0
    assert x + w <= frame.width
    assert y + h <= frame.height


def test_find_screen_rect_portrait_is_tall():
    frame = Image.open(PORTRAIT_FRAME).convert("RGBA")
    _, _, w, h = find_screen_rect(frame)
    assert h > w, "portrait screen rect must be taller than wide"


def test_find_screen_rect_landscape_is_wide():
    frame = Image.open(LANDSCAPE_FRAME).convert("RGBA")
    _, _, w, h = find_screen_rect(frame)
    assert w > h, "landscape screen rect must be wider than tall"


def test_find_screen_rect_screen_smaller_than_frame():
    frame = Image.open(PORTRAIT_FRAME).convert("RGBA")
    x, y, w, h = find_screen_rect(frame)
    assert w <= frame.width
    assert h <= frame.height
