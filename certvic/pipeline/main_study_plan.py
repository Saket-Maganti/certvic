"""Main-study stage plan and gate sequence (V3 prompt 18).

Defines the full 200/1k/2k study as an ordered list of stages (with templated
commands, inputs, outputs, GPU flag, evidence status) and the gate sequence that
must pass between them. Planning only -- nothing is executed. Reuses the V3 scale
planner for runtime estimates.
"""

from __future__ import annotations

from certvic.pipeline.pilot_gate_check import GATE_STAGES
from certvic.planning.scale_planner import plan_scale

# Ordered study stages. Commands are templates ({root} = ADE20K root placeholder,
# {n} = scale). GPU stages are flagged; gate names mark where a gate must pass.
def stage_plan(scale: int, *, root_placeholder: str = "<ADE20K_ROOT>") -> list[dict]:
    n = scale
    return [
        {"id": "pilot_readiness", "name": "ADE20K readiness (dry-run inspection)", "gpu": False,
         "command": f"python3 -m certvic.data.pilot_readiness --config configs/real_pilot_ade20k.yaml --ade20k-root {root_placeholder} --dry-run",
         "inputs": [f"{root_placeholder} (local ADE20K)"], "outputs": ["readiness report"], "evidence_status": "READINESS_ONLY"},
        {"id": "manifests", "name": "Source + mask manifests", "gpu": False,
         "command": f"python3 -m certvic.data.ade20k_adapter --ade20k-root {root_placeholder} --out-sources data/manifests/ade20k_sources.jsonl --out-masks data/manifests/ade20k_masks.jsonl",
         "inputs": [f"{root_placeholder}"], "outputs": ["data/manifests/ade20k_sources.jsonl", "data/manifests/ade20k_masks.jsonl"], "evidence_status": "MANIFEST_ONLY"},
        {"id": "label_policy", "name": "Label policy report", "gpu": False,
         "command": "python3 -m certvic.data.label_policy_report --masks data/manifests/ade20k_masks.jsonl --policy configs/ade20k_label_policy.yaml --out data/results/label_policy_report.md",
         "inputs": ["data/manifests/ade20k_masks.jsonl"], "outputs": ["data/results/label_policy_report.md"], "evidence_status": "POLICY_ONLY"},
        {"id": "selection", "name": f"Pilot selection (target {n})", "gpu": False,
         "command": f"python3 -m certvic.data.select_pilot_items --config configs/real_pilot_ade20k.yaml --target {n} --out data/manifests/pilot_selection.jsonl",
         "inputs": ["data/manifests/ade20k_masks.jsonl"], "outputs": ["data/manifests/pilot_selection.jsonl"], "evidence_status": "CANDIDATE_ONLY", "gate_after": "before_edit_generation"},
        {"id": "edit_plan", "name": "Edit plan", "gpu": False,
         "command": "python3 -m certvic.edit.plan_edits --selection data/manifests/pilot_selection.jsonl --label-policy configs/ade20k_label_policy.yaml --out data/manifests/pilot_edit_plan.jsonl",
         "inputs": ["data/manifests/pilot_selection.jsonl"], "outputs": ["data/manifests/pilot_edit_plan.jsonl"], "evidence_status": "PLANNED_ONLY"},
        {"id": "diffusion_queue", "name": "Diffusion job queue (shard + resume)", "gpu": False,
         "command": "python3 -m certvic.edit.job_queue build --edit-plan data/manifests/pilot_edit_plan.jsonl --out data/manifests/diffusion_job_queue.jsonl --shards 4",
         "inputs": ["data/manifests/pilot_edit_plan.jsonl"], "outputs": ["data/manifests/diffusion_job_queue.jsonl"], "evidence_status": "JOB_PLANNED_ONLY"},
        {"id": "edit_generation", "name": f"Photorealistic edit generation ({n})", "gpu": True,
         "command": f"python3 -m certvic.edit.generate_edits --edit-plan data/manifests/pilot_edit_plan.jsonl --out-dir data/edits/ade20k_pilot --out-manifest data/manifests/pilot_generated_edits.jsonl --rejected-out data/manifests/pilot_generated_edits_rejected.jsonl --summary-out data/results/edit_generation_summary.json --max-items {n} --mode diffusers_inpaint --seed 0",
         "inputs": ["data/manifests/pilot_edit_plan.jsonl", f"{root_placeholder}", "<WEIGHTS_DIR>"], "outputs": ["data/edits/ade20k_pilot/", "data/manifests/pilot_generated_edits.jsonl"], "evidence_status": "GENERATED_EDIT_ONLY"},
        {"id": "quality_gates", "name": "Edit quality report + detectability", "gpu": False,
         "command": "python3 -m certvic.validation.edit_detectability --tasks data/manifests/pilot_generated_edits.jsonl --out-dir data/results/edit_detectability",
         "inputs": ["data/manifests/pilot_generated_edits.jsonl"], "outputs": ["data/results/edit_detectability/"], "evidence_status": "QUALITY_ONLY", "gate_after": "before_visual_review"},
        {"id": "visual_review", "name": "Human review (batches + IAA + adjudicate)", "gpu": False,
         "command": "python3 -m certvic.validation.review_batches --tasks data/manifests/pilot_eval_tasks_tiny.jsonl --out-dir data/annotations/review_batches --reviewers reviewer_a reviewer_b --overlap-rate 0.2",
         "inputs": ["data/manifests/pilot_eval_tasks_tiny.jsonl"], "outputs": ["data/annotations/review_batches/", "data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl"], "evidence_status": "HUMAN_REVIEWED_NON_EVIDENCE", "gate_after": "before_vlm"},
        {"id": "vlm_preflight", "name": "Open-local VLM preflight", "gpu": True,
         "command": "python3 -m certvic.eval.vlm_preflight --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --provider qwen2_5_vl_7b --check-gpu",
         "inputs": ["data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl"], "outputs": ["preflight report"], "evidence_status": "PREFLIGHT_ONLY"},
        {"id": "vlm_inference", "name": f"VLM inference (matrix, {n}, resumable)", "gpu": True,
         "command": "python3 -m certvic.eval.run_matrix_planner --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --providers qwen2_5_vl_7b internvl_8b llava_onevision_7b --out-dir data/results/model_run_matrix --max-items {n} --num-shards 4".replace("{n}", str(n)),
         "inputs": ["data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl", "<MODEL_WEIGHTS>"], "outputs": ["data/predictions/"], "evidence_status": "REAL_EVIDENCE"},
        {"id": "scoring", "name": "Scoring + power + triage", "gpu": False,
         "command": "python3 -m certvic.metrics.score_predictions --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --preds data/predictions/run.jsonl --out-scores data/results/pair_scores.jsonl --out-summary data/results/summary.json",
         "inputs": ["data/predictions/"], "outputs": ["data/results/pair_scores.jsonl", "data/results/summary.json"], "evidence_status": "REAL_EVIDENCE", "gate_after": "before_claims"},
        {"id": "certification", "name": "Anytime-valid certification + cluster diagnostics", "gpu": False,
         "command": "python3 -m certvic.metrics.cluster_diagnostics --scores data/results/pair_scores.jsonl --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/results/cluster_diagnostics",
         "inputs": ["data/results/pair_scores.jsonl"], "outputs": ["data/results/cluster_diagnostics/"], "evidence_status": "REAL_EVIDENCE"},
        {"id": "report", "name": "Paper report + result injection", "gpu": False,
         "command": "python3 -m certvic.reporting.build_v2_report --scores data/results/pair_scores.jsonl --preds data/predictions/run.jsonl --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/results/v2_report",
         "inputs": ["data/results/pair_scores.jsonl"], "outputs": ["data/results/v2_report/"], "evidence_status": "REAL_EVIDENCE", "gate_after": "before_release"},
        {"id": "release", "name": "Recipe-first artifact + privacy audit", "gpu": False,
         "command": "python3 -m certvic.release.build_artifact --config configs/release_recipe.yaml --out-dir release/certvic_recipe_artifact",
         "inputs": ["data/manifests/"], "outputs": ["release/certvic_recipe_artifact/"], "evidence_status": "RELEASE_RECIPE"},
    ]


