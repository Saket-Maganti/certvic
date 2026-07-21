# V2 Tiny Eval + Scoring Report

Date: 2026-06-22
Prompt: `13_V2_OPEN_MODEL_TINY_EVAL_AND_SCORING.md`

## What was added

- `certvic/pipeline/run_tiny_eval.py` — preflight -> run_eval -> score ->
  report_metrics (with certification gate) -> build_v2_report (best effort) ->
  audit. CLI: `python3 -m certvic.pipeline.run_tiny_eval`.
- `configs/tiny_reviewed_eval.yaml`.
- `docs/TINY_EVAL_RUNBOOK.md`.

## Enforcement

Tasks must be HUMAN_REVIEWED_NON_EVIDENCE or stronger; mock providers blocked for
the evidence path (`--allow-mock-smoke` for a non-evidence plumbing run); paid
providers blocked; max_items required unless --allow-full-run; resume on; raw
outputs preserved. The certification policy + anytime-valid CS gate certified
claims; smoke/mock data can never be certified.

## Tests

- `tests/test_v2_tiny_eval_pipeline.py` — 5 tests (max_items required, mock
  blocked for evidence, unreviewed blocked, mock-smoke completes non-evidence,
  certification block present). Full suite: **171 passed** (was 166).

## Status: PASS. Next: `05_V2_OPEN_VLM_INFERENCE_READINESS.md`.
