# Qwen Failed-12 Human Review Instructions

This packet is for real human review only. Do not prefill the `human_*` columns from machine triage. The existing `codex_prelim_label` field is only a CODEX_PRELIM machine aid and is not evidence.

## Goal

For each Qwen spurious failure, decide whether the edited/spurious image is still a valid irrelevant-control item for the question.

## Required Fields

- `human_valid_control`: enter `TRUE`, `FALSE`, or `UNSURE`.
- `human_failure_cause`: choose one of `VALID_IRRELEVANT_CONTROL`, `PATCH_TOO_SALIENT`, `PATCH_NEAR_TARGET`, `OBJECT_REGION_AFFECTED`, `PROMPT_AMBIGUOUS`, `PARSE_ERROR`, `IMAGE_MISMATCH`, `UNSURE`.
- `human_notes`: short free-text rationale.
- `human_reviewer_id`: anonymized reviewer ID.
- `human_review_timestamp`: ISO-like timestamp.

Leave no human field blank before running `scripts/apply_v9_qwen_spurious_human_review.py`. The apply script refuses incomplete sheets and never changes canonical V8/V9 results automatically.
