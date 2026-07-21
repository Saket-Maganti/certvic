# V2 Edit Engine and Quality Report

Date: 2026-06-22
Prompt: `04_V2_EDIT_ENGINE_AND_QUALITY_UPGRADE.md`

## What was added

- `certvic/edit/engines.py` — modular engine registry: `simple_fill`,
  `simple_occlude`, `simple_displace`, `simple_control`, `composite_occluder`,
  `diffusers_inpaint_optional` (disabled), `no_op_debug`. CLI:
  `python3 -m certvic.edit.engines ...`.
- Deterministic replay metadata per edit: engine version, seed,
  `source_image_sha256`, `mask_spec_hash`, `edit_plan_hash`,
  `generation_config_hash`, actual params.
- Batch generation safety: `--max-items` required unless `--allow-full-run`,
  resume by edit_id, rejected-file append/resume, fail-fast option, no overwrite
  by default, duplicate-edited-image detection by sha256.
- Quality-gate upgrades in `certvic/edit/quality_gates.py`: uniform-pixel
  fraction, sharpness score, all-black / all-white detectors. Metrics are always
  reported; the warnings are **opt-in** via `configs/edit_quality.yaml` so the
  existing simple/CPU fixtures are not falsely failed.
- `configs/edit_quality.yaml`.

## Key honesty point (construct validity)

The shipped simple engines remain crude (flat fill / gray box / cut-paste) and
are pipeline-validation only — NOT photorealistic evidence. The real-image
realism path is `diffusers_inpaint_optional`, which is disabled by default,
never downloads weights, and requires explicit local/cached weights + GPU. The
new degenerate-edit detectors exist precisely so that, once realistic edits are
generated, all-black/blurry/duplicate failures are caught before review.

## Tests

- `tests/test_v2_edit_engine_quality.py` — 14 tests (each engine, deterministic
  replay, diffusers-disabled, no-overwrite, batch max_items + resume, metric
  helpers).
- Full suite: **142 passed** (was 128). No regressions.

## Blockers before evidence

- Photorealistic edits require local diffusion weights + free GPU (not yet
  available); simple engines are not paper evidence.

## Status: PASS (CPU/fixtures). Next: `02_V2_VISUAL_REVIEW_AND_APPROVAL_WORKFLOW.md`.
