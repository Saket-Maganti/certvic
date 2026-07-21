# Preliminary Label Hygiene Migration

## Summary

- Total replacements: `163`.
- Machine/AI triage labels now use `CODEX_PRELIM_*` names.
- Qwen spurious specificity gate is unchanged: `12/94 = 0.1277`, failed threshold `<= 0.10`.
- `paper_evidence` remains `false`; no real human validation was created.

## Files Changed

- `data/results/main_real_200/v8_1_qwen_spurious_forensics/qwen_spurious_recompute_report.md`
- `data/results/main_real_200/v8_1_qwen_spurious_forensics/V8_1_TASK_LEDGER.md`
- `data/results/main_real_200/v8_1_qwen_spurious_forensics/qwen_spurious_failed_12_prelim_labels.csv`
- `data/results/main_real_200/v8_1_qwen_spurious_forensics/qwen_spurious_failed_12_prelim_labels.json`
- `data/results/main_real_200/v8_1_qwen_spurious_forensics/qwen_spurious_failed_12_gallery.html`
- `data/results/main_real_200/v8_1_qwen_spurious_forensics/qwen_spurious_recompute_scenarios.csv`
- `data/results/main_real_200/v8_1_qwen_spurious_forensics/qwen_spurious_failed_12_gallery_manifest.json`
- `data/results/main_real_200/v8_1_qwen_spurious_forensics/qwen_spurious_recompute_scenarios.json`
- `data/results/main_real_200/v8_1_qwen_spurious_forensics/human_claim.md`
- `data/results/main_real_200/v8_1_qwen_spurious_forensics/v8_1_task_ledger.json`
- `tests/test_v8_1_qwen_spurious_forensics.py`
- `scripts/build_v8_1_qwen_spurious_forensics.py`

## Replacement Counts

- `HUMAN_PRELIMINARY_EVAL` -> `CODEX_PRELIMINARY_EVAL`: `51`
- `HUMAN_VALID_FAILURE` -> `CODEX_PRELIM_VALID_FAILURE`: `12`
- `HUMAN_PATCH_TOO_SALIENT` -> `CODEX_PRELIM_PATCH_TOO_SALIENT`: `12`
- `HUMAN_PATCH_NEAR_TARGET` -> `CODEX_PRELIM_PATCH_NEAR_TARGET`: `28`
- `HUMAN_OBJECT_REGION_AFFECTED` -> `CODEX_PRELIM_OBJECT_REGION_AFFECTED`: `12`
- `HUMAN_PROMPT_AMBIGUOUS` -> `CODEX_PRELIM_PROMPT_AMBIGUOUS`: `2`
- `HUMAN_PARSE_ERROR` -> `CODEX_PRELIM_PARSE_ERROR`: `2`
- `HUMAN_IMAGE_MISMATCH` -> `CODEX_PRELIM_IMAGE_MISMATCH`: `2`
- `HUMAN_LOW_CONFIDENCE_UNKNOWN` -> `CODEX_PRELIM_LOW_CONFIDENCE_UNKNOWN`: `2`
- `CODEX_VALID_FAILURE` -> `CODEX_PRELIM_VALID_FAILURE`: `10`
- `CODEX_PATCH_TOO_SALIENT` -> `CODEX_PRELIM_PATCH_TOO_SALIENT`: `6`
- `CODEX_PATCH_NEAR_TARGET` -> `CODEX_PRELIM_PATCH_NEAR_TARGET`: `14`
- `CODEX_OBJECT_REGION_AFFECTED` -> `CODEX_PRELIM_OBJECT_REGION_AFFECTED`: `5`
- `CODEX_PROMPT_AMBIGUOUS` -> `CODEX_PRELIM_PROMPT_AMBIGUOUS`: `2`
- `CODEX_PARSE_ERROR` -> `CODEX_PRELIM_PARSE_ERROR`: `1`
- `CODEX_IMAGE_MISMATCH` -> `CODEX_PRELIM_IMAGE_MISMATCH`: `1`
- `CODEX_LOW_CONFIDENCE_UNKNOWN` -> `CODEX_PRELIM_LOW_CONFIDENCE_UNKNOWN`: `1`

## Blockers

- Real human review remains pending.
- Qwen specificity remains failed until a preregistered V9 gate says otherwise.
