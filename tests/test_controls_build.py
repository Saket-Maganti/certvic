"""Invariants for the spurious-flip control builder (no ADE20K data needed).

The whole point of the specificity control is that the irrelevant edit (a) lands in an
object-free region and (b) leaves everything outside that patch untouched. These tests
check both on synthetic arrays so a regression can't silently corrupt the object.
"""

from __future__ import annotations

import random

import numpy as np
from PIL import Image

from scripts.build_spurious_flip_control import _perturb, _place_patch


def test_place_patch_avoids_object_region():
    # Object fills everything except a 60x60 top-left corner.
    mask = np.ones((120, 120), dtype=bool)
    mask[:60, :60] = False
    box, overlap = _place_patch(mask, random.Random(0), frac=0.08)
    assert box is not None
    assert overlap == 0.0  # patch must sit entirely in the object-free corner


def test_perturb_changes_only_the_patch():
    im = Image.fromarray(np.full((120, 120, 3), 128, dtype=np.uint8))
    box = (0, 0, 40, 40)
    edited = np.asarray(_perturb(im, box, random.Random(1))).astype(int)
    orig = np.asarray(im).astype(int)
    diff = np.abs(orig - edited)
    assert diff[0:40, 0:40].mean() > 1.0      # the patch actually changed
    outside = diff.copy()
    outside[0:40, 0:40] = 0
    assert outside.max() == 0                  # nothing outside the patch moved (object preserved)
