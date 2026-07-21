"""Tests for the gated spurious-flip / control_irrelevant integration."""

from __future__ import annotations

from certvic.v7.spurious_control_integration import (
    check_readiness, compute_control_metrics, integrate,
)


def test_readiness_blocks_missing_explicit_human_review_even_with_outputs():
    r = check_readiness(".")
    assert r["ready"] is False
    assert r["specificity_status"] == "blocked"
    assert r["present"]["control_task_manifest"] is True
    assert r["present"]["control_images"] is True
    assert r["present"]["quality_detectability_report"] is True
    assert all(r["present"]["predictions_per_provider"].values())
    assert r["present"]["human_visual_review_complete"] is False
    assert r["n_human_review_approved"] == 0
    assert any("human visual review" in item for item in r["missing"])


def test_integrate_refuses_before_scoring_when_human_review_is_missing():
    status = integrate(".")
    assert status["status"] == "blocked"
    assert status["specificity_status"] == "blocked"
    assert status["paper_evidence"] is False
    assert any("human visual review" in item for item in status["missing"])
    assert "metrics" not in status


def test_compute_control_metrics_flip_math():
    tasks = [{"item_id": "a"}, {"item_id": "b"}, {"item_id": "c"}, {"item_id": "d"}]
    preds = {
        "qwen2_5_vl_7b": {
            "a": {"original": "yes", "edited": "yes"},   # no flip (good specificity)
            "b": {"original": "yes", "edited": "no"},    # spurious flip
            "c": {"original": "no", "edited": "no"},     # no flip
            "d": {"original": "yes", "edited": None},    # parse fail
        }
    }
    m = compute_control_metrics(tasks, preds)["qwen2_5_vl_7b"]
    assert m["n"] == 4
    assert m["n_scored"] == 3
    assert m["spurious_flip_rate"] == round(1 / 3, 4)
    assert m["consistency_under_irrelevant_edit"] == round(2 / 3, 4)
    assert m["parse_failure_rate"] == 0.25
    assert m["gate_pass"] is False


def test_blocked_report_written_without_scoring_unreviewed_controls():
    integrate(".")
    from pathlib import Path
    d = Path("data/results/main_real_200/control_irrelevant_report")
    assert (d / "INTEGRATION_BLOCKED.json").exists()
    assert (d / "INTEGRATION_BLOCKED.md").exists()
    canonical = __import__("json").loads((d / "control_irrelevant_report.json").read_text())
    assert canonical["specificity_status"] == "blocked"
    assert canonical["paper_evidence"] is False
