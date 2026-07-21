import numpy as np
from PIL import Image

from certvic.edit.displace import displace_object


def test_displace_output_exists(tmp_path):
    image = tmp_path / "img.png"
    out = tmp_path / "out.png"
    Image.new("RGB", (16, 16), (1, 2, 3)).save(image)
    mask = np.zeros((16, 16), dtype=bool)
    mask[2:4, 2:4] = True
    displace_object(str(image), mask, str(out), offset=(2, 0))
    assert out.exists()
