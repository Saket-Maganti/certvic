from __future__ import annotations

from pathlib import Path

from certvic.validation.claim_language_guard import main, scan_claim_language


def test_claim_language_cli_fails_when_forbidden_claim_is_found(tmp_path: Path) -> None:
    source = tmp_path / "paper.md"
    report = tmp_path / "guard.md"
    source.write_text("This proves causal understanding.", encoding="utf-8")

    assert main(["--root", str(source), "--out", str(report)]) == 1
    assert scan_claim_language([str(source)])["passed"] is False
    assert "Passed: False" in report.read_text(encoding="utf-8")


def test_claim_language_cli_passes_clean_text(tmp_path: Path) -> None:
    source = tmp_path / "paper.md"
    report = tmp_path / "guard.md"
    source.write_text("This pilot result is model- and dataset-specific.", encoding="utf-8")

    assert main(["--root", str(source), "--out", str(report)]) == 0
    assert "Passed: True" in report.read_text(encoding="utf-8")
