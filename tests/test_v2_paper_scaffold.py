"""Tests for the V2 paper scaffold upgrade."""

from __future__ import annotations

from pathlib import Path

from certvic.validation.claims import FORBIDDEN_CLAIM_PHRASES

REPO_ROOT = Path(__file__).resolve().parents[1]
SECTIONS = REPO_ROOT / "paper" / "sections"
SECTION_FILES = [
    "01_intro.tex", "02_related.tex", "03_method.tex", "04_experiments.tex",
    "05_results.tex", "06_limitations.tex", "07_conclusion.tex",
]


def _all_text() -> str:
    parts = [(SECTIONS / name).read_text(encoding="utf-8") for name in SECTION_FILES]
    parts.append((REPO_ROOT / "paper" / "supp" / "supplement.tex").read_text(encoding="utf-8"))
    return "\n".join(parts).lower()


def test_sections_exist():
    for name in SECTION_FILES:
        assert (SECTIONS / name).exists(), name


def test_results_still_placeholder_and_no_fabricated_numbers():
    text = _all_text()
    assert "[result required]" in text
    # No numeric-looking result near a metric word in the results section.
    results = (SECTIONS / "05_results.tex").read_text(encoding="utf-8")
    import re

    assert re.search(r"(accuracy|consistency|gap)[^\n]{0,30}\b0\.\d{2,}\b", results.lower()) is None


def test_no_forbidden_claim_phrases():
    text = _all_text()
    for phrase in FORBIDDEN_CLAIM_PHRASES:
        assert phrase not in text, phrase
    for banned in ["frontier models fail", "all vlms fail", "safe for autonomous driving", "proves causal"]:
        assert banned not in text


def test_method_defines_gap_and_cs():
    method = (SECTIONS / "03_method.tex").read_text(encoding="utf-8").lower()
    assert "intervention-consistency gap" in method
    assert "confidence sequence" in method
    assert "claim gate" in method


def test_intro_covers_contributions():
    intro = (SECTIONS / "01_intro.tex").read_text(encoding="utf-8").lower()
    assert "contribution" in intro
    assert "zero-cost" in intro


def test_reviewer_and_checklist_docs_exist():
    assert (REPO_ROOT / "docs" / "PAPER_CLAIM_CHECKLIST.md").exists()
    attacks = REPO_ROOT / "docs" / "REVIEWER_ATTACKS_AND_DEFENSES.md"
    assert attacks.exists()
    text = attacks.read_text(encoding="utf-8").lower()
    for topic in ["fake", "causal", "small", "licens", "open", "optional stopping", "gameable"]:
        assert topic in text
