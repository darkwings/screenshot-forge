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


def _interior_mask(frame_img: Image.Image) -> np.ndarray:
    """
    Find the true screen shape (transparent area enclosed by the device body)
    in an iOS device frame, as a boolean pixel mask.

    The screen area may include a Dynamic Island hole that is disconnected
    from the main screen rectangle by a thin opaque strip, and the screen
    itself has rounded corners — so it is not a plain rectangle. Frame PNGs
    can also have transparent padding around the whole device (drop-shadow
    margin), which must NOT be mistaken for screen area.

    Distinguish the two by connectivity to the image border: padding always
    touches the canvas edge, while the screen/Dynamic Island holes are fully
    enclosed by the opaque device body. Flood-fill transparency from the
    border (via iterative dilation) to find the padding; whatever transparent
    pixels remain make up the true screen shape.
    """
    arr = np.array(frame_img)
    alpha = arr[:, :, 3]

    transparent = alpha < 50
    outside = np.zeros_like(transparent)
    outside[0, :] = transparent[0, :]
    outside[-1, :] = transparent[-1, :]
    outside[:, 0] = transparent[:, 0]
    outside[:, -1] = transparent[:, -1]
    while True:
        grown = outside.copy()
        grown[1:, :] |= outside[:-1, :]
        grown[:-1, :] |= outside[1:, :]
        grown[:, 1:] |= outside[:, :-1]
        grown[:, :-1] |= outside[:, 1:]
        grown &= transparent
        if np.array_equal(grown, outside):
            break
        outside = grown

    return transparent & ~outside


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

    interior = _interior_mask(frame_img)
    rows = np.where(interior.any(axis=1))[0]
    cols = np.where(interior.any(axis=0))[0]
    if len(rows) == 0:
        raise ValueError("No transparent region found in frame — cannot locate screen area")
    rmin, rmax = int(rows[0]), int(rows[-1])
    cmin, cmax = int(cols[0]), int(cols[-1])

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

    # The screen isn't a plain rectangle (rounded corners, Dynamic Island
    # cutout), so clip the pasted screenshot to the true screen shape —
    # otherwise it bleeds into the transparent padding around the device
    # near the rounded corners.
    mask = _interior_mask(frame)
    canvas_arr = np.array(canvas)
    canvas_arr[~mask, 3] = 0
    canvas = Image.fromarray(canvas_arr, "RGBA")

    result = Image.alpha_composite(canvas, frame)
    output = io.BytesIO()
    result.save(output, format="PNG")
    return output.getvalue()
