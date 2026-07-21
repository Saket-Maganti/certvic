# Spurious V2 Ingest, Gate, and Decision

You are Codex ingesting real Spurious V2 Kaggle outputs if they exist. If they do not exist, write BLOCKED run instructions.

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

Normalize, validate, and score Spurious V2 results. Decide whether Qwen specificity is resolved or remains model-dependent.

## Expected inputs after Kaggle

Search:

```text
kaggleoutputs/spurious_v2
kaggleoutputs/newruns
~/Downloads
data/results/main_real_200/kaggle_spurious_v2
```

Expected files:

```text
pred_qwen2_5_vl_7b_spurious_v2_merged.jsonl
pred_internvl_8b_spurious_v2_merged.jsonl
pred_llava_onevision_7b_spurious_v2_merged.jsonl
```

If missing, write:

```text
data/results/main_real_200/v9_mega_upgrade/SPURIOUS_V2_BLOCKED_MISSING_PREDICTIONS.md
```

and stop without faking results.

## If present

Copy to:

```text
data/results/main_real_200/kaggle_spurious_v2/
```

Run/implement:

```bash
python3 scripts/pilot_report_from_raw.py --provider <provider> --model-name <model> --run-label <provider> --raw-spurious-v2 data/results/main_real_200/kaggle_spurious_v2/pred_<provider>_spurious_v2_merged.jsonl
```

If `--raw-spurious-v2` does not exist, extend the script carefully without breaking V1/V7/V8.

Run detectability/quality for V2:

```bash
python3 -m certvic.validation.edit_detectability --tasks data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl --out-dir data/results/spurious_v2_control/edit_detectability
```

Create:

```text
data/results/main_real_200/v9_mega_upgrade/spurious_v2_specificity_results.csv
data/results/main_real_200/v9_mega_upgrade/spurious_v2_specificity_results.json
data/results/main_real_200/v9_mega_upgrade/SPURIOUS_V2_DECISION_REPORT.md
```

## Decision logic

- If Qwen passes V2 and V2 quality gates pass: specificity issue likely v1-control-construction or borderline; write conservative claim.
- If Qwen fails V2: Qwen specificity failure is robust; reframe model-dependent.
- If V2 has high detectability/artifact risk: V2 invalid; redesign.
- Never weaken threshold.

## Tests

Add:

```text
tests/test_v9_spurious_v2_ingest_decision.py
```

Tests must pass both missing-output BLOCKED mode and present-output mode if files exist.
