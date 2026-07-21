# Main-500 VLM T4x2 Evaluation Pack

You are Codex preparing T4x2 VLM evaluation for Main-500.

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

## Gate

Requires approved Main-500 human review. If missing, write BLOCKED.

## Mission

Create/refresh Qwen, InternVL, and LLaVA T4x2 notebooks for Main-500 reviewed tasks.

Outputs:

```text
notebooks/kaggle/main500_qwen2_5_vl_7b_T4x2.ipynb
notebooks/kaggle/main500_internvl_8b_T4x2.ipynb
notebooks/kaggle/main500_llava_onevision_7b_T4x2.ipynb
docs/runbooks/MAIN500_VLM_T4X2_RUNBOOK.md
dist/main500_vlm_eval_bundle.zip
```

Each notebook must:

- split tasks deterministically across T4x2
- support resume
- write shard and merged predictions
- output parse summaries
- use strict yes/no parsing for certification tasks
- not use diagnostic freeform fallback on certification tasks

Tests: nbformat, paths, output names, no fake predictions.
