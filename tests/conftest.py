from __future__ import annotations

import pytest

from certvic.data.smoke_fixtures import generate_smoke_tasks


@pytest.fixture
def smoke_tasks(tmp_path):
    return generate_smoke_tasks(tmp_path / "smoke", n_items=12)
