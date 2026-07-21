from __future__ import annotations

from certvic.eval.run_eval import run_eval
from certvic.io import read_json, write_jsonl
from certvic.metrics.report_metrics import build_metrics_report
from certvic.metrics.score_predictions import score_predictions
from certvic.reporting.build_report import build_report
from certvic.schema import PairScore


def test_metrics_report_labels_descriptive_ci(smoke_tasks, tmp_path):
    tasks_path = tmp_path / "tasks.jsonl"
    preds_path = tmp_path / "preds.jsonl"
    config_path = tmp_path / "config.yaml"
    write_jsonl(tasks_path, smoke_tasks[:4])
    config_path.write_text("paid_services_enabled: false\n", encoding="utf-8")
    run_eval(str(config_path), str(tasks_path), str(preds_path), "mock_perfect", "run")
    scores = score_predictions(str(tasks_path), str(preds_path))
    report = build_metrics_report(scores, alpha=0.05, gap_threshold=0.05)
    assert report["descriptive_ci"]["overall"]["label"] == "descriptive_only_not_anytime_valid"
    assert "by_task_family" in report["descriptive_ci"]


def test_report_builder_writes_v1_1_outputs(smoke_tasks, tmp_path):
    tasks_path = tmp_path / "tasks.jsonl"
    preds_path = tmp_path / "preds.jsonl"
    scores_path = tmp_path / "scores.jsonl"
    config_path = tmp_path / "config.yaml"
    out_dir = tmp_path / "report"
    write_jsonl(tasks_path, smoke_tasks[:4])
    config_path.write_text("paid_services_enabled: false\n", encoding="utf-8")
    run_eval(str(config_path), str(tasks_path), str(preds_path), "mock_perfect", "run")
    scores = score_predictions(str(tasks_path), str(preds_path))
    write_jsonl(scores_path, scores)
    build_report(str(tasks_path), str(scores_path), str(preds_path), str(out_dir))
    expected = [
        "main_model_table.csv",
        "main_model_table.tex",
        "by_family_table.csv",
        "by_domain_table.csv",
        "control_edit_table.csv",
        "parse_failure_table.csv",
        "certification_status.json",
        "claim_ledger.json",
        "failure_gallery.jsonl",
        "report.md",
    ]
    for name in expected:
        assert (out_dir / name).exists()
    report_text = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "MOCK_ONLY" in report_text
    assert "No evidence claims are made" in report_text
    assert "No paid services were used" in report_text
    assert "Real pilot data are required before paper claims" in report_text
    assert not read_json(out_dir / "certification_status.json")["certified"]


def test_metrics_report_cannot_certify_cs_crossing_below_policy_minimum(monkeypatch):
    scores = [
        PairScore(
            run_id="r",
            item_id=f"i{index}",
            provider_name="qwen2_5_vl_7b",
            model_name="qwen",
            task_family="support_stability",
            domain="household",
            original_correct=True,
            edited_correct=False,
            consistent=False,
            required_change="change",
            parse_ok=True,
        )
        for index in range(91)
    ]

    def threshold_crossing(*args, **kwargs):
        return {
            "certified": True,
            "cs_threshold_passed": True,
            "lower_bound": 0.2,
            "upper_bound": 1.0,
            "threshold": 0.05,
            "alpha": 0.05,
            "confidence_sequence": {"available": True, "latest": {"lo": 0.2, "hi": 1.0}},
            "certification_gate_errors": [],
            "statement": "threshold crossed",
            "safe_claim": "threshold crossed",
        }

    monkeypatch.setattr("certvic.metrics.report_metrics.certify_gap", threshold_crossing)
    report = build_metrics_report(
        scores,
        alpha=0.05,
        gap_threshold=0.05,
        evidence_context={
            "splits": ["validation"],
            "evidence_statuses": ["HUMAN_REVIEWED_NON_EVIDENCE"],
            "provider_types": ["open_local"],
        },
    )
    assert report["certification"]["cs_threshold_passed"] is True
    assert report["certification"]["certified"] is False
    errors = report["certification"]["certification_gate_errors"]
    assert any("min_n_overall" in error for error in errors)
    assert any("specificity gate is required" in error for error in errors)
