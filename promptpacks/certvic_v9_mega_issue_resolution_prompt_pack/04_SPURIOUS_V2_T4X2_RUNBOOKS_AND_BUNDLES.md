# Spurious V2 T4x2 Runbooks and Kaggle Bundles

You are Codex preparing free Kaggle T4x2 execution for Spurious V2.

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

Create or update T4x2 notebooks/runbooks to run Spurious V2 across Qwen, InternVL, and LLaVA. This prompt does not run GPU inference locally.

## Inputs

```text
dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip
dist/certvic_kaggle_main200_bundle.zip
notebooks/kaggle/vlm_*_T4x2_parallel*.ipynb
```

## Outputs

Create:

```text
notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb
notebooks/kaggle/vlm_internvl_8b_spurious_v2_T4x2.ipynb
notebooks/kaggle/vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb
docs/runbooks/KAGGLE_SPURIOUS_V2_T4X2_RUNBOOK.md
dist/kaggle_remaining_runs/SPURIOUS_V2_INPUTS_MATRIX.md
dist/kaggle_remaining_runs/SPURIOUS_V2_LOCAL_INGEST_COMMANDS.md
```

Each notebook must:

- use `RUN_TAG="spurious_v2"`
- support T4x2 parallel shard0/shard1 workers
- write `pred_<provider>_spurious_v2_merged.jsonl`
- zip outputs as `<provider>_spurious_v2_preds.zip`
- support resume/skip complete shards
- print row counts and parse summary
- use diagnostic-freeform fixes where applicable but keep spurious strict yes/no

## Runtime estimates

Use V2 item count to estimate:

- Qwen T4x2 runtime
- InternVL T4x2 runtime
- LLaVA T4x2 runtime
- fallback single-GPU runtime

## Tests

Update remaining-runbook tests so:

- V2 notebooks are nbformat-valid
- contain `CUDA_VISIBLE_DEVICES`
- output filenames match ingest docs
- no fake predictions
- no private paths

Run full tests/guards.
