"""Tests for the V7 scale planner."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from certvic.validation.detectability_gate import CONDITIONAL_MAX_AUC, GO_MAX_AUC

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "plan_scaled_main_run", REPO / "scripts/plan_scaled_main_run.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def test_targets_cover_500_to_2000():
    assert mod.TARGETS == [500, 800, 1000, 2000]


def test_plans_are_projections_and_zero_cost():
    surv = mod._observed_survival()
    for n in mod.TARGETS:
        p = mod.plan_for_target(n, surv, vlm_lat=1.5, kb_img=63.4)
        assert p["is_projection"] is True
        assert p["cost_usd"] == 0


def test_projected_resources_increase_with_target():
    surv = mod._observed_survival()
    src = [mod.plan_for_target(n, surv, 1.5, 63.4)["projected_source_items"] for n in mod.TARGETS]
    assert src == sorted(src) and src[0] < src[-1]


def test_observed_survival_matches_artifacts():
    surv = mod._observed_survival()
    assert surv["candidates"] == 200 and surv["planned"] == 168
    assert surv["tasks"] == 103 and surv["approved"] == 91
    assert abs(surv["overall"] - 91 / 200) < 1e-9


def test_stop_go_gates_reuse_canonical_detectability_thresholds():
    gates = {g["gate"]: g for g in mod.stop_go_gates()}
    det = gates["detectability_auc"]
    # Thresholds must reference the canonical constants, not weakened numbers.
    assert str(CONDITIONAL_MAX_AUC) in det["halt_if"]
    assert str(GO_MAX_AUC) in det["conditional_if"]
    assert "result_ledger_hashing" in gates
    assert "controls" in gates
