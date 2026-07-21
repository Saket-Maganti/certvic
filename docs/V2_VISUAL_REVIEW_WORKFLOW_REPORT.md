# V2 Visual Review Workflow Report

Date: 2026-06-22
Prompt: `02_V2_VISUAL_REVIEW_AND_APPROVAL_WORKFLOW.md`

## What was added

- `certvic/validation/export_visual_review.py` — review-sheet CSV with the
  required columns (item/edit/source ids, task_family, domain, edit_type,
  required_change, image paths, mask_id, bbox, quality status/warnings,
  neutral_question, the six reviewer fields, notes, reviewer_id). **No model
  outputs.**
- `certvic/validation/build_review_gallery.py` — local HTML gallery, relative
  links, no pixel copy by default, no external services.
- `certvic/validation/aggregate_visual_review.py` — keep/drop decisions + per
  field IAA + keep/drop lists.
- `certvic/data/apply_visual_review.py` — materializes approved tasks with
  `visual_review_status=approved`, `evidence_status=HUMAN_REVIEWED_NON_EVIDENCE`.
- `certvic/reporting/visual_review_report.py` — markdown + JSON report.
- IAA strengthened in `certvic/validation/iaa.py`: `normalize_rating`,
  `majority_agreement`, `field_iaa` (Cohen kappa for 2 raters, majority for 3+,
  single-rater warning, robust yes/no/uncertain).

## Drop rule

An item is dropped if ANY of photorealistic, single_factor, target_object_clear,
required_change_unambiguous, prompt_answerable, keep_for_eval is majority-no,
uncertain-heavy, or not majority-yes.

## Tests

- `tests/test_v2_visual_review.py` — 5 tests (sheet columns + no predictions,
  IAA methods, keep/drop + IAA aggregation, approved-status materialization,
  gallery + report). Full suite: **147 passed** (was 142). No regressions.

## Updated

- `configs/real_pilot_ade20k.yaml` (label_policy + visual_review block),
  `docs/REPRO.md`, `docs/DATA_CARD.md`, `docs/PILOT_ADE20K.md` (earlier),
  `docs/RISK_REGISTER.md`.

## Status: PASS (fixtures). Next: `06_V2_BASELINES_AND_ABLATIONS_UPGRADE.md`.
