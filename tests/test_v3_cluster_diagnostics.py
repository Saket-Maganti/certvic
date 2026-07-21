"""Tests for the V3 cluster-aware certification diagnostics (prompt 06)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from certvic.io import write_jsonl
from certvic.metrics import cluster_diagnostics, cluster_sensitivity


def _score(item_id, source_id, edit_type, original_correct, consistent, task_family="support_stability", domain="household", model="qwen2_5_vl_7b"):
    return {
        "run_id": "r1",
        "item_id": item_id,
        "provider_name": model,
        "model_name": model,
        "task_family": task_family,
        "domain": domain,
        "original_correct": original_correct,
        "consistent": consistent,
        "required_change": "change",
        "parse_ok": True,
        "metadata": {"source_id": source_id, "edit_type": edit_type},
    }


# --- cluster_sensitivity primitives ----------------------------------------

def test_gap_basic():
    d = np.array([1.0, 0.0, -1.0, 1.0])
    assert cluster_sensitivity.gap(d) == 0.25


def test_icc_high_when_clusters_homogeneous():
    # Two clusters, each internally identical but different from each other.
    d = np.array([1.0, 1.0, 1.0, -1.0, -1.0, -1.0])
    clusters = ["a", "a", "a", "b", "b", "b"]
    res = cluster_sensitivity.icc_and_design_effect(d, clusters)
    assert res["icc"] > 0.8
    assert res["design_effect"] > 1.0
    assert res["n_eff"] < res["n"]


def test_icc_independent_when_one_item_per_cluster():
    d = np.array([1.0, 0.0, -1.0, 1.0])
    clusters = ["a", "b", "c", "d"]
    res = cluster_sensitivity.icc_and_design_effect(d, clusters)
    assert res["design_effect"] == 1.0
    assert res["n_eff"] == 4.0


def test_cluster_bootstrap_ci_is_descriptive_not_certification():
    d = np.array([1.0, 1.0, 0.0, 0.0, 1.0, 0.0])
    clusters = ["a", "a", "b", "b", "c", "c"]
    ci = cluster_sensitivity.cluster_bootstrap_ci(d, clusters, n_boot=500, seed=0)
    assert ci["available"] is True
    assert ci["is_certification"] is False
    assert ci["lo"] <= ci["point"] <= ci["hi"]


def test_leave_one_cluster_out_influence():
    d = np.array([1.0, 1.0, 0.0, 0.0])
    clusters = ["a", "a", "b", "b"]
    loo = cluster_sensitivity.leave_one_cluster_out(d, clusters)
    assert loo["n_clusters"] == 2
    assert loo["most_influential"]["size"] == 2
    assert loo["is_certification"] is False


# --- cluster_diagnostics orchestration -------------------------------------

def _scores_file(tmp_path, n_sources=4, per_source=3):
    rows = []
    i = 0
    for s in range(n_sources):
        for j in range(per_source):
            rows.append(_score(f"item_{i}", f"src_{s}", ["remove", "occlude", "displace"][j % 3], original_correct=True, consistent=(j % 2 == 0)))
            i += 1
    path = tmp_path / "scores.jsonl"
    write_jsonl(path, rows)
    return path, rows


def test_run_diagnostics_positive(tmp_path):
    scores, rows = _scores_file(tmp_path)
    result = cluster_diagnostics.run_cluster_diagnostics(str(scores))
    assert result["n_items"] == len(rows)
    assert "source" in result["dimensions_analyzed"]
    assert result["is_certification"] is False
    assert result["replaces_anytime_valid_cs"] is False
    assert result["evidence_claims_made"] is False
    # source dimension has proper effective-n analysis.
    src = result["per_dimension"]["source"]
    assert src["effective_n"]["n_clusters"] == 4
    assert src["cluster_bootstrap_ci"]["is_certification"] is False


def test_single_cluster_dimension_skipped(tmp_path):
    # All same source -> source dimension has a single cluster.
    rows = [_score(f"i{i}", "only_src", "remove", True, i % 2 == 0) for i in range(6)]
    path = tmp_path / "s.jsonl"
    write_jsonl(path, rows)
    result = cluster_diagnostics.run_cluster_diagnostics(str(path))
    assert result["per_dimension"]["source"].get("skipped") == "single_cluster"


def test_cluster_value_extraction_with_task_enrichment():
    score = _score("i0", "src_0", "remove", True, True)
    task = {"item_id": "i0", "metadata": {"label_name": "chair"}, "edit": {"edit_type": "remove", "params": {"engine": "diffusers_inpaint_optional"}}}
    assert cluster_diagnostics.cluster_value(score, "source", task) == "src_0"
    assert cluster_diagnostics.cluster_value(score, "label", task) == "chair"
    assert cluster_diagnostics.cluster_value(score, "engine", task) == "diffusers_inpaint_optional"


def test_write_outputs_and_report(tmp_path):
    scores, _ = _scores_file(tmp_path)
    result = cluster_diagnostics.run_cluster_diagnostics(str(scores))
    paths = cluster_diagnostics.write_outputs(result, str(tmp_path / "out"))
    for p in paths.values():
        assert Path(p).exists()
    report = Path(paths["report"]).read_text(encoding="utf-8")
    assert "Cluster-Dependence Diagnostics" in report
    assert "NOT certification" in report


def test_empty_scores(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    result = cluster_diagnostics.run_cluster_diagnostics(str(path))
    assert result["n_items"] == 0
    assert result["is_certification"] is False


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
