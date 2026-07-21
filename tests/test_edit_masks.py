import numpy as np

from certvic.edit.masks import bbox_from_mask, mask_area_fraction


def test_mask_bbox_and_area():
    mask = np.zeros((10, 10), dtype=bool)
    mask[2:4, 3:8] = True
    assert bbox_from_mask(mask) == [3, 2, 8, 4]
    assert mask_area_fraction(mask) == 0.1
