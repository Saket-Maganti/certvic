"""Tests for the V7 pilot paper scaffold (guard-clean, pilot-only)."""

from __future__ import annotations

from pathlib import Path

from certvic.validation.claim_language_guard import scan_claim_language
from certvic.validation.paper_numbers_guard import verify_paper

REPO = Path(__file__).resolve().parents[1]
SECTIONS = ["paper/sections/pilot_results_main200.tex",
            "paper/sections/limitations_current_pilot.tex"]
MANIFEST = REPO / "paper/pilot_results_provenance.json"


def test_paper_numbers_guard_passes_with_manifest():
    result = verify_paper(results_files=SECTIONS, repo_root=str(REPO), manifest_path=str(MANIFEST))
    assert result["passed"] is True, result


def test_no_hand_typed_numbers_in_prose():
    # Every result number must arrive via \input; prose carries none (only allowed constants).
    result = verify_paper(results_files=SECTIONS, repo_root=str(REPO), manifest_path=str(MANIFEST))
    for f in result["files"]:
        assert f["extracted"]["untraced_numbers"] == []


def test_claim_language_guard_clean_on_sections():
    roots = [str(REPO / s) for s in SECTIONS]
    assert scan_claim_language(roots)["passed"] is True


def test_sections_use_pilot_only_language():
    res = (REPO / "paper/sections/pilot_results_main200.tex").read_text().lower()
    lim = (REPO / "paper/sections/limitations_current_pilot.tex").read_text().lower()
    assert "pilot only" in res or "pilot" in res
    assert "under the pilot protocol" in res
    # explicit "what this result does not show" subsection present
    assert "does not show" in lim
    # no overclaiming language
    for banned in ("state of the art", "paper-grade evidence", "final result", "proves vlms fail"):
        assert banned not in res and banned not in lim


def test_input_tables_exist():
    for name in ("main200_multimodel_results.tex", "main200_control_results.tex"):
        assert (REPO / "data/results/main_real_200/tables" / name).exists()
