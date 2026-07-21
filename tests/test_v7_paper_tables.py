"""Tests for the V7 main-200 paper-table generator."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "build_main200_paper_tables", REPO / "scripts/build_main200_paper_tables.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def test_intervention_rows_match_canonical_summary():
    reports = mod._load_reports()
    rows = {r["provider"]: r for r in mod._intervention_rows(reports)}
    assert set(rows) == {"qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"}
    qwen = rows["qwen2_5_vl_7b"]
    assert qwen["original_accuracy_a"] == 0.9231
    assert qwen["delta_gap"] == 0.7473
    assert qwen["cs_threshold_passed"] is True
    assert qwen["certified"] is False
    assert rows["internvl_8b"]["cs_lower"] == 0.4409


def test_control_irrelevant_rows_reflect_real_spurious_gate_status():
    reports = mod._load_reports()
    per_edit = mod._per_edit_type_rows(reports)
    ci = [r for r in per_edit if r["edit_type"] == "control_irrelevant"]
    assert ci, "control_irrelevant rows must be present"
    by_provider = {r["provider"]: r for r in ci}
    assert by_provider["qwen2_5_vl_7b"]["status"] == "gate_fail"
    assert by_provider["internvl_8b"]["status"] == "gate_pass"
    assert by_provider["llava_onevision_7b"]["status"] == "gate_pass"
    assert all(r["n"] == 94 for r in ci)


def test_every_run_edit_type_has_real_counts():
    reports = mod._load_reports()
    per_edit = mod._per_edit_type_rows(reports)
    run_rows = [r for r in per_edit if r["status"] == "run"]
    assert run_rows
    for r in run_rows:
        assert isinstance(r["n"], int) and r["n"] > 0
        assert r["gap"] is not None
