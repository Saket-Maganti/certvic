"""Plan a larger real CertVIC run (main_500 .. main_2000) without breaking gates (V7 prompt 05).

Projects the resources needed to reach a target number of *reviewed-approved* items, using
**observed pilot survival rates** (from real artifacts) and **observed VLM latency**. Every
output number that is not directly measured is a **projection** and is labelled as such.
Diffusion throughput and human-review pace are explicit planning **assumptions** (documented).

This script launches no GPU jobs, downloads nothing, and does not weaken any quality or
detectability threshold (it imports the canonical detectability thresholds rather than
restating them).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from certvic.io import read_json, write_json  # noqa: E402
from certvic.validation.detectability_gate import (  # noqa: E402
    ARTIFACT_CONFOUNDED_AUC, CONDITIONAL_MAX_AUC, GO_MAX_AUC,
)

RESULTS = REPO / "data/results/main_real_200"
OUT_DIR = REPO / "data/results/scale_plans"
CMD_DIR = REPO / "commands/scale"
DOC = REPO / "docs/SCALE_PLAN_MAIN_800_2000.md"

TARGETS = [500, 800, 1000, 2000]

# ---- Planning assumptions (NOT measurements). Conservative; documented in the report. ----
DIFFUSION_SEC_PER_EDIT = 25.0      # SD-inpaint on a free T4, incl. amortized load
SESSION_USABLE_HOURS = 9.0         # conservative usable GPU hours per free Kaggle session
REVIEW_MIN_PER_ITEM = 1.5          # primary visual review pace (assumption)
RESIDUAL_REVIEW_MIN_PER_ITEM = 1.0 # residual-cue pass (assumption)
VLM_LATENCY_SAFETY = 2.0           # multiply observed mean latency for headroom
CONTROL_ITEMS_FIXED = 120          # absent-object control set size (held fixed across scales)
KB_PER_IMAGE_FALLBACK = 63.4


def _observed_survival() -> dict:
    eps = read_json(RESULTS / "pilot_edit_plan_summary.json")
    rev = read_json(RESULTS / "reviewed_summary.json")
    candidates, planned = eps["input_candidates"], eps["planned"]
    tasks, approved = rev["input_tasks"], rev["approved_tasks"]
    return {
        "candidates": candidates, "planned": planned, "tasks": tasks, "approved": approved,
        "plan_yield": planned / candidates,         # candidate -> planned edit
        "task_yield": tasks / planned,              # planned edit -> generated/quality-passed task
        "approve_rate": approved / tasks,           # task -> human-approved
        "overall": approved / candidates,           # candidate -> approved
    }


def _observed_vlm_latency() -> float:
    path = RESULTS / "raw_predictions/presence__pred_qwen2_5_vl_7b_merged.jsonl"
    lats = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r.get("latency_s"):
            lats.append(r["latency_s"])
    return sum(lats) / len(lats) if lats else 2.0


def _kb_per_image() -> float:
    import glob
    import os
    fs = glob.glob(str(REPO / "data/edits/main_real_200/*.jpg"))
    fs += glob.glob(str(REPO / "data/edits/main_real_200/orig/*.jpg"))
    if not fs:
        return KB_PER_IMAGE_FALLBACK
    return sum(os.path.getsize(f) for f in fs) / len(fs) / 1024.0


def plan_for_target(n_target: int, surv: dict, vlm_lat: float, kb_img: float) -> dict:
    # Backward chain from approved-target -> tasks -> planned edits -> source candidates.
    tasks_needed = math.ceil(n_target / surv["approve_rate"])
    planned_needed = math.ceil(tasks_needed / surv["task_yield"])
    source_items = math.ceil(planned_needed / surv["plan_yield"])

    session_seconds = SESSION_USABLE_HOURS * 3600
    diffusion_sessions = math.ceil(planned_needed * DIFFUSION_SEC_PER_EDIT / session_seconds)

    # VLM per model: presence (orig+edited = 2x tasks) + fixed control set.
    vlm_inferences_per_model = tasks_needed * 2 + CONTROL_ITEMS_FIXED
    vlm_seconds = vlm_inferences_per_model * vlm_lat * VLM_LATENCY_SAFETY
    vlm_sessions_per_model = max(1, math.ceil(vlm_seconds / session_seconds))

    review_hours = round(tasks_needed * (REVIEW_MIN_PER_ITEM + RESIDUAL_REVIEW_MIN_PER_ITEM) / 60, 1)
    images = planned_needed * 2 + CONTROL_ITEMS_FIXED  # edited+orig per edit, plus control imgs
    storage_mb = round(images * kb_img / 1024, 1)

    return {
        "target_approved_items": n_target,
        "is_projection": True,
        "projected_source_items": source_items,
        "projected_planned_edits": planned_needed,
        "projected_generated_tasks": tasks_needed,
        "gpu_sessions_diffusion": diffusion_sessions,
        "gpu_sessions_vlm_per_model": vlm_sessions_per_model,
        "gpu_sessions_vlm_3_models": vlm_sessions_per_model * 3,
        "human_review_hours": review_hours,
        "storage_footprint_mb": storage_mb,
        "cost_usd": 0,
        "cost_note": "free-tier only (local CPU + free Kaggle T4); no paid APIs/GPUs/datasets/annotation",
    }


def stop_go_gates() -> list[dict]:
    return [
        {"gate": "detectability_auc", "halt_if": f"edit-detectability AUC > {CONDITIONAL_MAX_AUC}",
         "conditional_if": f"AUC > {GO_MAX_AUC}", "confounded_if": f"AUC >= {ARTIFACT_CONFOUNDED_AUC}",
         "source": "certvic.validation.detectability_gate (canonical thresholds, not weakened)",
         "pilot_observed": 0.349},
        {"gate": "human_review_pass_rate", "halt_if": "approve_rate < 0.50 (collapsed)",
         "warn_if": "approve_rate < 0.70", "pilot_observed": round(0.0 + 91 / 103, 3)},
        {"gate": "controls", "halt_if": "absent-object control accuracy drops materially, OR "
         "spurious-flip specificity control fails when run"},
        {"gate": "parse_failures", "halt_if": "parse_failure_rate > 0.05", "warn_if": "> 0.02",
         "pilot_observed": 0.0, "note": "policy threshold (pilot had 0.0); not an existing gate being weakened"},
        {"gate": "result_ledger_hashing", "halt_if": "certvic.v7.result_ledger_audit cannot hash all "
         "artifacts or any hash mismatches"},
    ]


def build() -> dict:
    surv = _observed_survival()
    vlm_lat = _observed_vlm_latency()
    kb_img = _kb_per_image()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plans = {}
    for n in TARGETS:
        p = plan_for_target(n, surv, vlm_lat, kb_img)
        plans[f"main_{n}"] = p
        write_json(OUT_DIR / f"scale_plan_main_{n}.json", {
            "schema": "certvic.scale_plan.v1",
            "evidence_status": "SCALE_PROJECTION_NON_EVIDENCE", "paper_evidence": False,
            "observed_pilot": surv, "assumptions": _assumptions(vlm_lat, kb_img),
            "plan": p, "stop_go_gates": stop_go_gates(),
        })
        _write_commands(n, p)

    summary = {
        "schema": "certvic.scale_plan_summary.v1",
        "evidence_status": "SCALE_PROJECTION_NON_EVIDENCE", "paper_evidence": False,
        "note": "All per-target figures are PROJECTIONS from observed pilot survival rates, "
                "not results. Diffusion throughput and review pace are planning assumptions.",
        "observed_pilot_survival": surv,
        "observed_vlm_mean_latency_s": round(vlm_lat, 3),
        "assumptions": _assumptions(vlm_lat, kb_img),
        "targets": plans,
        "stop_go_gates": stop_go_gates(),
        "first_safe_scale_command": "python3 scripts/plan_scaled_main_run.py  # then run main_500 "
                                    "ONLY after the spurious-flip specificity control passes",
    }
    write_json(OUT_DIR / "scale_plan_summary.json", summary)
    DOC.write_text(_doc_md(summary), encoding="utf-8")
    return summary


def _assumptions(vlm_lat: float, kb_img: float) -> dict:
    return {
        "diffusion_sec_per_edit": DIFFUSION_SEC_PER_EDIT,
        "session_usable_hours": SESSION_USABLE_HOURS,
        "review_min_per_item_primary": REVIEW_MIN_PER_ITEM,
        "review_min_per_item_residual": RESIDUAL_REVIEW_MIN_PER_ITEM,
        "vlm_mean_latency_s_observed": round(vlm_lat, 3),
        "vlm_latency_safety_factor": VLM_LATENCY_SAFETY,
        "kb_per_image_observed": round(kb_img, 1),
        "control_items_fixed": CONTROL_ITEMS_FIXED,
    }


def _write_commands(n: int, plan: dict) -> None:
    d = CMD_DIR / f"main_{n}"
    d.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Kaggle shard plan template — main_{n} (PROJECTION, free-tier only)",
        "",
        f"Target reviewed-approved items: **{n}** (projection).",
        f"- Source candidates to select: ~{plan['projected_source_items']}",
        f"- Planned edits: ~{plan['projected_planned_edits']}",
        f"- Diffusion GPU sessions (T4, ~{SESSION_USABLE_HOURS}h each): **{plan['gpu_sessions_diffusion']}**",
        f"- VLM GPU sessions per model: **{plan['gpu_sessions_vlm_per_model']}** "
        f"(×3 models = {plan['gpu_sessions_vlm_3_models']})",
        f"- Human review: ~{plan['human_review_hours']} h · Storage: ~{plan['storage_footprint_mb']} MB · Cost: $0",
        "",
        "## Diffusion shards",
        f"Split ~{plan['projected_planned_edits']} edits across {plan['gpu_sessions_diffusion']} "
        "session(s); reuse scripts/split_edit_plan_by_shard.py and "
        "notebooks/kaggle/certvic_main200_diffusion_T4x2.ipynb.",
        "",
        "## VLM shards (per provider)",
        "Reuse notebooks/kaggle/certvic_main200_vlm_T4x2_AFTER_GATES.ipynb; one shard plan per "
        "provider in {qwen2_5_vl_7b, internvl_8b, llava_onevision_7b}.",
        "",
        "## Gate order (do not skip)",
        "1. detectability + quality gate (GO/conditional/confounded per detectability_gate)",
        "2. human visual review + residual-cue review",
        "3. spurious-flip specificity control MUST pass before treating scale as evidence",
        "4. result-ledger hash audit",
        "",
    ]
    (d / "shard_plan.md").write_text("\n".join(lines), encoding="utf-8")


def _doc_md(summary: dict) -> str:
    surv = summary["observed_pilot_survival"]
    a = summary["assumptions"]
    L: list[str] = []
    P = L.append
    P("# Scale Plan — main_500 to main_2000 (without breaking gates)")
    P("")
    P("**PROJECTION, NOT A RESULT** (`evidence_status = SCALE_PROJECTION_NON_EVIDENCE`). The "
      "n=91 pilot is strong but below CVPR main-claim scale. This plan projects the resources "
      "to reach larger reviewed-approved sets while preserving every validity gate. No GPU job "
      "is launched here; no threshold is weakened.")
    P("")
    P("## Observed pilot survival (from real artifacts — measured, not projected)")
    P("")
    P(f"- Source candidates → planned edits: {surv['planned']}/{surv['candidates']} "
      f"= {surv['plan_yield']:.3f}")
    P(f"- Planned edits → generated/quality-passed tasks: {surv['tasks']}/{surv['planned']} "
      f"= {surv['task_yield']:.3f}")
    P(f"- Tasks → human-approved: {surv['approved']}/{surv['tasks']} = {surv['approve_rate']:.3f}")
    P(f"- **Overall candidate → approved: {surv['approved']}/{surv['candidates']} "
      f"= {surv['overall']:.3f}**")
    P("")
    P("## Projected resources per target")
    P("")
    P("| target (approved) | source items | planned edits | diffusion sessions | VLM sessions ×3 | review h | storage MB | cost |")
    P("|---|---|---|---|---|---|---|---|")
    for key, p in summary["targets"].items():
        P(f"| {p['target_approved_items']} | {p['projected_source_items']} | "
          f"{p['projected_planned_edits']} | {p['gpu_sessions_diffusion']} | "
          f"{p['gpu_sessions_vlm_3_models']} | {p['human_review_hours']} | "
          f"{p['storage_footprint_mb']} | $0 |")
    P("")
    P("All rows are **projections** computed by `scripts/plan_scaled_main_run.py` from the "
      "observed survival rates above.")
    P("")
    P("## Planning assumptions (not measurements)")
    P("")
    P(f"- Diffusion: {a['diffusion_sec_per_edit']} s/edit on a free T4 (conservative, incl. load).")
    P(f"- Usable GPU hours per free session: {a['session_usable_hours']} h.")
    P(f"- VLM latency: {a['vlm_mean_latency_s_observed']} s/inference observed × "
      f"{a['vlm_latency_safety_factor']} safety.")
    P(f"- Review pace: {a['review_min_per_item_primary']} + {a['review_min_per_item_residual']} "
      "min/item (primary + residual-cue).")
    P(f"- Image size: {a['kb_per_image_observed']} KB/image observed; control held at "
      f"{a['control_items_fixed']} items.")
    P("")
    P("## Stop / go gates (scaling halts if any trips)")
    P("")
    for g in summary["stop_go_gates"]:
        extra = "; ".join(f"{k}: {v}" for k, v in g.items() if k not in {"gate"})
        P(f"- **{g['gate']}** — {extra}")
    P("")
    P("## Cost")
    P("")
    P("Zero. Local Mac/M4 CPU for planning + free Kaggle T4 for diffusion/VLM. No paid APIs, "
      "GPUs, datasets, annotation, or credits.")
    P("")
    P("## First safe scale command")
    P("")
    P("```bash")
    P("python3 scripts/plan_scaled_main_run.py")
    P("# Then execute main_500 ONLY after the spurious-flip specificity control passes and the")
    P("# result-ledger audit is clean. Do not use any projected number as a paper result.")
    P("```")
    P("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    summary = build()
    print(json.dumps({"targets": {k: v["gpu_sessions_diffusion"] for k, v in summary["targets"].items()},
                      "doc": str(DOC.relative_to(REPO))}, sort_keys=True))


if __name__ == "__main__":
    main()
