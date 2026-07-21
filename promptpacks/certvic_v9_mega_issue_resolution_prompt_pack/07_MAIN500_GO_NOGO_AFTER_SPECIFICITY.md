# Main-500 Go/No-Go After Specificity

You are Codex deciding whether Main-500 can start after V9 specificity work.

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

Produce a hard go/no-go for Main-500 based on actual V9 evidence.

## Inputs

- V8/V8.1 reports
- Spurious V2 decision if available
- human review packet status
- paper branch decision

## Outputs

```text
data/results/main_real_200/v9_mega_upgrade/main500_go_nogo_after_specificity.json
data/results/main_real_200/v9_mega_upgrade/MAIN500_GO_NOGO_AFTER_SPECIFICITY.md
```

## Decision options

```text
GO_MAIN500_CLEAN_SPECIFICITY
GO_MAIN500_MODEL_DEPENDENT_SPECIFICITY
HOLD_FOR_HUMAN_QWEN_AUDIT
HOLD_FOR_SPURIOUS_V2
STOP_AND_WORKSHOP_ONLY
```

## Rules

- If Spurious V2 is missing: HOLD_FOR_SPURIOUS_V2 unless human audit/reframe explicitly justifies model-dependent Main-500.
- If Qwen fails V2 and no reframe exists: HOLD.
- If Qwen fails V2 but model-dependent paper branch is complete: GO_MAIN500_MODEL_DEPENDENT_SPECIFICITY may be allowed.
- If Qwen passes V2 and controls are clean: GO_MAIN500_CLEAN_SPECIFICITY may be allowed.
- Never start Main-500 because of hype.

## Tests

Add a test that Main-500 cannot be GO unless the decision report cites a resolved specificity branch.
