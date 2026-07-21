# V2 Tiny Real Pilot Orchestrator Report

Date: 2026-06-22
Prompt: `12_V2_END_TO_END_TINY_REAL_PILOT.md`

## What was added

- `certvic/pipeline/__init__.py`, `certvic/pipeline/run_tiny_pilot.py` — chains
  the full edit-side pipeline (11 stages) with per-stage resume, dry-run, command
  log, and zero-cost audit. CLI: `python3 -m certvic.pipeline.run_tiny_pilot`.
- `docs/TINY_REAL_PILOT_RUNBOOK.md`.

## Stages

pilot_readiness, manifests, label_policy_report, selection, edit_planning,
task_preview, pilot_plan_report, edit_generation, quality_report,
materialization, visual_review_sheet. `--dry-run` stops after label_policy_report
and prints remaining commands.

## Guarantees

No downloads, no GPU, no VLM inference, no evidence claims; PIPELINE_NON_EVIDENCE.

## Tests

- `tests/test_v2_tiny_pilot_orchestrator.py` — 3 tests using a synthetic ADE20K
  layout: dry-run lists next commands + writes audit; full pipeline runs all 11
  stages with zero failures and produces generated edits + review sheet; resume
  reuses completed stages. Full suite: **166 passed** (was 163).

## Blockers before evidence

- Requires a user-supplied local ADE20K root (tests use a synthetic fixture).

## Status: PASS. Next: `13_V2_OPEN_MODEL_TINY_EVAL_AND_SCORING.md`.
