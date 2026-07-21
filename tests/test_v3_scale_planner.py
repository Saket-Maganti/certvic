"""Tests for the V3 scale planner / free-compute budget (prompt 10)."""

from __future__ import annotations

import json
import sys

from certvic.planning import free_compute_budget, scale_planner


# --- free_compute_budget ---------------------------------------------------

def test_merge_params_overrides():
    p = free_compute_budget.merge_params({"num_models": 5, "edit_seconds_per_item": None})
    assert p["num_models"] == 5
    # None overrides are ignored (default kept).
    assert p["edit_seconds_per_item"] == free_compute_budget.DEFAULTS["edit_seconds_per_item"]


def test_wall_clock_weeks_and_batch():
    assert free_compute_budget.wall_clock_weeks(60.0, 30.0) == 2.0
    assert free_compute_budget.wall_clock_weeks(10.0, 0.0) == float("inf")
    # 11.5h session at 3s/item -> 13800 items.
    assert free_compute_budget.session_batch_size(3.0, 11.5) == int(11.5 * 3600 / 3.0)
    assert free_compute_budget.session_batch_size(0.0, 11.5) == 0


# --- scale_planner ---------------------------------------------------------

def test_plan_scale_monotonic():
    small = scale_planner.plan_scale(200)
    big = scale_planner.plan_scale(2000)
    assert big["gpu"]["total_gpu_hours"] > small["gpu"]["total_gpu_hours"]
    assert big["human"]["total_human_hours"] > small["human"]["total_human_hours"]
    assert big["storage_gb"] >= small["storage_gb"]
    assert small["evidence_claims_made"] is False
    assert small["vlm_inference_run"] is False


def test_plan_scale_components_present():
    plan = scale_planner.plan_scale(200)
    assert plan["gpu"]["edit_gpu_hours"] > 0
    assert plan["gpu"]["vlm_gpu_hours"] > 0
    assert plan["cpu_hours"] >= 0
    assert plan["bottleneck"] in {"free_gpu_quota", "human_review", "storage", "none"}
    assert plan["recommended_batch_sizes"]["vlm_images_per_kaggle_session"] > 0


def test_overrides_change_gpu_estimate():
    base = scale_planner.plan_scale(200)
    more_models = scale_planner.plan_scale(200, overrides={"num_models": 6})
    assert more_models["gpu"]["vlm_gpu_hours"] > base["gpu"]["vlm_gpu_hours"]


def test_human_bottleneck_when_review_is_slow():
    # Very slow human review, plenty of GPU -> human review dominates.
    plan = scale_planner.plan_scale(2000, overrides={"human_seconds_per_item": 120.0, "weekly_free_gpu_hours": 1000.0})
    assert plan["bottleneck"] == "human_review"


def test_storage_bottleneck_flagged():
    plan = scale_planner.plan_scale(500_000)
    assert plan["fits_kaggle_working"] is False
    assert plan["bottleneck"] == "storage"


def test_report_renders(tmp_path):
    plan = scale_planner.plan_scale(200)
    md = scale_planner.render_report(plan)
    assert md.startswith("# Scale & Budget Plan")
    assert "Bottleneck" in md and "GPU" in md


def test_cli_writes_md_and_json(tmp_path):
    out = tmp_path / "plan.md"
    js = tmp_path / "plan.json"
    scale_planner.main(["--scale", "200", "--out", str(out), "--json-out", str(js)])
    assert out.exists() and js.exists()
    data = json.loads(js.read_text(encoding="utf-8"))
    assert data["scale"] == 200 and "gpu" in data


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
