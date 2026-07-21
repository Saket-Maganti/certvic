from __future__ import annotations

import zipfile

import pytest

from certvic.cvpr.chaos import ChaosValidationError, run_chaos_suite, validate_zip


def test_chaos_suite_covers_fault_matrix_without_corruption() -> None:
    report = run_chaos_suite()
    assert report["status"] == "PASS"
    assert report["scenario_count"] >= 20
    assert report["canonical_corruption"] is False
    assert all(row["observed_code"] == row["expected_code"] for row in report["scenarios"])


def test_zip_validator_refuses_traversal_and_accepts_safe_archive(tmp_path) -> None:
    unsafe = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(unsafe, "w") as handle:
        handle.writestr("../escape", b"no")
    with pytest.raises(ChaosValidationError, match="unsafe archive member") as caught:
        validate_zip(unsafe)
    assert caught.value.code == "CHAOS_PATH_TRAVERSAL"

    safe = tmp_path / "safe.zip"
    with zipfile.ZipFile(safe, "w") as handle:
        handle.writestr("folder/file.txt", b"yes")
    assert validate_zip(safe)["passed"] is True

