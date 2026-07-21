"""Tests for the V3 paper result injection and traceability (prompt 12)."""

from __future__ import annotations

import sys

from certvic.io import write_json
from certvic.paper import inject_results, paper_trace_report, result_manifest

RESULTS_TEX = """\\section{Results}

\\subsection{Main Consistency Results}
% Table: main_results_table.tex (n, gap, CS lower, certified)
[RESULT REQUIRED]

\\subsection{Gap Certification}
% Figure: cs_trajectory.png
[RESULT REQUIRED]
"""


def _paper_dir(tmp_path):
    paper = tmp_path / "paper"
    (paper / "sections").mkdir(parents=True)
    (paper / "tables").mkdir()
    (paper / "figures").mkdir()
    (paper / "sections" / "05_results.tex").write_text(RESULTS_TEX, encoding="utf-8")
    return paper


def _report_dir(tmp_path, *, evidence_status="UNKNOWN", provider_type="unknown"):
    rdir = tmp_path / "report"
    rdir.mkdir()
    (rdir / "main_results_table.tex").write_text("\\begin{tabular}{cc}a & b\\end{tabular}", encoding="utf-8")
    (rdir / "cs_trajectory.png").write_text("PNGDATA", encoding="utf-8")
    write_json(rdir / "report_summary.json", {"evidence_status": evidence_status, "provider_type": provider_type})
    return rdir


# --- result_manifest -------------------------------------------------------

def test_manifest_marks_non_evidence_ineligible(tmp_path):
    rdir = _report_dir(tmp_path)  # UNKNOWN/unknown -> ineligible
    out = tmp_path / "result_manifest.json"
    manifest = result_manifest.build_result_manifest(str(rdir), None, str(out))
    assert manifest["n_entries"] >= 2
    assert manifest["any_eligible"] is False
    assert all(e["sha256"] for e in manifest["entries"])  # hashes required


def test_manifest_eligible_for_real_open_local(tmp_path):
    rdir = _report_dir(tmp_path, evidence_status="REAL_EVIDENCE", provider_type="open_local")
    out = tmp_path / "rm.json"
    manifest = result_manifest.build_result_manifest(str(rdir), None, str(out))
    assert manifest["any_eligible"] is True
    table = next(e for e in manifest["entries"] if e["basename"] == "main_results_table.tex")
    assert table["eligible"] is True


# --- inject_results --------------------------------------------------------

def test_dry_run_does_not_write(tmp_path):
    paper = _paper_dir(tmp_path)
    rdir = _report_dir(tmp_path, evidence_status="REAL_EVIDENCE", provider_type="open_local")
    mani = tmp_path / "rm.json"
    result_manifest.build_result_manifest(str(rdir), None, str(mani))
    before = (paper / "sections" / "05_results.tex").read_text(encoding="utf-8")
    result = inject_results.inject_results(str(mani), str(paper))  # dry-run default
    assert result["dry_run"] is True
    assert result["n_injected"] >= 1
    # File unchanged on dry-run.
    assert (paper / "sections" / "05_results.tex").read_text(encoding="utf-8") == before


def test_ineligible_artifacts_preserve_placeholder(tmp_path):
    paper = _paper_dir(tmp_path)
    rdir = _report_dir(tmp_path)  # ineligible
    mani = tmp_path / "rm.json"
    result_manifest.build_result_manifest(str(rdir), None, str(mani))
    result = inject_results.inject_results(str(mani), str(paper), allow_write=True)
    assert result["n_injected"] == 0
    assert result["n_preserved_placeholders"] == 2
    assert result["refused_non_evidence"] is True
    # Placeholders intact.
    text = (paper / "sections" / "05_results.tex").read_text(encoding="utf-8")
    assert text.count("[RESULT REQUIRED]") == 2


def test_allow_write_injects_eligible_and_guard_passes(tmp_path):
    paper = _paper_dir(tmp_path)
    rdir = _report_dir(tmp_path, evidence_status="REAL_EVIDENCE", provider_type="open_local")
    mani = tmp_path / "rm.json"
    # Place the table where the guard/paper expect it so \input resolves conceptually.
    result_manifest.build_result_manifest(str(rdir), None, str(mani))
    result = inject_results.inject_results(str(mani), str(paper), allow_write=True)
    assert result["n_injected"] >= 1
    text = (paper / "sections" / "05_results.tex").read_text(encoding="utf-8")
    assert "\\input{tables/main_results_table.tex}" in text
    assert "\\includegraphics" in text  # figure injected
    # Guard ran after write and passed (inputs trace to eligible manifest entries).
    assert result["guard_passed"] is True


def test_missing_hash_refused(tmp_path):
    paper = _paper_dir(tmp_path)
    # Hand-build a manifest with an eligible-but-unhashed entry.
    mani = tmp_path / "rm.json"
    write_json(mani, {"entries": [{
        "artifact": "x/main_results_table.tex", "basename": "main_results_table.tex",
        "kind": "table", "sha256": "", "evidence_status": "REAL_EVIDENCE",
        "provider_type": "open_local", "eligible": True,
    }]})
    result = inject_results.inject_results(str(mani), str(paper), allow_write=True)
    assert result["n_injected"] == 0
    assert result["refused_non_evidence"] is True


# --- paper_trace_report ----------------------------------------------------

def test_trace_report_placeholders_only(tmp_path):
    paper = _paper_dir(tmp_path)
    rdir = _report_dir(tmp_path)
    mani = tmp_path / "rm.json"
    result_manifest.build_result_manifest(str(rdir), None, str(mani))
    result = paper_trace_report.trace_paper(str(paper), str(mani))
    f = result["files"][0]
    assert f["n_placeholders"] == 2
    assert f["n_inputs"] == 0
    md = paper_trace_report.render_report(result)
    assert "Paper Result Traceability Report" in md


def test_trace_report_after_injection(tmp_path):
    paper = _paper_dir(tmp_path)
    rdir = _report_dir(tmp_path, evidence_status="REAL_EVIDENCE", provider_type="open_local")
    mani = tmp_path / "rm.json"
    result_manifest.build_result_manifest(str(rdir), None, str(mani))
    inject_results.inject_results(str(mani), str(paper), allow_write=True)
    result = paper_trace_report.trace_paper(str(paper), str(mani))
    f = result["files"][0]
    assert f["n_inputs"] >= 1
    assert f["all_inputs_traced"] is True
    assert result["ok"] is True


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
