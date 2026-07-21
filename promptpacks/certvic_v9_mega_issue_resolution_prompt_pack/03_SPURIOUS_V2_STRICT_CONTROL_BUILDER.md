# Spurious V2 Strict Control Builder

You are Codex building a stricter spurious-control v2 dataset to test whether Qwen's 12/94 failure is due to model instability or v1 control construction.

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

Build a CPU-only Spurious V2 control set with stronger geometric and salience constraints. This prompt builds data and manifests only; it does not run VLMs.

## Requirements

V2 should target `n=200-300` no-change pairs if data supports it. If insufficient data, produce the maximum feasible set and document why.

Hard item rules:

- target object mask must not change
- object-region pixel difference must be exactly zero or within a documented codec tolerance
- patch/mask overlap must be zero
- patch bbox/target bbox intersection must be zero
- minimum patch-to-target bbox distance threshold must be enforced
- patch should be lower salience than v1
- same JPEG re-encoding for original/control arms
- class-balanced sampling where feasible
- no manual cherry-picking
- deterministic seed
- split from ADE20K train/validation must be recorded

## First inspect

```bash
find data/edits/spurious_flip_control -maxdepth 4 -type f | sort | head -200
find data -iname "*ade*mask*" -o -iname "*mask*.jsonl" | sort | head -50
find scripts certvic -iname "*spurious*" -o -iname "*control*" | sort
```

## Build code

Create:

```text
scripts/build_spurious_v2_control.py
certvic/v9/spurious_v2_quality.py
commands/spurious_v2/build_spurious_v2.sh
```

Outputs:

```text
data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl
data/edits/spurious_v2_control/images/
data/edits/spurious_v2_control/spurious_v2_manifest.json
data/results/main_real_200/v9_mega_upgrade/spurious_v2_quality_report.json
data/results/main_real_200/v9_mega_upgrade/SPURIOUS_V2_QUALITY_REPORT.md
dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip
```

## Quality report must include

- n_items
- class distribution
- split distribution
- object-region diff summary
- patch salience summary
- bbox distance summary
- bbox overlap count
- mask overlap count
- detectability proxy if cheap CPU
- examples gallery path

## Tests

Add:

```text
tests/test_v9_spurious_v2_builder.py
```

Tests:

- output task file exists
- no object/mask overlap
- no bbox overlap
- min distance rule enforced
- bundle contains images/tasks/manifest
- bundle contains no predictions/model weights/private paths
- v2 does not overwrite v1

Run full tests/guards.