def gate_sequence() -> list[dict]:
    descriptions = {
        "before_edit_generation": "selection meets target, label policy clean, sources eligible",
        "before_visual_review": "edits generated, quality gates pass, detectability acceptable",
        "before_vlm": "reviewed tasks exist with adequate IAA; only reviewed items proceed",
        "before_claims": "real open-local predictions scored; no high parse failure / control flip",
        "before_release": "certified or honest-null report; privacy audit clean; numbers traced",
    }
    seq = [{"gate": g, "command": f"python3 -m certvic.pipeline.pilot_gate_check --stage {g} --config configs/real_pilot_ade20k.yaml", "checks": descriptions.get(g, "")} for g in GATE_STAGES]
    # Cross-cutting gates that bracket the whole study.
    seq.insert(0, {"gate": "pre_run_master_audit", "command": "python3 -m certvic.v2.pre_run_master_audit", "checks": "all systems green before any real work"})
    seq.append({"gate": "security_privacy_audit", "command": "python3 -m certvic.security.release_privacy_audit --root . --release-dir release/certvic_recipe_artifact --out docs/SECURITY_PRIVACY_AUDIT.md", "checks": "no private paths / secrets / pixels leak"})
    seq.append({"gate": "final_pre_real_run_audit", "command": "python3 -m certvic.v3.final_pre_real_run_audit", "checks": "V3 final gate (built in prompt 19)"})
    return seq


def build_main_study_plan(scale: int) -> dict:
    stages = stage_plan(scale)
    gates = gate_sequence()
    runtime = plan_scale(scale)
    required_inputs = sorted({i for s in stages for i in s["inputs"] if "<" in i or "local" in i.lower()})
    expected_outputs = sorted({o for s in stages for o in s["outputs"]})
    return {
        "plan": "certvic_main_study",
        "scale": scale,
        "n_stages": len(stages),
        "n_gpu_stages": sum(1 for s in stages if s["gpu"]),
        "stages": stages,
        "gate_sequence": gates,
        "required_inputs": required_inputs,
        "expected_outputs": expected_outputs,
        "runtime_estimate": {
            "total_gpu_hours": runtime["gpu"]["total_gpu_hours"],
            "wall_clock_weeks_under_quota": runtime["gpu"]["wall_clock_weeks_under_quota"],
            "human_hours": runtime["human"]["total_human_hours"],
            "storage_gb": runtime["storage_gb"],
            "bottleneck": runtime["bottleneck"],
        },
        "executed": False,
        "vlm_inference_run": False,
        "downloads_attempted": False,
        "evidence_claims_made": False,
    }
