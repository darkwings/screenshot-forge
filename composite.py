from __future__ import annotations

import io
import os

import numpy as np
from PIL import Image


def list_devices(assets_dir: str) -> dict:
    raise NotImplementedError


def find_screen_rect(frame_img: Image.Image) -> tuple[int, int, int, int]:
    raise NotImplementedError


def crop_to_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    raise NotImplementedError


def composite_screenshot(frame_path: str, screenshot_bytes: bytes) -> bytes:
    raise NotImplementedError
