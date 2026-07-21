# Preliminary Label Hygiene and V8.1 Audit Repair

You are Codex repairing evidence-label hygiene in the V8.1 forensic artifacts.

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

## Problem

V8.1 generated preliminary AI/machine triage labels with prefixes like `HUMAN_PATCH_NEAR_TARGET` and `HUMAN_PRELIMINARY_EVAL`. Even if the report says they are not human review, those names are dangerous and must be repaired.

## Mission

Rename all non-human preliminary labels to explicit machine labels without changing the underlying Qwen result.

Use replacement mapping:

```text
HUMAN_PRELIMINARY_EVAL -> CODEX_PRELIMINARY_EVAL
HUMAN_VALID_FAILURE -> CODEX_PRELIM_VALID_FAILURE
HUMAN_PATCH_TOO_SALIENT -> CODEX_PRELIM_PATCH_TOO_SALIENT
HUMAN_PATCH_NEAR_TARGET -> CODEX_PRELIM_PATCH_NEAR_TARGET
HUMAN_OBJECT_REGION_AFFECTED -> CODEX_PRELIM_OBJECT_REGION_AFFECTED
HUMAN_PROMPT_AMBIGUOUS -> CODEX_PRELIM_PROMPT_AMBIGUOUS
HUMAN_PARSE_ERROR -> CODEX_PRELIM_PARSE_ERROR
HUMAN_IMAGE_MISMATCH -> CODEX_PRELIM_IMAGE_MISMATCH
HUMAN_LOW_CONFIDENCE_UNKNOWN -> CODEX_PRELIM_LOW_CONFIDENCE_UNKNOWN
```

## Steps

1. Search all V8.1 artifacts:

```bash
grep -R "HUMAN_PRELIM\|HUMAN_PATCH\|HUMAN_VALID\|HUMAN_OBJECT\|HUMAN_PROMPT\|HUMAN_PARSE\|HUMAN_IMAGE\|HUMAN_LOW" -n   data/results/main_real_200/v8_1_qwen_spurious_forensics paper docs tests scripts certvic || true
```

2. Update generated V8.1 artifacts, code, tests, reports, and paper sections to use `CODEX_PRELIM_*`.
3. Create a migration report:

```text
data/results/main_real_200/v9_mega_upgrade/prelim_label_hygiene_migration.json
data/results/main_real_200/v9_mega_upgrade/PRELIM_LABEL_HYGIENE_MIGRATION.md
```

4. Add/modify tests so no non-human AI label begins with `HUMAN_`.
5. Keep any true human review files separate and empty/pending unless actually filled.

## Required tests

Add or update:

```text
tests/test_v9_prelim_label_hygiene.py
```

Tests:

- no `HUMAN_PRELIMINARY_EVAL` remains
- no `HUMAN_*` label remains in machine triage outputs
- `CODEX_PRELIMINARY_EVAL` disclaimer exists
- Qwen raw result remains 12/94 failing
- paper_evidence remains false

Run:

```bash
python3 -m pytest -q tests/test_v9_prelim_label_hygiene.py
python3 -m pytest -q
python3 -m certvic.validation.claim_language_guard --root docs paper data/results/main_real_200/v9_mega_upgrade data/results/main_real_200/v8_1_qwen_spurious_forensics --out data/results/main_real_200/v9_mega_upgrade/claim_guard_v9_label_hygiene.json
python3 -m certvic.security.release_privacy_audit --root . --out data/results/main_real_200/v9_mega_upgrade/privacy_v9_label_hygiene.md --json-out data/results/main_real_200/v9_mega_upgrade/privacy_v9_label_hygiene.json
```

## Required final response

- files changed
- number of replacements
- confirmation no machine label uses `HUMAN_`
- confirmation Qwen gate unchanged
- tests/guards
