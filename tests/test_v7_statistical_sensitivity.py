"""Tests for V7 statistical sensitivity + sequential-design plan."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from certvic.io import read_json

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "main_study_power_and_stopping_plan", REPO / "scripts/main_study_power_and_stopping_plan.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

SENS = REPO / "data/results/main_real_200/statistical_sensitivity.json"


def test_thresholds_unchanged_and_plan_non_evidence():
    r = read_json(SENS)
    assert r["thresholds_unchanged"] == {"gap_threshold": 0.05, "alpha": 0.05}
    assert r["paper_evidence"] is False


def test_observed_effect_sizes_match_canonical():
    r = read_json(SENS)
    by = {m["provider"]: m for m in r["observed_pilot_effect_sizes"]}
    assert by["internvl_8b"]["observed_gap_delta"] == 0.8242
    assert by["qwen2_5_vl_7b"]["observed_gap_delta"] == 0.7473


def test_conservative_deltas_below_observed():
    r = read_json(SENS)
    lo_obs = r["observed_gap_range"][0]
    for e in r["conservative_planning_deltas"]["estimates"]:
        assert e["conservative_delta"] < lo_obs  # deliberately conservative


def test_planning_n_decreases_with_larger_delta():
    r = read_json(SENS)
    est = sorted(r["conservative_planning_deltas"]["estimates"], key=lambda e: e["conservative_delta"])
    ns = [e["n"] for e in est]
    assert ns == sorted(ns, reverse=True)  # bigger effect -> fewer items


def test_optional_stopping_type_i_error_within_alpha():
    r = read_json(SENS)
    for s in r["optional_stopping_plan"]["simulations"]:
        if s.get("available"):
            assert s["type_i_error"] is not None
            assert s["type_i_error"] <= 0.05 + 1e-9  # anytime-valid control under peeking


def test_what_not_to_certify_lists_specificity_and_affordance():
    r = read_json(SENS)
    joined = " ".join(r["what_not_to_certify"]).lower()
    assert "specificity" in joined
    assert "affordance" in joined
