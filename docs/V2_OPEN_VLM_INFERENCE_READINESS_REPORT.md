# V2 Open-Local VLM Inference Readiness Report

Date: 2026-06-22
Prompt: `05_V2_OPEN_VLM_INFERENCE_READINESS.md`

## What was added

- `certvic/providers/registry.py` — `PROVIDER_METADATA` (model_family,
  expected_gpu_memory_gb, supports_4bit, supports_batching, tested_status,
  cost_status, provider_type), `provider_metadata(name)`,
  `is_evidence_eligible_provider(name)` (open-local only; mock/baseline/paid
  excluded).
- `certvic/eval/vlm_preflight.py` — preflight CLI: manifest/images exist,
  provider importability, optional deps, optional GPU (`--check-gpu`), memory
  estimate, output writable, zero-cost policy. No inference, no downloads.
- `certvic/eval/run_eval.py` — writes provider-metadata + environment sidecars;
  `evidence_run=True` (`--evidence-run`) blocks mock providers and unreviewed
  tasks before any model load.
- `configs/tiny_reviewed_eval.yaml` (added in Prompt 13), Kaggle notebook update.

## Tests

- `tests/test_v2_open_vlm_readiness.py` — 7 tests (metadata + eligibility,
  environment summary, preflight blocks missing manifest, preflight structural
  pass, runner sidecars, evidence-run blocks mock, evidence-run blocks unreviewed).
  Full suite: **178 passed** (was 171).

## Blockers before evidence

- Real VLM inference requires free Kaggle/Colab GPU + transformers/torch (not in
  the test env). Adapters remain scaffolds (tested_status=adapter_scaffold).

## Status: PASS. Next: `08_V2_RESULTS_REPORTING_FIGURES_TABLES.md`.
