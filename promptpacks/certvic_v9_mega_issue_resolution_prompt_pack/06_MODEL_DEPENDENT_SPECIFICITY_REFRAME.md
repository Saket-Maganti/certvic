# Model-Dependent Specificity Reframe

You are Codex writing a scientifically honest reframe that keeps project value high even if Qwen fails specificity.

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

Prepare the paper and reports for two branches:

A. Qwen passes Spurious V2: cleaner cross-model specificity story.
B. Qwen fails Spurious V2: model-dependent specificity story.

Do not force either branch. Detect current evidence and render the correct branch.

## Outputs

Create:

```text
data/results/main_real_200/v9_mega_upgrade/specificity_branch_decision.json
data/results/main_real_200/v9_mega_upgrade/SPECIFICITY_BRANCH_DECISION.md
paper/sections/v9_specificity_controls.tex
paper/sections/v9_model_dependent_limitations.tex
paper/tables/v9_specificity_controls.tex
```

## Required language if Qwen remains failed

Say:

- InternVL and LLaVA pass the irrelevant-edit specificity gate.
- Qwen shows a strong update-gap result but elevated sensitivity to irrelevant controls.
- The evidence supports model-dependent specificity, not all-model specificity.
- Main conclusions must be conditioned on this limitation.

Do not say all models pass.

## Required language if Qwen passes V2

Say:

- V1 showed Qwen borderline/failing behavior under the initial spurious control.
- V2 was stricter and preregistered after forensic analysis.
- Report both V1 and V2 results.
- Avoid hiding V1; V2 does not erase it.

## Tests

Test that claim language is branch-consistent and never claims all-model specificity unless both V1/V2 policy permits it.
