# CertVIC V1.5 Tiny Edit Generation + Quality Report

Date: 2026-06-21

Verdict: PASS for tiny real edit generation and quality-gate readiness.

This is not a VLM run and not an evidence run. V1.5 can generate a tiny local
batch of simple edited images from `pilot_edit_plan.jsonl`, run quality gates,
write review reports, and materialize non-evidence task rows. It does not use
paid APIs, paid cloud, automatic downloads, VLM inference, or paper claims.

## What Changed

- Added `python3 -m certvic.edit.generate_edits`.
- Added deterministic simple local edit generation for:
  - `remove`
  - `occlude`
  - `displace`
  - `control_irrelevant`
- Added generated edit manifests with:
  - original/edited image paths
  - mask source info
  - planned and actual params
  - edited image SHA256
  - `generation_status`
  - `quality_gate_status`
  - `evidence_status=GENERATED_EDIT_ONLY`
  - `zero_cost=true`
- Added rejected generation sidecar rows for infeasible items.
- Added optional `diffusers_inpaint` mode checks, disabled by default and
  import-safe.
- Strengthened quality gates for:
  - mask-area fraction
  - bbox validity
  - inside-mask change fraction
  - outside-mask change fraction
  - edit-specific allowed-region changes
  - image-size match
  - edited file/hash presence
  - changed-region non-emptiness
  - simple artifact warnings
- Added `python3 -m certvic.edit.quality_report`.
- Added `python3 -m certvic.data.materialize_tasks`.
- Updated claim gates so `GENERATED_EDIT_ONLY` and
  `EDIT_READY_NON_EVIDENCE` cannot support certified claims.

## Tests Run

```bash
python3 -m pytest -q
```

Result: 110 passed.

Focused V1.5 fake-fixture coverage is in:

```text
tests/test_v1_5_tiny_edit_generation.py
```

## Commands Added

Tiny edit generation:

```bash
python3 -m certvic.edit.generate_edits \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --out-dir data/edits/ade20k_tiny_pilot \
  --out-manifest data/manifests/pilot_generated_edits.jsonl \
  --rejected-out data/manifests/pilot_generated_edits_rejected.jsonl \
  --summary-out data/results/tiny_edit_generation_summary.json \
  --max-items 20 \
  --mode simple \
  --seed 0
```

Quality report:

```bash
python3 -m certvic.edit.quality_report \
  --generated-manifest data/manifests/pilot_generated_edits.jsonl \
  --rejected data/manifests/pilot_generated_edits_rejected.jsonl \
  --out-dir data/results/tiny_edit_quality_report
```

Materialize tiny non-evidence tasks:

```bash
python3 -m certvic.data.materialize_tasks \
  --task-preview data/manifests/pilot_task_preview.jsonl \
  --generated-edits data/manifests/pilot_generated_edits.jsonl \
  --out data/manifests/pilot_eval_tasks_tiny.jsonl \
  --summary-out data/manifests/pilot_eval_tasks_tiny_summary.json
```

## Fake Fixture Validation

The V1.5 tests use tiny generated local images and masks only. They verify:

- simple `remove` writes an edited image
- simple `occlude` writes an edited image
- simple `displace` writes an edited image
- `control_irrelevant` writes an edited image
- generated manifests include edited-image hashes
- rejected manifests record infeasible items
- quality gates catch global destructive edits
- quality gates pass reasonable simple edits
- quality reports write all expected files
- materialization includes only quality-passed edits
- materialized task rows pass leakage checks
- generated/edit-ready statuses cannot support claims
- optional diffusers mode is import-safe and fails clearly when unavailable

No real ADE20K root was processed during V1.5 validation.

## Generated And Rejected Behavior

Generated rows are written to:

```text
data/manifests/pilot_generated_edits.jsonl
```

Rejected rows are written to:

```text
data/manifests/pilot_generated_edits_rejected.jsonl
```

Rejected rows keep the planned identifiers and include `rejection_reason`,
`generation_status=rejected`, and `quality_gate_status=not_run`.

## Quality Gate Behavior

Quality gates are structural edit checks, not semantic validity checks. They
allow edit-type-specific expected changes:

- `remove`: changes should be concentrated in the mask.
- `occlude`: changes may cover the planned occluder bbox.
- `displace`: changes may cover the original mask and planned destination.
- `control_irrelevant`: changes must be mild and not globally destructive.

Passing quality gates means an edit is ready for manual/human validity review.
It does not mean the item is evidence.

## Current Non-Evidence Status

- generated edits are `GENERATED_EDIT_ONLY`
- materialized tiny task rows are `EDIT_READY_NON_EVIDENCE`
- no VLM inference was run
- no human validity checks were run
- no model predictions or scores exist
- no certification artifacts exist
- no paper result claims are enabled

## Exact Command Sequence After Real `pilot_edit_plan.jsonl` Exists

```bash
python3 -m certvic.edit.generate_edits \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --out-dir data/edits/ade20k_tiny_pilot \
  --out-manifest data/manifests/pilot_generated_edits.jsonl \
  --rejected-out data/manifests/pilot_generated_edits_rejected.jsonl \
  --summary-out data/results/tiny_edit_generation_summary.json \
  --max-items 20 \
  --mode simple \
  --seed 0

python3 -m certvic.edit.quality_report \
  --generated-manifest data/manifests/pilot_generated_edits.jsonl \
  --rejected data/manifests/pilot_generated_edits_rejected.jsonl \
  --out-dir data/results/tiny_edit_quality_report

python3 -m certvic.data.materialize_tasks \
  --task-preview data/manifests/pilot_task_preview.jsonl \
  --generated-edits data/manifests/pilot_generated_edits.jsonl \
  --out data/manifests/pilot_eval_tasks_tiny.jsonl \
  --summary-out data/manifests/pilot_eval_tasks_tiny_summary.json
```

## Manual Review Before VLM Inference

- inspect every generated original/edited image pair
- inspect `data/results/tiny_edit_quality_report/generated_edit_review.md`
- inspect `data/results/tiny_edit_quality_report/review_gallery_manifest.jsonl`
- inspect all rejected generation rows
- confirm task-family/edit-type compatibility
- confirm simple edits are semantically valid
- confirm control edits are mild and irrelevant
- confirm leakage summary remains clean
- run human validity checks

## Remaining Blockers Before VLM Inference

- run V1.5 commands against a reviewed real local edit plan
- inspect generated/rejected artifacts manually
- resolve any quality warnings or generator failures
- prepare and pass human validity checks
- decide whether simple mode is sufficient or a reviewed local generator is
  needed
- keep any optional inpainting mode local/cache-only and explicitly approved

## Remaining Blockers Before Evidence Claims

- VLM inference must run on approved zero-cost/local setup
- predictions must be parsed and scored
- confidence-sequence/certification artifacts must exist
- claim ledger and paper scanner must pass
- human validity and quality-gate results must be linked to the evaluated rows

Until then, paper result sections must keep `[RESULT REQUIRED]` placeholders.
