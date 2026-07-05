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
    """
    Find the screen region (transparent area) in an iOS device frame.

    Args:
        frame_img: RGBA image of the device frame

    Returns:
        (x, y, width, height) tuple in pixels, where:
        - x, y: top-left corner of screen region
        - width, height: dimensions of screen region

    Raises:
        ValueError: if no transparent region found
    """
    arr = np.array(frame_img)
    alpha = arr[:, :, 3]
    img_h, img_w = alpha.shape
    cx, cy = img_w // 2, img_h // 2

    if alpha[cy, cx] >= 50:
        raise ValueError("No transparent region found in frame — cannot locate screen area")

    # Find the contiguous transparent (screen) region by scanning inward from center.
    # This avoids including transparent corner pixels that lie outside the device bezel.
    center_row = alpha[cy, :]
    left_opaque = np.where(center_row[:cx] >= 50)[0]
    cmin = int(left_opaque[-1]) + 1 if len(left_opaque) > 0 else 0
    right_opaque = np.where(center_row[cx + 1:] >= 50)[0]
    cmax = cx + int(right_opaque[0]) if len(right_opaque) > 0 else img_w - 1

    center_col = alpha[:, cx]
    above_opaque = np.where(center_col[:cy] >= 50)[0]
    rmin = int(above_opaque[-1]) + 1 if len(above_opaque) > 0 else 0
    below_opaque = np.where(center_col[cy + 1:] >= 50)[0]
    rmax = cy + int(below_opaque[0]) if len(below_opaque) > 0 else img_h - 1

    return cmin, rmin, cmax - cmin + 1, rmax - rmin + 1


def crop_to_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    raise NotImplementedError


def composite_screenshot(frame_path: str, screenshot_bytes: bytes) -> bytes:
    raise NotImplementedError
