#!/usr/bin/env bash
set -euo pipefail
# CertVIC main study plan (scale 2000). DRY-RUN PLAN -- review before running.
# Set ADE20K_ROOT and weights dirs first; gates must pass between stages.

# Pre-run audit
python3 -m certvic.v2.pre_run_master_audit

# [pilot_readiness] ADE20K readiness (dry-run inspection)
python3 -m certvic.data.pilot_readiness --config configs/real_pilot_ade20k.yaml --ade20k-root <ADE20K_ROOT> --dry-run

# [manifests] Source + mask manifests
python3 -m certvic.data.ade20k_adapter --ade20k-root <ADE20K_ROOT> --out-sources data/manifests/ade20k_sources.jsonl --out-masks data/manifests/ade20k_masks.jsonl

# [label_policy] Label policy report
python3 -m certvic.data.label_policy_report --masks data/manifests/ade20k_masks.jsonl --policy configs/ade20k_label_policy.yaml --out data/results/label_policy_report.md

# [selection] Pilot selection (target 2000)
python3 -m certvic.data.select_pilot_items --config configs/real_pilot_ade20k.yaml --target 2000 --out data/manifests/pilot_selection.jsonl
# GATE: before_edit_generation
python3 -m certvic.pipeline.pilot_gate_check --stage before_edit_generation --config configs/real_pilot_ade20k.yaml

# [edit_plan] Edit plan
python3 -m certvic.edit.plan_edits --selection data/manifests/pilot_selection.jsonl --label-policy configs/ade20k_label_policy.yaml --out data/manifests/pilot_edit_plan.jsonl

# [diffusion_queue] Diffusion job queue (shard + resume)
python3 -m certvic.edit.job_queue build --edit-plan data/manifests/pilot_edit_plan.jsonl --out data/manifests/diffusion_job_queue.jsonl --shards 4

# [edit_generation] Photorealistic edit generation (2000)  (GPU)
python3 -m certvic.edit.generate_edits --edit-plan data/manifests/pilot_edit_plan.jsonl --out-dir data/edits/ade20k_pilot --out-manifest data/manifests/pilot_generated_edits.jsonl --rejected-out data/manifests/pilot_generated_edits_rejected.jsonl --summary-out data/results/edit_generation_summary.json --max-items 2000 --mode diffusers_inpaint --seed 0

# [quality_gates] Edit quality report + detectability
python3 -m certvic.validation.edit_detectability --tasks data/manifests/pilot_generated_edits.jsonl --out-dir data/results/edit_detectability
# GATE: before_visual_review
python3 -m certvic.pipeline.pilot_gate_check --stage before_visual_review --config configs/real_pilot_ade20k.yaml

# [visual_review] Human review (batches + IAA + adjudicate)
python3 -m certvic.validation.review_batches --tasks data/manifests/pilot_eval_tasks_tiny.jsonl --out-dir data/annotations/review_batches --reviewers reviewer_a reviewer_b --overlap-rate 0.2
# GATE: before_vlm
python3 -m certvic.pipeline.pilot_gate_check --stage before_vlm --config configs/real_pilot_ade20k.yaml

# [vlm_preflight] Open-local VLM preflight  (GPU)
python3 -m certvic.eval.vlm_preflight --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --provider qwen2_5_vl_7b --check-gpu

# [vlm_inference] VLM inference (matrix, 2000, resumable)  (GPU)
python3 -m certvic.eval.run_matrix_planner --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --providers qwen2_5_vl_7b internvl_8b llava_onevision_7b --out-dir data/results/model_run_matrix --max-items 2000 --num-shards 4

# [scoring] Scoring + power + triage
python3 -m certvic.metrics.score_predictions --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --preds data/predictions/run.jsonl --out-scores data/results/pair_scores.jsonl --out-summary data/results/summary.json
# GATE: before_claims
python3 -m certvic.pipeline.pilot_gate_check --stage before_claims --config configs/real_pilot_ade20k.yaml

# [certification] Anytime-valid certification + cluster diagnostics
python3 -m certvic.metrics.cluster_diagnostics --scores data/results/pair_scores.jsonl --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/results/cluster_diagnostics

# [report] Paper report + result injection
python3 -m certvic.reporting.build_v2_report --scores data/results/pair_scores.jsonl --preds data/predictions/run.jsonl --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/results/v2_report
# GATE: before_release
python3 -m certvic.pipeline.pilot_gate_check --stage before_release --config configs/real_pilot_ade20k.yaml

# [release] Recipe-first artifact + privacy audit
python3 -m certvic.release.build_artifact --config configs/release_recipe.yaml --out-dir release/certvic_recipe_artifact

# Final audits
python3 -m certvic.security.release_privacy_audit --root . --release-dir release/certvic_recipe_artifact --out docs/SECURITY_PRIVACY_AUDIT.md
python3 -m certvic.v3.final_pre_real_run_audit
