# V3 Prompt 18 — Main Study Orchestrator Dry Run Report

## Goal

Plan the full 200/1k/2k study without executing GPU/VLM jobs.

## What was built

- `certvic/pipeline/main_study_plan.py` — 15-stage ordered plan (readiness → manifests → label policy → selection → edit plan → diffusion queue → edit generation → quality+detectability → human review → VLM preflight → VLM inference → scoring → certification+cluster → report → release), each with templated command, inputs, outputs, GPU flag, evidence status, and gate-after marker; `gate_sequence()` bracketed by `pre_run_master_audit` and the security + final audits; runtime via the scale planner.
- `certvic/pipeline/main_study_dry_run.py` — writes `stage_plan.json`, `commands.sh` (gates inlined), `required_inputs.md`, `expected_outputs.md`, `gate_sequence.md`, `runtime_estimates.md`, `report.md`. No execution.

## Tests

`tests/test_v3_main_study_dry_run.py` — 7 tests: stage ordering + gates attached; plan scale + non-execution flags; required inputs include dataset root + weights; gate sequence bracketed by audits; dry-run writes exactly 7 artifacts with gates inlined in commands.sh; no-execution markers; no heavy imports.

## Verification

- `python3 -m pytest -q` — full suite green (425 passed; was 418).
- CLI smoke at scale 200 and 2000: 15 stages (3 GPU), bottleneck `free_gpu_quota`, all 7 artifacts written, `executed: false`.

## Evidence / cost discipline

Planning only — no GPU, no VLM inference, no downloads, no paid services.
`executed=false`, `vlm_inference_run=false`, `downloads_attempted=false`,
`evidence_claims_made=false`. No heavy imports.

## Status

**PASSED.**

## Remaining blockers

None. The plan references `certvic.v3.final_pre_real_run_audit` (built in prompt
19) in its closing gate.
