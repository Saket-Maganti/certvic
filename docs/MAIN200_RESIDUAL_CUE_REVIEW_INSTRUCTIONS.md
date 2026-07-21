# Main-200 Residual-Cue Review — Instructions

**Purpose.** The absent-object control already shows the models perceive *natural* absence.
This separate review asks, for each **edited** image: *after the edit, is any visible trace
of the target object still present?* It is the human check against the reviewer objection
*"the edited images have residual artifacts the VLM exploits."*

This is **not** the original visual review and does **not** change the canonical pilot
result. It produces a separate sensitivity summary only.

## Workflow

1. **Export the blank sheet** (already generated; regenerate any time):
   ```bash
   python3 scripts/export_residual_cue_review.py
   ```
   → `data/results/main_real_200/residual_cue_review/residual_cue_review_sheet.csv`

2. **Review each row** against the two images. Open `original_image_path` and
   `edited_image_path` side by side. Fill **only** the human columns (leave the rest as-is).

3. **Apply / summarize** the completed sheet:
   ```bash
   python3 scripts/apply_residual_cue_review.py
   ```
   → `residual_cue_summary.json` + `residual_cue_sensitivity.md`

## Columns

Pre-filled (do not edit): `item_id`, `edit_id`, `model_fail_count`, `original_image_path`,
`edited_image_path`, `target_object`, `edit_type`.

- `model_fail_count` (0–3): how many of the three models gave a wrong post-edit presence
  answer for this item (canonical `edited_correct = False`). A reviewer **aid** for
  prioritization — not a label to copy.

Human-entered (one reviewer per row; blank until reviewed):

| column | allowed values | meaning |
|---|---|---|
| `residual_target_visible` | `yes` / `no` / `uncertain` | Is any visible trace of the target still present in the edited image? |
| `residual_type` | `none` / `silhouette` / `texture` / `shadow` / `partial object` / `context-only` / `other` | If a trace is visible, what kind? `context-only` = the surrounding scene implies it but no direct trace. |
| `human_absence_confident` | `yes` / `no` / `uncertain` | Are you confident the target is genuinely gone/not-clearly-visible? |
| `notes` | free text | Anything notable (e.g., "faint shadow lower-left"). |
| `reviewer_id` | short id | Required on every reviewed row. |

## What the summary computes

- **Residual-cue rate** = `yes / (yes + no)` over decided rows (`uncertain` excluded).
- **Model-fail rate when `human_absence_confident = yes`** — the headline cross-check.
- **Per-edit-type** breakdown (residual rate + mean model-fail).
- **Uncertain rows** — listed and excluded from strong claims.
- **Clean subset** (`human_absence_confident = yes` **and** `residual_target_visible = no`):
  the strongest signal that the failure is not explained by residual pixels.

## Hard rules (enforced by the scripts)

- Human labels are **never** auto-filled; the export ships blank.
- Unreviewed rows are excluded — never treated as evidence.
- Items are **not** removed from the canonical pilot result; this is an alternate
  sensitivity report. Full re-certification on any subset requires re-running
  `scripts/pilot_report_from_raw.py` on the filtered set.
- `residual_cue_summary.json` carries `evidence_status = RESIDUAL_CUE_SENSITIVITY_NON_EVIDENCE`.
