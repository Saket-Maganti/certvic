"""Deterministic CPU displace edit."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from certvic.edit.inpaint import SimpleFillInpainter


def displace_object(image_path: str, mask: np.ndarray, out_path: str, offset: tuple[int, int] = (16, 0)) -> str:
    image = Image.open(image_path).convert("RGB")
    arr = np.asarray(image).copy()
    object_pixels = arr.copy()
    inpainter = SimpleFillInpainter()
    edited = np.asarray(inpainter.inpaint(image, mask)).copy()
    ys, xs = np.where(mask)
    dy, dx = offset[1], offset[0]
    for y, x in zip(ys, xs):
        ny, nx = y + dy, x + dx
        if 0 <= ny < edited.shape[0] and 0 <= nx < edited.shape[1]:
            edited[ny, nx] = object_pixels[y, x]
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(edited).save(out_path)
    return out_path
