import numpy as np

from certvic.edit.quality_gates import pass_quality_gates


def test_quality_gate_catches_global_change():
    orig = np.zeros((10, 10, 3), dtype="uint8")
    edited = np.ones((10, 10, 3), dtype="uint8") * 255
    mask = np.zeros((10, 10), dtype=bool)
    mask[2:4, 2:4] = True
    result = pass_quality_gates(orig, edited, mask, {"max_outside_mask_change_fraction": 0.1})
    assert not result["pass"]
