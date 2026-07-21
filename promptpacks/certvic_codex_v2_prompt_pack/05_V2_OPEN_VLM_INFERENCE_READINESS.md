# CertVIC Codex V2 Prompt 05 — Open-Local VLM Inference Readiness

Do not use paid APIs. Do not use paid cloud. Do not run large inference in tests. Do not make evidence claims.

## Goal

Prepare robust open-local VLM inference for reviewed tasks on free compute.

## Tasks

1. Harden provider registry:
   - no paid providers
   - open-local providers disabled unless selected
   - mock providers remain for tests
   - free-tier reference remains disabled/non-core

2. Add provider metadata:
   - model_family
   - expected_gpu_memory_gb
   - supports_4bit
   - supports_batching
   - tested_status
   - cost_status = zero_cost_open_local

3. Improve open VLM adapters:
   - lazy imports
   - no downloads unless user cache/setup permits
   - clear missing dependency errors
   - clear missing model/cache errors
   - max_new_tokens low by default
   - temperature 0.0

4. Add preflight command:

   `python3 -m certvic.eval.vlm_preflight --provider qwen2_5_vl_7b --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/results/vlm_preflight_qwen.json`

   Checks:
   - task manifest exists
   - images exist
   - provider importability
   - optional dependencies
   - GPU availability if requested
   - memory estimate
   - output path writable
   - zero-cost policy
   - no paid services

5. Add config:
   - `configs/tiny_reviewed_eval.yaml`

6. Strengthen runner:
   - write provider metadata sidecar
   - write environment summary
   - enforce reviewed task status for real providers unless override flag
   - block mock provider from evidence-eligible runs

7. Add tests:
   - `tests/test_v2_open_vlm_readiness.py`

8. Update:
   - `notebooks/kaggle/04_run_open_vlms.md`
   - `docs/REPRO.md`

9. Create:
   - `docs/V2_OPEN_VLM_INFERENCE_READINESS_REPORT.md`

10. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, commands added, whether open-VLM readiness passed, and next prompt: `06_V2_BASELINES_AND_ABLATIONS_UPGRADE.md`.
