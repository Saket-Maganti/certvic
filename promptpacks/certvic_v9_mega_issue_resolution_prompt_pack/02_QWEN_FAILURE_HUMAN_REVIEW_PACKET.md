# Real Human Review Packet for Qwen Spurious Failures

You are Codex building a real human-review packet. You must not fill human labels.

## Global hard constraints for every V9 prompt

- Repo: `/Users/saketmaganti/Projects/certVIC`.
- Do not fabricate predictions, human labels, results, citations, or paper claims.
- Do not weaken `control_spurious_flip_max <= 0.10`.
- Do not manually delete Qwen failures to force a pass.
- Do not mark `paper_evidence=true` unless an existing, explicit repository policy allows it after real gates pass.
- Do not claim CVPR-ready unless the V9 final audit supports it.
- Do not commit unless explicitly asked.
- Keep all tests CPU/local.
- Heavy model/GPU work must be packaged for Kaggle/free GPU and never simulated locally.
- Any machine/AI triage label must be named `CODEX_PRELIM_*`, never `HUMAN_*`.
- Real human labels must be absent unless a person actually fills a review sheet.
- If a task is blocked, write a BLOCKED artifact with the exact missing file/action.
- Preserve V7/V8 canonical outputs; never destructively overwrite prior results.
- Every prompt must update a V9 task ledger.

## Current state to assume

- V8 ingested all 12 provider/run outputs from `kaggleoutputs/newruns`.
- Main pilot: Qwen2.5-VL-7B, InternVL2-8B, LLaVA-OneVision-7B on 91 reviewed items.
- Spurious specificity gate: Qwen failed with `12/94 = 0.1277`; InternVL passed `1/94`; LLaVA passed `3/94`.
- Detectability: `n_items=94`, AUC about `0.6682`, `artifact_risk=false`.
- Scaled perception: Qwen about `0.897`, InternVL about `0.935`, LLaVA about `0.9322`.
- Polarity and mechanism diagnostics are complete and diagnostic-only.
- V8.1 forensic audit says Qwen failures are Qwen-only; claim-valid recompute scenarios still fail; preliminary labels were machine/AI triage and must not be represented as human review.
- Recommendation before V9: do not start Main-500 until Qwen specificity is resolved or the paper is honestly reframed.

## Mission

Create an ergonomic review packet for the 12 Qwen spurious failures so a real human can judge whether each item is a valid irrelevant perturbation or a flawed control item.

## Inputs

Use V8.1 files:

```text
data/results/main_real_200/v8_1_qwen_spurious_forensics/qwen_spurious_failed_12.csv
data/results/main_real_200/v8_1_qwen_spurious_forensics/qwen_spurious_failed_12_gallery.html
```

Also use image paths and metadata from the all-items JSONL/CSV and quality audit.

## Outputs

Create:

```text
data/annotations/v9_qwen_spurious_human_review/qwen_failed_12_human_review.csv
data/annotations/v9_qwen_spurious_human_review/qwen_failed_12_human_review_instructions.md
data/annotations/v9_qwen_spurious_human_review/qwen_failed_12_human_review_gallery.html
data/annotations/v9_qwen_spurious_human_review/qwen_failed_12_human_review_manifest.json
scripts/apply_v9_qwen_spurious_human_review.py
```

## Review sheet columns

Required columns:

```text
item_id
target_object
question
original_image_path
spurious_image_path
qwen_original_raw
qwen_spurious_raw
qwen_original_parsed
qwen_spurious_parsed
codex_prelim_label
codex_prelim_confidence
human_valid_control
human_failure_cause
human_notes
human_reviewer_id
human_review_timestamp
```

Human label options:

```text
VALID_IRRELEVANT_CONTROL
PATCH_TOO_SALIENT
PATCH_NEAR_TARGET
OBJECT_REGION_AFFECTED
PROMPT_AMBIGUOUS
PARSE_ERROR
IMAGE_MISMATCH
UNSURE
```

Leave all human columns blank. Do not fill them.

## Apply script behavior

`scripts/apply_v9_qwen_spurious_human_review.py` must:

- refuse if human labels are blank
- validate label vocabulary
- recompute Qwen spurious gate under human-confirmed objective exclusions only
- separately report subjective exclusions
- never change canonical result automatically
- write:

```text
data/results/main_real_200/v9_mega_upgrade/qwen_spurious_human_review_apply_report.json
data/results/main_real_200/v9_mega_upgrade/QWEN_SPURIOUS_HUMAN_REVIEW_APPLY_REPORT.md
```

## Tests

Add:

```text
tests/test_v9_qwen_spurious_human_review_packet.py
```

Test sheet exists, human columns blank, apply script refuses blank review, no paper evidence change.

Run full tests and guards.
