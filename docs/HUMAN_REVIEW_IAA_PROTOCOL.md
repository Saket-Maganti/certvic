# Human Review & Inter-Annotator Agreement (IAA) Protocol

**Status: protocol ready; two-rater IAA pending, NOT evidence**
(`evidence_status = REVIEW_IAA_PENDING_NON_EVIDENCE` until a second rater completes the sheet).

The current reviewed set is **single-rater**. A CVPR-grade paper needs a second independent
rater, a measured agreement (Cohen's κ), and an explicit handling of items where raters
disagree. This protocol is zero-cost (one additional human, no paid annotation tools).

## Step 1 — Export the blinded second-rater sheet

```bash
python3 scripts/export_second_rater_review.py        # seed fixes the blinded order
```
→ `data/results/main_real_200/review_iaa/second_rater_review_sheet.csv`

The sheet is **blinded**: rows are in randomized (seeded) order, and it contains **no model
results and no first-rater labels**, so the second rater is not anchored.

## Step 2 — Second rater fills the sheet

One person, independent of rater 1, judges each edited image and fills only the human
columns. Allowed values are `yes`/`no` (and `uncertain` where noted):

| field | values | IAA? |
|---|---|---|
| `photorealism` | yes/no | ✅ vs `photorealistic` |
| `single_factor` | yes/no | ✅ vs `single_factor` |
| `answerability` | yes/no | ✅ vs `prompt_answerable` |
| `required_answer_change_unambiguous` | yes/no | ✅ vs `required_change_unambiguous` |
| `keep_for_eval` (gate) | yes/no | ✅ vs `keep_for_eval` |
| `target_absent_after_edit` | yes/no/uncertain | rater-2 only (no κ yet) |
| `residual_target_cue_visible` | yes/no/uncertain | rater-2 only |
| `confidence` | high/med/low | rater-2 only |
| `notes`, `reviewer_id` | text | required `reviewer_id` |

## Step 3 — Compute agreement

```bash
python3 scripts/compute_review_iaa.py
```
→ `review_iaa/iaa_report.{json,md}`. Reports, **separately**:
- **Preliminary single-rater** (current canonical visual review) — descriptive only.
- **Two-rater**: Cohen's κ + % agreement per overlapping field (reuses
  `certvic.validation.iaa`), plus the **exclusion/sensitivity set** = items where the two
  raters disagree on the `keep_for_eval` gate.

Items in the exclusion set drive a sensitivity check (recompute the gap with them dropped via
`scripts/pilot_report_from_raw.py`); they are **not** silently removed from the canonical set.

## Hard rules (enforced)

- Human labels are **never** auto-filled; the export ships blank.
- No reviewer is fabricated; `reviewer_id` is required on completed rows.
- Existing first-rater labels are **never** overwritten (the second sheet is a separate file).
- **No paper-grade review claim** until two-rater IAA exists; until then the status stays
  `second_rater_pending`.
