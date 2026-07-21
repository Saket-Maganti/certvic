"""Mask utilities."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def load_binary_mask(path: str | Path) -> np.ndarray:
    arr = np.asarray(Image.open(path).convert("L"))
    return arr > 127


def validate_mask_dimensions(image_path: str | Path, mask: np.ndarray) -> None:
    image = Image.open(image_path)
    if image.size != (mask.shape[1], mask.shape[0]):
        raise ValueError(f"mask dimensions {mask.shape[::-1]} do not match image size {image.size}")


def bbox_from_mask(mask: np.ndarray) -> list[int]:
    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return [0, 0, 0, 0]
    return [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]


def mask_area_fraction(mask: np.ndarray) -> float:
    return float(mask.mean())


def dilate_mask(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    result = mask.astype(bool)
    for _ in range(iterations):
        padded = np.pad(result, 1, mode="edge")
        result = (
            padded[:-2, :-2]
            | padded[:-2, 1:-1]
            | padded[:-2, 2:]
            | padded[1:-1, :-2]
            | padded[1:-1, 1:-1]
            | padded[1:-1, 2:]
            | padded[2:, :-2]
            | padded[2:, 1:-1]
            | padded[2:, 2:]
        )
    return result


def erode_mask(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    result = mask.astype(bool)
    for _ in range(iterations):
        padded = np.pad(result, 1, mode="edge")
        result = (
            padded[:-2, :-2]
            & padded[:-2, 1:-1]
            & padded[:-2, 2:]
            & padded[1:-1, :-2]
            & padded[1:-1, 1:-1]
            & padded[1:-1, 2:]
            & padded[2:, :-2]
            & padded[2:, 1:-1]
            & padded[2:, 2:]
        )
    return result
