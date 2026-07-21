"""Tests for V2 power planning, optional stopping, and the certification policy."""

from __future__ import annotations

from pathlib import Path

from certvic.metrics.certification_policy import (
    evaluate_certification_policy,
    load_certification_policy,
)
from certvic.metrics.power import (
    _norm_ppf,
    estimate_n_for_gap,
    minimum_detectable_gap_grid,
    simulate_consistency_gap,
)
from certvic.metrics.power_plan import build_power_plan

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_norm_ppf_known_values():
    assert abs(_norm_ppf(0.975) - 1.959963985) < 1e-3
    assert abs(_norm_ppf(0.95) - 1.6448536) < 1e-3
    assert abs(_norm_ppf(0.5)) < 1e-6


def test_estimate_n_for_gap_monotone():
    big = estimate_n_for_gap(0.30, threshold=0.05)
    small = estimate_n_for_gap(0.10, threshold=0.05)
    assert big["feasible"] and small["feasible"]
    assert big["n"] < small["n"]  # larger gap needs fewer samples


def test_estimate_n_infeasible_when_gap_not_above_threshold():
    res = estimate_n_for_gap(0.05, threshold=0.05)
    assert res["feasible"] is False


def test_mdg_grid_decreases_with_n():
    grid = minimum_detectable_gap_grid([50, 200, 500])
    gaps = [row["minimum_detectable_gap_over_threshold"] for row in grid]
    assert gaps == sorted(gaps, reverse=True)


def test_simulate_consistency_gap_degrades_without_confseq():
    res = simulate_consistency_gap(n=100, accuracy=0.8, consistency=0.5, allow_unavailable=True)
    assert "empirical_gap" in res
    assert res["cs_available"] in (True, False)
    if not res["cs_available"]:
        assert res["certified"] is False


def test_power_plan_cli_writes_files(tmp_path):
    plan = build_power_plan(None, str(tmp_path / "pp"), gaps=[0.1, 0.2], n_values=[100, 200])
    assert (tmp_path / "pp" / "power_plan.json").exists()
    assert (tmp_path / "pp" / "n_vs_gap.csv").exists()
    assert (tmp_path / "pp" / "power_plan.md").exists()
    assert len(plan["n_for_gap"]) == 2


def test_default_policy_loads_and_blocks_mock():
    policy = load_certification_policy(str(REPO_ROOT / "configs" / "certification_policy.yaml"))
    summary = {"n": 200, "parse_failure_rate": 0.01, "by_task_family": {"support_stability": {"n": 60}}, "control_edit": {"spurious_flip_rate": 0.02}}
    certification = {"confidence_sequence": {"available": True}, "lower_bound": 0.2}
    context = {"evidence_statuses": ["HUMAN_REVIEWED_NON_EVIDENCE"], "provider_types": ["mock"]}
    result = evaluate_certification_policy(summary, certification, policy, context)
    assert result["policy_passed"] is False
    assert any("disallowed provider" in e for e in result["errors"])


def test_policy_passes_with_clean_evidence():
    policy = load_certification_policy(None)
    summary = {"n": 200, "parse_failure_rate": 0.01, "by_task_family": {"support_stability": {"n": 60}}, "control_edit": {"spurious_flip_rate": 0.02}}
    certification = {"confidence_sequence": {"available": True}, "lower_bound": 0.2}
    context = {"evidence_statuses": ["HUMAN_REVIEWED_NON_EVIDENCE"], "provider_types": ["open_local"]}
    result = evaluate_certification_policy(summary, certification, policy, context)
    assert result["policy_passed"] is True
    assert result["certified"] is True


def test_policy_blocks_when_cs_unavailable():
    policy = load_certification_policy(None)
    summary = {"n": 200, "parse_failure_rate": 0.0, "by_task_family": {}, "control_edit": {}}
    certification = {"confidence_sequence": {"available": False}, "lower_bound": None}
    context = {"evidence_statuses": ["HUMAN_REVIEWED_NON_EVIDENCE"], "provider_types": ["open_local"]}
    result = evaluate_certification_policy(summary, certification, policy, context)
    assert result["policy_passed"] is False
    assert any("CS unavailable" in e for e in result["errors"])


def test_policy_blocks_small_n():
    policy = load_certification_policy(None)
    summary = {"n": 10, "parse_failure_rate": 0.0, "by_task_family": {}, "control_edit": {}}
    certification = {"confidence_sequence": {"available": True}, "lower_bound": 0.2}
    context = {"evidence_statuses": ["HUMAN_REVIEWED_NON_EVIDENCE"], "provider_types": ["open_local"]}
    result = evaluate_certification_policy(summary, certification, policy, context)
    assert result["policy_passed"] is False
    assert any("min_n_overall" in e for e in result["errors"])


def test_policy_requires_separate_specificity_gate():
    policy = load_certification_policy(None)
    summary = {
        "n": 200,
        "parse_failure_rate": 0.0,
        "by_task_family": {"support_stability": {"n": 200}},
        "control_edit": {},
    }
    certification = {"confidence_sequence": {"available": True}, "lower_bound": 0.2}
    context = {
        "evidence_statuses": ["HUMAN_REVIEWED_NON_EVIDENCE"],
        "provider_types": ["open_local"],
    }
    result = evaluate_certification_policy(summary, certification, policy, context)
    assert result["policy_passed"] is False
    assert any("specificity gate is required" in error for error in result["errors"])
