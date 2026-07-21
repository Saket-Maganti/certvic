"""Tests for the V3 related-work / citation audit (prompt 13)."""

from __future__ import annotations

import sys

import yaml

from certvic.paper import related_work_audit

MATRIX_PATH = "paper/related_work_matrix.yaml"


def test_matrix_has_all_eight_categories():
    matrix = related_work_audit.load_matrix(MATRIX_PATH)
    cats = matrix["categories"]
    assert len(cats) == 8
    # No fabricated citations: every category's representative_works is empty.
    assert all(not c.get("representative_works") for c in cats.values())


def test_audit_on_real_related_section():
    result = related_work_audit.audit_related_work(MATRIX_PATH, "paper/sections/02_related.tex")
    assert result["n_categories"] == 8
    assert result["fabricated_citations"] is False
    # All categories still need citations (scaffold state).
    assert len(result["categories_needing_citations"]) == 8
    # No real \cite keys yet -> no fabrication risk.
    assert result["fabrication_risk"] is False


def test_coverage_detection(tmp_path):
    matrix = tmp_path / "m.yaml"
    matrix.write_text(yaml.safe_dump({"categories": {
        "anytime_valid_inference": {"title": "AV", "keywords": ["confidence sequence", "betting"], "representative_works": [], "differentiator": "x"},
        "budgeted_evaluation": {"title": "Budget", "keywords": ["sample efficiency"], "representative_works": [], "differentiator": "y"},
    }}), encoding="utf-8")
    paper = tmp_path / "rel.tex"
    paper.write_text("We use a confidence sequence for certification.", encoding="utf-8")
    result = related_work_audit.audit_related_work(str(matrix), str(paper))
    covered = {r["category"]: r["covered_in_paper"] for r in result["categories"]}
    assert covered["anytime_valid_inference"] is True
    assert covered["budgeted_evaluation"] is False
    assert "budgeted_evaluation" in result["missing_categories"]


def test_unverified_cite_keys_flagged(tmp_path):
    matrix = tmp_path / "m.yaml"
    matrix.write_text(yaml.safe_dump({"categories": {}}), encoding="utf-8")
    paper = tmp_path / "rel.tex"
    paper.write_text("As shown by \\cite{smith2024fake}, models fail.", encoding="utf-8")
    result = related_work_audit.audit_related_work(str(matrix), str(paper))
    assert "smith2024fake" in result["unverified_cite_keys"]
    assert result["fabrication_risk"] is True
    # With a verified bib, the same key is no longer flagged.
    result2 = related_work_audit.audit_related_work(str(matrix), str(paper), bib_keys={"smith2024fake"})
    assert result2["unverified_cite_keys"] == []
    assert result2["fabrication_risk"] is False


def test_novelty_claims_flagged(tmp_path):
    matrix = tmp_path / "m.yaml"
    matrix.write_text(yaml.safe_dump({"categories": {}}), encoding="utf-8")
    paper = tmp_path / "rel.tex"
    paper.write_text("We are the first to certify the gap. This is a novel benchmark.", encoding="utf-8")
    result = related_work_audit.audit_related_work(str(matrix), str(paper))
    phrases = {f["phrase"] for f in result["novelty_claim_flags"]}
    assert "we are the first" in phrases
    assert "novel" in phrases


def test_report_renders():
    result = related_work_audit.audit_related_work(MATRIX_PATH, "paper/sections/02_related.tex")
    md = related_work_audit.render_report(result)
    assert "Related Work Audit" in md
    assert "Citation integrity" in md


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
