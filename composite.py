from __future__ import annotations

import io
import os

import numpy as np
from PIL import Image


def list_devices(assets_dir: str) -> dict:
    result: dict[str, dict[str, list[str]]] = {}
    if not os.path.isdir(assets_dir):
        return result
    for model in sorted(os.listdir(assets_dir)):
        model_path = os.path.join(assets_dir, model)
        if not os.path.isdir(model_path) or model.startswith("."):
            continue
        result[model] = {}
        for filename in sorted(os.listdir(model_path)):
            if not filename.endswith(".png") or filename.startswith("."):
                continue
            stem = filename[:-4]          # strip .png
            parts = stem.split(" - ")     # e.g. ["iPhone 17 Pro", "Deep Blue", "Portrait"]
            if len(parts) < 3:
                continue
            color = parts[-2]
            orientation = parts[-1]
            result[model].setdefault(color, [])
            if orientation not in result[model][color]:
                result[model][color].append(orientation)
    return result


def find_screen_rect(frame_img: Image.Image) -> tuple[int, int, int, int]:
    raise NotImplementedError


def crop_to_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    raise NotImplementedError


def composite_screenshot(frame_path: str, screenshot_bytes: bytes) -> bytes:
    raise NotImplementedError
