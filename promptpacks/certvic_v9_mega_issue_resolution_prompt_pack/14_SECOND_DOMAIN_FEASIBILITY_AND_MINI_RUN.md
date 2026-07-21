# Second Domain Feasibility and Mini-Run

You are Codex building a second-domain expansion path.

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

Prepare a low-cost second-domain mini-run using COCO/LVIS/OpenImages if available/free, with the goal of strengthening generality without derailing Main-500.

Steps:

1. Inspect existing second-domain stubs.
2. Choose one feasible public/free domain.
3. Build a tiny CPU plan: 50-100 candidate items.
4. Prepare but do not fake edit/VLM results.

Outputs:

```text
data/results/second_domain/feasibility/SECOND_DOMAIN_FEASIBILITY.md
data/results/second_domain/feasibility/second_domain_plan.json
commands/second_domain/build_mini_run.sh
notebooks/kaggle/second_domain_mini_diffusion_T4x2.ipynb
notebooks/kaggle/second_domain_mini_vlm_T4x2.ipynb
```

Gate: second domain is optional and must not block resolving Qwen specificity.
