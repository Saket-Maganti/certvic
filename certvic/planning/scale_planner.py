"""Scale planner for CertVIC studies (V3 prompt 10).

Estimates the CPU / GPU / human / wall-clock / storage cost of a study at a given
scale under free Kaggle/Colab limits, names the bottleneck, and recommends
per-session batch sizes. Reuses the V3 storage planner for disk. Conservative,
not optimistic. No inference, no downloads, no paid services.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from certvic.io import ensure_parent
from certvic.planning.free_compute_budget import (
    COLAB_SESSION_HOURS,
    merge_params,
    session_batch_size,
    wall_clock_weeks,
)
from certvic.storage.plan_storage import estimate_storage


def plan_scale(scale: int, *, overrides: dict | None = None) -> dict:
    p = merge_params(overrides)
    n = int(scale)
    candidates = int(round(n * p["overgeneration_factor"]))

    # GPU time.
    edit_gpu_seconds = candidates * p["edit_seconds_per_item"]
    vlm_runs = n * p["variants_per_item"] * p["num_models"] * p["ablation_multiplier"]
    vlm_gpu_seconds = vlm_runs * p["vlm_seconds_per_item"]
    gpu_seconds = edit_gpu_seconds + vlm_gpu_seconds
    gpu_hours = gpu_seconds / 3600.0

    # CPU time (masks, scoring, reporting).
    cpu_seconds = n * p["cpu_seconds_per_item"]
    cpu_hours = cpu_seconds / 3600.0

    # Human time (review). Wall-clock assumes a sustainable hours/day.
    human_seconds = n * p["human_seconds_per_item"]
    human_hours = human_seconds / 3600.0
    human_days = human_hours / p["human_hours_per_day"] if p["human_hours_per_day"] > 0 else float("inf")

    gpu_weeks = wall_clock_weeks(gpu_hours, p["weekly_free_gpu_hours"])

    storage = estimate_storage(
        n,
        bytes_per=None,
        config={"tiny_edit_generation": {"overgeneration_factor": p["overgeneration_factor"]}},
    )

    # Bottleneck: compare wall-clock contributions (weeks).
    gpu_calendar_weeks = gpu_weeks
    human_calendar_weeks = human_days / 7.0
    if gpu_calendar_weeks >= human_calendar_weeks and gpu_calendar_weeks > 0:
        bottleneck = "free_gpu_quota"
    elif human_calendar_weeks > 0:
        bottleneck = "human_review"
    else:
        bottleneck = "none"
    if not storage["fits_kaggle_working"]:
        bottleneck = "storage"

    batch_sizes = {
        "edit_items_per_kaggle_session": session_batch_size(p["edit_seconds_per_item"], p["session_hours"]),
        "vlm_images_per_kaggle_session": session_batch_size(p["vlm_seconds_per_item"], p["session_hours"]),
        "vlm_images_per_colab_session": session_batch_size(p["vlm_seconds_per_item"], COLAB_SESSION_HOURS),
    }

    return {
        "plan": "certvic_scale_plan",
        "scale": n,
        "params": p,
        "candidates_generated": candidates,
        "gpu": {
            "edit_gpu_hours": round(edit_gpu_seconds / 3600.0, 2),
            "vlm_gpu_hours": round(vlm_gpu_seconds / 3600.0, 2),
            "total_gpu_hours": round(gpu_hours, 2),
            "weekly_free_gpu_hours": p["weekly_free_gpu_hours"],
            "wall_clock_weeks_under_quota": round(gpu_weeks, 2),
        },
        "cpu_hours": round(cpu_hours, 3),
        "human": {
            "total_human_hours": round(human_hours, 2),
            "human_hours_per_day": p["human_hours_per_day"],
            "wall_clock_days": round(human_days, 1),
            "wall_clock_weeks": round(human_calendar_weeks, 2),
        },
        "storage_gb": storage["working_gb"],
        "fits_kaggle_working": storage["fits_kaggle_working"],
        "storage_warnings": storage["warnings"],
        "bottleneck": bottleneck,
        "recommended_batch_sizes": batch_sizes,
        "evidence_claims_made": False,
        "downloads_attempted": False,
        "paid_services": False,
        "vlm_inference_run": False,
    }


def render_report(plan: dict) -> str:
    g = plan["gpu"]
    h = plan["human"]
    lines = [
        f"# Scale & Budget Plan — {plan['scale']} items",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "Conservative estimate under free Kaggle/Colab limits. No inference run; no claims.",
        "",
        f"**Bottleneck: `{plan['bottleneck']}`**",
        "",
        "## GPU",
        "",
        f"- Edit generation: {g['edit_gpu_hours']} GPU-h ({plan['candidates_generated']} candidates)",
        f"- VLM inference: {g['vlm_gpu_hours']} GPU-h "
        f"({plan['params']['num_models']} models × {plan['params']['variants_per_item']} variants × {plan['params']['ablation_multiplier']}× ablations)",
        f"- Total: {g['total_gpu_hours']} GPU-h",
        f"- Free GPU quota: {g['weekly_free_gpu_hours']} h/week → **{g['wall_clock_weeks_under_quota']} week(s)** wall-clock",
        "",
        "## Human review",
        "",
        f"- {h['total_human_hours']} h at {plan['params']['human_seconds_per_item']} s/item",
        f"- At {h['human_hours_per_day']} h/day → {h['wall_clock_days']} day(s) (~{h['wall_clock_weeks']} week(s))",
        "",
        "## CPU & storage",
        "",
        f"- CPU work: {plan['cpu_hours']} h",
        f"- Working storage: {plan['storage_gb']} GB (fits Kaggle ~20 GB: {plan['fits_kaggle_working']})",
        *([f"- WARNING: {w}" for w in plan["storage_warnings"]]),
        "",
        "## Recommended per-session batch sizes",
        "",
        f"- Edit items / Kaggle session: {plan['recommended_batch_sizes']['edit_items_per_kaggle_session']}",
        f"- VLM images / Kaggle session: {plan['recommended_batch_sizes']['vlm_images_per_kaggle_session']}",
        f"- VLM images / Colab session: {plan['recommended_batch_sizes']['vlm_images_per_colab_session']}",
        "",
    ]
    return "\n".join(lines)


def _overrides_from_args(args) -> dict:
    keys = [
        "overgeneration_factor", "edit_seconds_per_item", "vlm_seconds_per_item",
        "num_models", "ablation_multiplier", "human_seconds_per_item",
        "weekly_free_gpu_hours",
    ]
    return {k: getattr(args, k) for k in keys if getattr(args, k, None) is not None}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC scale & free-compute budget planner")
    parser.add_argument("--scale", type=int, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--overgeneration-factor", type=float)
    parser.add_argument("--edit-seconds-per-item", type=float)
    parser.add_argument("--vlm-seconds-per-item", type=float)
    parser.add_argument("--num-models", type=int)
    parser.add_argument("--ablation-multiplier", type=float)
    parser.add_argument("--human-seconds-per-item", type=float)
    parser.add_argument("--weekly-free-gpu-hours", type=float)
    parser.add_argument("--json-out")
    args = parser.parse_args(argv)
    plan = plan_scale(args.scale, overrides=_overrides_from_args(args))
    ensure_parent(args.out)
    Path(args.out).write_text(render_report(plan), encoding="utf-8")
    if args.json_out:
        import json

        ensure_parent(args.json_out)
        Path(args.json_out).write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
    import json

    print(json.dumps({
        "scale": plan["scale"],
        "total_gpu_hours": plan["gpu"]["total_gpu_hours"],
        "human_hours": plan["human"]["total_human_hours"],
        "storage_gb": plan["storage_gb"],
        "bottleneck": plan["bottleneck"],
        "out": args.out,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
