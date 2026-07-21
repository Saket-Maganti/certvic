"""Control edits that should not change the answer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def color_control_edit(image_path: str, mask: np.ndarray, out_path: str) -> str:
    image = Image.open(image_path).convert("RGB")
    arr = np.asarray(image).copy()
    outside = ~mask
    arr[outside] = np.clip(arr[outside].astype(int) + np.array([3, 0, 3]), 0, 255)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr.astype("uint8")).save(out_path)
    return out_path
