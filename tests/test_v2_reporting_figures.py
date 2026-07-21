"""Tests for the V2 report builder (tables, figures, claim ledger)."""

from __future__ import annotations

import json
from pathlib import Path

from certvic.data.smoke_fixtures import generate_smoke_tasks
from certvic.eval.run_eval import run_eval
from certvic.io import write_jsonl
from certvic.metrics.score_predictions import score_predictions
from certvic.reporting.build_v2_report import build_v2_report

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = str(REPO_ROOT / "configs" / "smoke.yaml")


def _make_run(tmp_path):
    tasks = generate_smoke_tasks(tmp_path / "smoke", n_items=10)
    tasks_path = tmp_path / "tasks.jsonl"
    write_jsonl(tasks_path, [t.model_dump(mode="json") for t in tasks])
    preds_path = tmp_path / "preds.jsonl"
    run_eval(CONFIG, str(tasks_path), str(preds_path), "mock_inconsistent", "run1", max_items=10)
    scores = score_predictions(str(tasks_path), str(preds_path))
    scores_path = tmp_path / "scores.jsonl"
    write_jsonl(scores_path, [s.model_dump(mode="json") for s in scores])
    return tasks_path, preds_path, scores_path


def test_build_v2_report_writes_tables(tmp_path):
    tasks_path, preds_path, scores_path = _make_run(tmp_path)
    out = tmp_path / "v2_report"
    result = build_v2_report(str(scores_path), str(preds_path), str(tasks_path), str(out))
    for name in [
        "main_results_table.csv", "main_results_table.tex", "by_family_table.csv", "by_family_table.tex",
        "by_domain_table.csv", "by_edit_type_table.csv", "control_edit_table.csv",
        "parser_sensitivity_table.csv", "certification_table.csv", "claim_ledger.json", "report.md",
    ]:
        assert (out / name).exists(), name
    assert result["n"] == 10


def test_smoke_run_is_not_certified(tmp_path):
    tasks_path, preds_path, scores_path = _make_run(tmp_path)
    out = tmp_path / "v2_report"
    result = build_v2_report(str(scores_path), str(preds_path), str(tasks_path), str(out))
    assert result["certified"] is False
    ledger = json.loads((out / "claim_ledger.json").read_text())
    assert ledger["certified"] is False


def test_unavailable_renders_as_double_dash(tmp_path):
    # Empty scores -> tables still render with -- for unavailable cells.
    scores_path = tmp_path / "empty_scores.jsonl"
    scores_path.write_text("", encoding="utf-8")
    out = tmp_path / "v2_report"
    result = build_v2_report(str(scores_path), "", "", str(out))
    text = (out / "main_results_table.tex").read_text()
    assert "--" in text
    assert result["certified"] is False


def test_figures_and_manifest(tmp_path):
    tasks_path, preds_path, scores_path = _make_run(tmp_path)
    out = tmp_path / "v2_report"
    build_v2_report(str(scores_path), str(preds_path), str(tasks_path), str(out))
    manifest = json.loads((out / "figure_manifest.json").read_text())
    ids = {f.get("figure_id") for f in manifest if "figure_id" in f}
    # At least the descriptive figures are present in the manifest.
    assert {"consistency_gap_bar", "parse_failure", "control_spurious_flip"} <= ids
    for f in manifest:
        assert "claim_status" in f
