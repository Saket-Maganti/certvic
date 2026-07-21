# V3 Prompt 07 — Human Review Operations Report

## Goal

Scale the visual review process: reviewer batching, overlap for IAA, progress
tracking, disagreement resolution, adjudication.

## What was built

- `certvic/validation/review_batches.py` — stratified (`task_family`×`edit_type`) balanced batching with an overlap subset assigned to all reviewers for IAA; writes per-reviewer CSV sheets (standard decision columns) + `assignment_manifest.json` with a workload/wall-clock estimate.
- `certvic/validation/review_progress.py` — per-reviewer assigned/rated/missing counts, blank-field detection, overlap disagreements per field, and IAA (reuses `certvic.validation.iaa.field_iaa`).
- `certvic/validation/adjudicate_review.py` — majority-vote adjudication to one row per item with `unanimous` / `majority` / `tie_needs_human` status and flagged disagreement fields.

## Tests

`tests/test_v3_human_review_ops.py` — 8 tests: balanced batching with overlap (assignment accounting + CSV headers + workload), zero overlap for a single reviewer, invalid overlap-rate rejection, per-reviewer load balance (≤1 apart), progress completion + missing detection, overlap disagreement + IAA detection, adjudication unanimous/majority/tie resolution + CSV output, and a no-paid/no-heavy-import guard.

## Verification

- `python3 -m pytest -q` — full suite green (326 passed; was 318).
- CLI smoke: batched 20 tasks across 2 reviewers (4 overlap, balanced 12/12, ~6 min parallel wall-clock); progress on unfilled batches (0% complete, 24 assigned); adjudicated a 24-row combined ratings file into 20 unanimous items.

## Evidence / cost discipline

No paid annotation services, no model outputs in sheets, no GPU/downloads. All
results carry `paid_annotation_services=false` / `evidence_claims_made=false`. No
heavy imports.

## Status

**PASSED.**

## Remaining blockers

None. Adjudicated keep-lists feed the existing `certvic.data.apply_visual_review`
flow unchanged once real reviewers fill the sheets.
