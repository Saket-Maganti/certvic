#!/usr/bin/env bash
set -euo pipefail

# CertVIC V4 real-run commands: tiny_pilot
# Generated for later execution; generation itself executed nothing.
# Review required inputs and run gates between stages before continuing.
# Planned command artifacts are non-evidence.

# [v3_gate] Confirm the V3 final gate is green
# CPU-only audit; creates no evidence.
python3 -m certvic.v3.final_pre_real_run_audit --out docs/V3_FINAL_PRE_REAL_RUN_AUDIT_REPORT.md --json-out data/results/v3_final_pre_real_run_audit.json

# [study_plan] Render the main-study dry-run plan
# Command planning only; no GPU/VLM execution.
python3 -m certvic.pipeline.main_study_dry_run --scale 20 --out-dir data/results/main_study_dry_run_20

# [tiny_pilot_dry_run] Inspect ADE20K and build local dry-run state
# Safety flag `--dry-run` must pass before running the non-dry-run command.
python3 -m certvic.pipeline.run_tiny_pilot --config configs/real_pilot_ade20k.yaml --ade20k-root <ADE20K_ROOT> --out-dir data/results/tiny_real_pilot --max-items 20 --seed 0 --dry-run

# [tiny_pilot_execute] Run the bounded pilot pipeline
# Resume by re-running; stage_status.json skips completed stages unless `--force`.
python3 -m certvic.pipeline.run_tiny_pilot --config configs/real_pilot_ade20k.yaml --ade20k-root <ADE20K_ROOT> --out-dir data/results/tiny_real_pilot --max-items 20 --seed 0

# [diffusion_queue] Build the resumable diffusion queue
# Queue building only.
python3 -m certvic.edit.job_queue build --edit-plan data/results/tiny_real_pilot/pilot_edit_plan.jsonl --out data/results/tiny_real_pilot/diffusion_job_queue.jsonl --shards 2

# [diffusion_resume_status] Compute diffusion resume worklist
# Use this before each free-GPU session.
python3 -m certvic.edit.diffusion_resume --queue data/results/tiny_real_pilot/diffusion_job_queue.jsonl --generated data/results/tiny_real_pilot/pilot_generated_edits.jsonl --out data/results/tiny_real_pilot/diffusion_resume.jsonl

# [gpu_edit_generation] Generate photorealistic edits on free GPU
# Runs only when the user executes it on free GPU with local/cached weights.
python3 -m certvic.edit.engines --edit-plan data/results/tiny_real_pilot/pilot_edit_plan.jsonl --out-dir data/edits/tiny_real_pilot --out-manifest data/results/tiny_real_pilot/pilot_generated_edits.jsonl --rejected-out data/results/tiny_real_pilot/pilot_generated_rejected.jsonl --summary-out data/results/tiny_real_pilot/pilot_generation_summary.json --engine diffusers_inpaint_optional --max-items 20 --seed 0 --resume --fail-fast

# [quality_gate] Build quality and detectability reports
# Quality gates do not create evidence claims.
python3 -m certvic.edit.quality_report --generated-manifest data/results/tiny_real_pilot/pilot_generated_edits.jsonl --rejected data/results/tiny_real_pilot/pilot_generated_rejected.jsonl --out-dir data/results/tiny_real_pilot/tiny_edit_quality_report

# [review_batches] Create human review batches
# Reviewer IDs are placeholders; paid annotation is not required.
python3 -m certvic.validation.review_batches --tasks data/results/tiny_real_pilot/pilot_eval_tasks_tiny.jsonl --out-dir data/annotations/tiny_real_pilot_review_batches --reviewers reviewer_a reviewer_b --overlap-rate 0.2

# [model_matrix] Plan the open-local VLM matrix
# Planning only; no inference.
python3 -m certvic.eval.run_matrix_planner --tasks data/results/tiny_real_pilot/pilot_eval_tasks_reviewed.jsonl --providers qwen2_5_vl_7b internvl_8b llava_onevision_7b --out-dir data/results/tiny_real_pilot/model_run_matrix --config configs/kaggle_open_vlm.yaml --pred-root data/predictions/tiny_real_pilot --max-items 20 --num-shards 2

# [vlm_dry_run_one_shard] Dry-run one VLM shard before real inference
# Safety flags included; dry-run must pass before dropping `--dry-run`.
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/results/tiny_real_pilot/pilot_eval_tasks_reviewed.jsonl --out data/predictions/tiny_real_pilot/qwen2_5_vl_7b_shard0.jsonl --provider qwen2_5_vl_7b --run-id tiny_pilot_qwen2_5_vl_7b_shard0 --max-items 20 --shard-index 0 --num-shards 2 --dry-run --strict-leakage --fail-fast

# [vlm_execute_one_shard] Execute one evidence-eligible open-local VLM shard
# Resume is default because completed task keys are skipped by the runner.
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/results/tiny_real_pilot/pilot_eval_tasks_reviewed.jsonl --out data/predictions/tiny_real_pilot/qwen2_5_vl_7b_shard0.jsonl --provider qwen2_5_vl_7b --run-id tiny_pilot_qwen2_5_vl_7b_shard0 --max-items 20 --shard-index 0 --num-shards 2 --strict-leakage --evidence-run --fail-fast

# [score_predictions] Score merged predictions
# Only valid after real open-local predictions exist.
python3 -m certvic.metrics.score_predictions --tasks data/results/tiny_real_pilot/pilot_eval_tasks_reviewed.jsonl --preds data/predictions/tiny_real_pilot/merged.jsonl --out-scores data/results/tiny_real_pilot/pair_scores.jsonl --out-summary data/results/tiny_real_pilot/score_summary.json

# [triage_outputs] Triage parse/output quality
# Inspect before trusting gaps.
python3 -m certvic.eval.output_triage --preds data/predictions/tiny_real_pilot/merged.jsonl --tasks data/results/tiny_real_pilot/pilot_eval_tasks_reviewed.jsonl --out-dir data/results/tiny_real_pilot/output_triage

# [build_report] Build report artifacts without paper-number injection
# Paper claims still require claim gates and future result lockfiles.
python3 -m certvic.reporting.build_v2_report --tasks data/results/tiny_real_pilot/pilot_eval_tasks_reviewed.jsonl --preds data/predictions/tiny_real_pilot/merged.jsonl --scores data/results/tiny_real_pilot/pair_scores.jsonl --out-dir data/results/tiny_real_pilot/v2_report
