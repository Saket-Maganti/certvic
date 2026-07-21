"""Inpainting interfaces."""

from __future__ import annotations

import numpy as np
from PIL import Image

from certvic.exceptions import MissingOptionalDependencyError


class SimpleFillInpainter:
    def inpaint(self, image: Image.Image, mask: np.ndarray, fill=(238, 238, 232)) -> Image.Image:
        arr = np.asarray(image.convert("RGB")).copy()
        arr[mask] = fill
        return Image.fromarray(arr)


class DiffusersInpainter:
    def __init__(self, model_id: str, **kwargs):
        try:
            import diffusers  # noqa: F401
            import torch  # noqa: F401
        except Exception as exc:
            raise MissingOptionalDependencyError(
                "DiffusersInpainter requires optional vision dependencies and free/local weights."
            ) from exc
        raise MissingOptionalDependencyError("DiffusersInpainter is a V1 hook; configure before real use.")
