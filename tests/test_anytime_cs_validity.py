"""Tests for the native anytime-valid CS and the empirical validity lab."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from certvic.metrics.anytime_cs import hoeffding_mixture_cs_01
from certvic.metrics.confseq_wrappers import bounded_mean_cs_01, gap_cs
from certvic.sim.anytime_validity import run_anytime_validity_lab, simulate


def test_native_cs_is_available_and_bounded():
    rng = np.random.default_rng(0)
    x = (rng.random(200) < 0.4).astype(float)
    res = hoeffding_mixture_cs_01(x, alpha=0.05)
    assert res["available"] is True
    assert res["method"].endswith("hoeffding_mixture")
    assert len(res["lo"]) == len(res["hi"]) == 200
    assert all(0.0 <= lo <= hi <= 1.0 for lo, hi in zip(res["lo"], res["hi"]))


def test_native_cs_matches_closed_form_reference_at_t_one():
    alpha = 0.05
    t_opt = 10
    sigma2 = 4.0 / t_opt
    a_one = 1.0 / 8.0 + 1.0 / (2.0 * sigma2)
    radius = math.sqrt(4.0 * a_one * math.log(math.sqrt(sigma2 * 2.0 * a_one) / alpha))
    result = hoeffding_mixture_cs_01([0.5], alpha=alpha, t_opt=t_opt)
    assert result["lo"][0] == max(0.0, 0.5 - radius)
    assert result["hi"][0] == min(1.0, 0.5 + radius)


def test_native_cs_width_shrinks_with_n():
    rng = np.random.default_rng(1)
    x = (rng.random(400) < 0.5).astype(float)
    res = hoeffding_mixture_cs_01(x, alpha=0.05)
    width_early = res["hi"][9] - res["lo"][9]
    width_late = res["hi"][-1] - res["lo"][-1]
    assert width_late < width_early


def test_native_cs_rejects_out_of_range():
    with pytest.raises(ValueError):
        hoeffding_mixture_cs_01([0.0, 1.5], alpha=0.05)


def test_native_cs_empty_is_available_but_none():
    res = hoeffding_mixture_cs_01([], alpha=0.05)
    assert res["available"] is True
    assert res["latest"] == {"lo": None, "hi": None}


def test_auto_backend_falls_back_to_native_when_confseq_absent():
    res = bounded_mean_cs_01([0, 1, 1, 0, 1], allow_unavailable=True, backend="auto")
    assert res["available"] is True  # native fallback guarantees availability


def test_explicit_native_backend():
    res = bounded_mean_cs_01([0, 1, 1], backend="native")
    assert res["method"].endswith("hoeffding_mixture")


def test_gap_cs_native_maps_to_delta_scale():
    # a always correct, C always inconsistent -> Delta = 1.
    g = gap_cs([1] * 50, [0] * 50, backend="native")
    assert g["available"] is True
    assert g["latest"]["hi"] <= 1.0
    assert g["latest"]["lo"] < g["latest"]["hi"]


def test_simulate_null_controls_type_i_under_peeking():
    res = simulate(true_delta=0.0, n=300, n_trials=1500, alpha=0.05, threshold=0.0, seed=0)
    # CS keeps false-certification at/under alpha under continuous peeking.
    assert res["cs_certify_rate"] <= 0.05
    # Peeked fixed-n CI inflates well past alpha (the cautionary baseline).
    assert res["peeking_fixed_n_certify_rate"] > res["cs_certify_rate"]
    # CS coverage of the true mean is controlled.
    assert res["cs_miscoverage_rate"] <= 0.05


def test_validity_lab_writes_artifacts_and_passes_checks(tmp_path):
    result = run_anytime_validity_lab(
        tmp_path / "av", n=250, n_trials=1200, alpha=0.05, threshold=0.0, seed=0
    )
    assert result["all_checks_passed"] is True
    assert result["evidence_status"] == "SIMULATED_ONLY"
    payload = json.loads((tmp_path / "av" / "anytime_validity_summary.json").read_text())
    assert payload["simulated_only"] is True
    assert payload["checks"]["cs_type_i_controlled"] is True
    assert payload["checks"]["peeking_fixed_n_inflates_type_i"] is True
    assert (tmp_path / "av" / "anytime_validity_summary.csv").exists()
    report = (tmp_path / "av" / "anytime_validity_report.md").read_text()
    assert "SIMULATED_ONLY" in report
    assert "not VLM evidence" in report or "not real" in report
