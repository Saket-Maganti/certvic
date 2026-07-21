from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.build_maximum_ceiling_release import audit_release, deterministic_rebuild


ROOT = Path(__file__).resolve().parents[1]


def test_maximum_release_is_deterministic_and_hash_complete(tmp_path) -> None:
    archive = tmp_path / "maximum.zip"
    rebuilt = deterministic_rebuild(archive, root=ROOT)
    assert rebuilt["passed"] is True
    audited = audit_release(archive)
    assert audited["passed"] is True
    with zipfile.ZipFile(archive) as handle:
        names = set(handle.namelist())
    assert "certvic/cvpr/doctor.py" in names
    assert "certvic/cvpr/chaos.py" in names
    assert "configs/data/source_license_registry.yaml" in names
    assert "RELEASE_FILE_MANIFEST.json" in names
    assert all("incoming_archives" not in name for name in names)
