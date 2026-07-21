from __future__ import annotations

import json

from certvic.io import load_model_jsonl, read_jsonl
from certvic.schema import PairScore, PredictionRecord, TaskItem
from certvic.sim.generate_synthetic_run import main as generate_main
from certvic.sim.outcome_models import BUILTIN_SCENARIOS, generate_outcome
from certvic.sim.simulated_manifests import build_synthetic_run, validate_synthetic_artifacts
from certvic.sim.stress_scenarios import run_stress_matrix
from certvic.validation.claims import validate_certified_claim_eligibility


def _task_view():
    return {
        "item_id": "sim_000001",
        "answer_original": "yes",
        "answer_edited": "no",
        "required_change": "change",
        "task_family": "support_stability",
        "domain": "household",
        "edit_type": "displace",
    }


def test_v2_1_outcome_models_are_seed_deterministic():
    for scenario in BUILTIN_SCENARIOS:
        a = [generate_outcome(_task_view(), scenario, seed=3, index=i) for i in range(8)]
        b = [generate_outcome(_task_view(), scenario, seed=3, index=i) for i in range(8)]
        c = [generate_outcome(_task_view(), scenario, seed=4, index=i) for i in range(8)]
        assert a == b
        assert a != c or scenario == "perfect_consistent"


def test_v2_1_synthetic_manifests_are_schema_compatible_and_simulated(tmp_path):
    result = build_synthetic_run(tmp_path / "run", "high_accuracy_low_consistency", n_items=32, seed=0)
    validation = validate_synthetic_artifacts(
        result["tasks_path"],
        result["predictions_path"],
        result["scores_path"],
    )
    assert validation["tasks"] == 32
    assert validation["predictions"] == 64
    assert validation["scores"] == 32
    assert validation["all_simulated_only"] is True
    tasks = load_model_jsonl(result["tasks_path"], TaskItem)
    preds = load_model_jsonl(result["predictions_path"], PredictionRecord)
    scores = load_model_jsonl(result["scores_path"], PairScore)
    assert all(task.metadata["simulated"] is True for task in tasks)
    assert all(pred.metadata["not_for_paper_claims"] is True for pred in preds)
    assert all(score.metadata["evidence_status"] == "SIMULATED_ONLY" for score in scores)


def test_v2_1_scenario_cli_writes_expected_files(tmp_path):
    out_dir = tmp_path / "single"
    generate_main([
        "--out-dir",
        str(out_dir),
        "--scenario",
        "parse_failure_heavy",
        "--n-items",
        "40",
        "--seed",
        "0",
    ])
    for name in [
        "simulated_tasks.jsonl",
        "simulated_predictions.jsonl",
        "simulated_pair_scores.jsonl",
        "simulated_run_metadata.json",
        "scenario_config.json",
    ]:
        assert (out_dir / name).exists()
    metadata = json.loads((out_dir / "simulated_run_metadata.json").read_text())
    assert metadata["evidence_status"] == "SIMULATED_ONLY"
    assert metadata["not_for_paper_claims"] is True


def test_v2_1_matrix_writes_summary_and_blocks_claims(tmp_path):
    result = run_stress_matrix(tmp_path / "matrix", n_items=80, seed=0)
    assert result["scenarios"] == len(BUILTIN_SCENARIOS)
    assert result["all_claim_gates_blocked"] is True
    assert (tmp_path / "matrix" / "scenario_matrix_summary.csv").exists()
    assert (tmp_path / "matrix" / "scenario_matrix_summary.json").exists()
    assert (tmp_path / "matrix" / "scenario_matrix_report.md").exists()
    rows = json.loads((tmp_path / "matrix" / "scenario_matrix_summary.json").read_text())["scenarios"]
    by_name = {row["scenario"]: row for row in rows}
    assert abs(by_name["null_gap"]["gap"]) <= 0.05
    assert by_name["high_accuracy_low_consistency"]["gap"] > 0.15
    assert by_name["parse_failure_heavy"]["parse_failure_rate"] >= 0.20
    assert by_name["parse_failure_heavy"]["parse_failure_warning"] is True
    assert by_name["spurious_control_flipper"]["control_spurious_flip_rate"] >= 0.25
    assert by_name["spurious_control_flipper"]["control_spurious_flip_warning"] is True
    assert by_name["small_gap_borderline"]["certified"] is False
    assert all(row["claim_gate_blocks_simulated"] for row in rows)


def test_v2_1_simulated_status_is_claim_blocked():
    certification = {
        "confidence_sequence": {"available": True, "latest": {"lo": 0.20, "hi": 0.40}},
        "lower_bound": 0.20,
    }
    errors = validate_certified_claim_eligibility(
        certification,
        claim_text="A narrow certified gap claim.",
        evidence_context={
            "splits": ["simulation"],
            "evidence_statuses": ["SIMULATED_ONLY"],
            "provider_types": ["baseline"],
            "has_synthetic_smoke_fixtures": False,
        },
        threshold=0.05,
    )
    assert any("SIMULATED_ONLY" in error for error in errors)


def test_v2_1_reports_do_not_mark_simulated_runs_as_evidence(tmp_path):
    result = run_stress_matrix(tmp_path / "matrix", n_items=40, seed=1, scenarios=["null_gap"])
    assert result["all_claim_gates_blocked"] is True
    scenario_dir = tmp_path / "matrix" / "null_gap"
    report_text = (scenario_dir / "v2_report" / "report.md").read_text()
    claim_ledger = json.loads((scenario_dir / "v2_report" / "claim_ledger.json").read_text())
    matrix_text = (tmp_path / "matrix" / "scenario_matrix_report.md").read_text()
    assert "SIMULATED_ONLY" in report_text
    assert "not real data" in report_text
    assert claim_ledger["simulation_only"] is True
    assert claim_ledger["certified"] is False
    assert "not model evidence" in matrix_text
    assert read_jsonl(scenario_dir / "simulated_pair_scores.jsonl")
