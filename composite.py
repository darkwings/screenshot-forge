from __future__ import annotations

import io
import math
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

    # For vertical extent, scan the full screen band [cmin:cmax].
    # Using only the center column misses the Dynamic Island hole, which is a
    # separate transparent cutout above the main screen area in Apple's frames.
    screen_band = alpha[:, cmin:cmax + 1]
    band_w = cmax - cmin + 1
    pixels_per_row = np.sum(screen_band < 50, axis=1)
    # Require at least 2% of screen width to be transparent — filters corner bleed.
    valid_rows = np.where(pixels_per_row >= max(1, band_w * 0.02))[0]
    if len(valid_rows) == 0:
        raise ValueError("No transparent region found in frame — cannot locate screen area")
    rmin = int(valid_rows[0])
    rmax = int(valid_rows[-1])

    return cmin, rmin, cmax - cmin + 1, rmax - rmin + 1


def crop_to_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Resize and crop image to fit exact target dimensions via center-crop.

    Scale image such that at least one dimension matches the target, then
    center-crop to return exact (target_w, target_h) image.

    Args:
        img: Input image
        target_w: Target width
        target_h: Target height

    Returns:
        Resized and cropped RGBA image with size (target_w, target_h)
    """
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = math.ceil(src_w * scale)
    new_h = math.ceil(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def composite_screenshot(frame_path: str, screenshot_bytes: bytes) -> bytes:
    """
    Composite a screenshot into an iOS device frame.

    Args:
        frame_path: Path to RGBA device frame PNG
        screenshot_bytes: Screenshot image bytes (PNG)

    Returns:
        PNG bytes with screenshot composited into frame, RGBA, transparent background
    """
    frame = Image.open(frame_path).convert("RGBA")
    x, y, w, h = find_screen_rect(frame)
    screenshot = Image.open(io.BytesIO(screenshot_bytes)).convert("RGBA")
    screenshot = crop_to_fit(screenshot, w, h)
    canvas = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    canvas.paste(screenshot, (x, y))
    result = Image.alpha_composite(canvas, frame)
    output = io.BytesIO()
    result.save(output, format="PNG")
    return output.getvalue()
