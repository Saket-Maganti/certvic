"""Deterministic occlusion edit."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from certvic.edit.masks import bbox_from_mask


def occlude_region(image_path: str, mask: np.ndarray, out_path: str, color=(110, 110, 110)) -> str:
    image = Image.open(image_path).convert("RGB")
    arr = np.asarray(image).copy()
    x1, y1, x2, y2 = bbox_from_mask(mask)
    arr[y1:y2, x1:x2] = color
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr).save(out_path)
    return out_path
