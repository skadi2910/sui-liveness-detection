from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .types import FaceBoundingBox, FrameInput


def decode_frame_image(frame: FrameInput) -> np.ndarray | None:
    if not frame.image_base64:
        return None

    try:
        image_bytes = base64.b64decode(frame.image_base64)
    except Exception:
        return None

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    if image_array.size == 0:
        return None
    return cv2.imdecode(image_array, cv2.IMREAD_COLOR)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def parse_silent_face_model_name(model_name: str) -> tuple[int, int, str, float | None]:
    info = model_name.split("_")[0:-1]
    h_input, w_input = info[-1].split("x")
    model_type = Path(model_name).stem.split("_")[-1]
    if info[0] == "org":
        scale = None
    else:
        scale = float(info[0])
    return int(h_input), int(w_input), model_type, scale


def crop_image(
    image: np.ndarray,
    bbox: FaceBoundingBox,
    *,
    scale: float | None,
    out_w: int,
    out_h: int,
    crop: bool = True,
) -> np.ndarray:
    if not crop or scale is None:
        return cv2.resize(image, (out_w, out_h))

    src_h, src_w = image.shape[:2]
    x = float(bbox.x)
    y = float(bbox.y)
    box_w = max(1.0, float(bbox.width))
    box_h = max(1.0, float(bbox.height))

    scale = min((src_h - 1) / box_h, min((src_w - 1) / box_w, scale))
    new_width = box_w * scale
    new_height = box_h * scale

    center_x = box_w / 2 + x
    center_y = box_h / 2 + y

    left = center_x - new_width / 2
    top = center_y - new_height / 2
    right = center_x + new_width / 2
    bottom = center_y + new_height / 2

    if left < 0:
        right -= left
        left = 0
    if top < 0:
        bottom -= top
        top = 0
    if right > src_w - 1:
        left -= right - src_w + 1
        right = src_w - 1
    if bottom > src_h - 1:
        top -= bottom - src_h + 1
        bottom = src_h - 1

    left_i = max(0, int(left))
    top_i = max(0, int(top))
    right_i = max(left_i + 1, int(right))
    bottom_i = max(top_i + 1, int(bottom))

    patch = image[top_i : bottom_i + 1, left_i : right_i + 1]
    return cv2.resize(patch, (out_w, out_h))


def softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values, axis=-1, keepdims=True)
    exps = np.exp(shifted)
    return exps / np.sum(exps, axis=-1, keepdims=True)


def bool_from_metadata(metadata: dict[str, Any], key: str) -> bool | None:
    if key not in metadata:
        return None
    return bool(metadata[key])
