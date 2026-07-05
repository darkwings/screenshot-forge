import os
import pytest
from composite import list_devices

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "iOS Assets", "Bezel iPhone")


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
