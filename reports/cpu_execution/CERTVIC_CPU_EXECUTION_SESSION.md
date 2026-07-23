# CertVIC CPU Execution Session

Generated: `2026-07-23T06:30:31+00:00`

This session executed only CPU-safe commands with offline flags and at most four CPU threads. No GPU inference, diffusion generation, model loading, predictions, or human decisions were fabricated.

## Counts

- `ALREADY_VALID`: 8
- `BLOCKED_BY_EXTERNAL_BYTES`: 3
- `BLOCKED_BY_GENUINE_HUMAN_REVIEW`: 1
- `BLOCKED_BY_GPU_OUTPUT`: 3
- `BLOCKED_BY_UPSTREAM_GATE`: 6
- `COMPLETED`: 4
- `FAILED_LOCAL_REPAIR_REQUIRED`: 0

## Completed or already valid

- `baseline_validation` — COMPLETED (124.429 s)
- `repository_kaggle_bundles` — ALREADY_VALID (0.0 s)
- `wheelhouse_preflight` — ALREADY_VALID (0.0 s)
- `snapshot_preflight_qwen` — ALREADY_VALID (0.0 s)
- `snapshot_preflight_internvl` — ALREADY_VALID (0.0 s)
- `snapshot_preflight_llava` — ALREADY_VALID (0.0 s)
- `data_license_overlap_inventory` — ALREADY_VALID (0.0 s)
- `runtime_upload_map` — ALREADY_VALID (0.0 s)
- `paper_evidence_and_release` — ALREADY_VALID (0.0 s)
- `refresh_release_lineage` — COMPLETED (0.1 s)
- `register_repository_bundles` — COMPLETED (0.084 s)
- `final_registry_verification` — COMPLETED (0.081 s)

## Resumable blockers

- `first_gpu_wave_return_validation` — BLOCKED_BY_GPU_OUTPUT: missing inputs: data/runtime/00B_qwen2_5_vl_7b_snapshot_bundle.zip, data/runtime/00B_internvl_8b_snapshot_bundle.zip, data/runtime/00B_llava_onevision_7b_snapshot_bundle.zip. Next: `place all four unchanged return ZIPs in data/runtime and run python3 scripts/run_all_cpu_workflows.py --resume`
- `real_smoke_preparation` — BLOCKED_BY_EXTERNAL_BYTES: missing inputs: local_inputs/smoke/real_smoke_tasks.jsonl. Next: `python3 -m certvic.cvpr.smoke_input_builder --task-manifest local_inputs/smoke/real_smoke_tasks.jsonl --output kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip`
- `pre_smoke_permissions` — BLOCKED_BY_UPSTREAM_GATE: unmet prerequisites: first_gpu_wave_return_validation, real_smoke_preparation. Next: `python3 -m certvic.cvpr.pre_smoke_packager --config <INPUTS_JSON>`
- `confirmatory_source_preparation` — BLOCKED_BY_EXTERNAL_BYTES: missing inputs: local_inputs/confirmatory/source_manifest.jsonl. Next: `python3 -m certvic.cvpr.confirmatory_input_builder --config <INPUT_CONFIG_JSON>`
- `generated_edit_cpu_qa` — BLOCKED_BY_GPU_OUTPUT: unmet prerequisites: confirmatory_source_preparation. Next: `download and validate confirmatory_generation_return.zip, then resume`
- `review_packet_preparation` — BLOCKED_BY_UPSTREAM_GATE: unmet prerequisites: generated_edit_cpu_qa. Next: `generate blinded review packet and hand to genuine reviewers`
- `exact_selection` — BLOCKED_BY_GENUINE_HUMAN_REVIEW: unmet prerequisites: review_packet_preparation. Next: `validate genuine finalized inclusion inputs, then resume`
- `detectability_gate` — BLOCKED_BY_UPSTREAM_GATE: unmet prerequisites: exact_selection. Next: `run grouped detectability only on the genuine selected set`
- `freeze_and_permissions` — BLOCKED_BY_UPSTREAM_GATE: unmet prerequisites: detectability_gate. Next: `resume only after every real gate exists and validates`
- `process_kaggle_returns` — BLOCKED_BY_GPU_OUTPUT: unmet prerequisites: freeze_and_permissions. Next: `place unchanged return ZIPs in canonical local_inputs/provider_returns path and resume`
- `statistical_analysis` — BLOCKED_BY_UPSTREAM_GATE: unmet prerequisites: process_kaggle_returns. Next: `run canonical after-runs analysis after import validation`
- `main_cpu_preparation` — BLOCKED_BY_UPSTREAM_GATE: unmet prerequisites: statistical_analysis. Next: `continue only if canonical confirmatory decision authorizes Main`
- `coco_cpu_preparation` — BLOCKED_BY_EXTERNAL_BYTES: missing inputs: local_inputs/coco/instances_val2017.json. Next: `provision licensed COCO validation assets and source manifest, then resume`

`paper_evidence=false`

`genuine human_reviewed=true count=0`

