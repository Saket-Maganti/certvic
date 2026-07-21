# Paper Compile and CVPR Scaffold

You are Codex turning the artifact-backed results into a compiled, anonymous, claim-safe CVPR scaffold.

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

Build a paper draft that compiles, with guarded result language.

Outputs:

```text
paper/main_v9.tex
paper/sections/01_introduction_v9.tex
paper/sections/02_related_work_v9.tex
paper/sections/03_method_v9.tex
paper/sections/04_experiments_v9.tex
paper/sections/05_results_v9.tex
paper/sections/06_limitations_v9.tex
paper/sections/07_conclusion_v9.tex
paper/main_v9.pdf
```

Rules:

- Use artifact-backed tables only.
- If Main-500 missing, label Main-200 as pilot and do not overclaim.
- If Qwen specificity remains failed, use model-dependent branch.
- Compile with `latexmk` or `pdflatex`; if tool unavailable, write exact failure.
- Run paper numbers guard and claim language guard.

Tests: compiled PDF exists if LaTeX installed; otherwise blocked with clear reason.
