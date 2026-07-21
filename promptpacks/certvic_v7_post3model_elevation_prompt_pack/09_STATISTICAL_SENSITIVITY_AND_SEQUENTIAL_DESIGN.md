# 09 — Statistical Sensitivity and Sequential Design Upgrade

You are Claude Opus acting as a senior CVPR research advisor, ML systems engineer, statistician, VLM evaluation scientist, reproducibility lead, and adversarial reviewer.

Repo:
/Users/saketmaganti/Projects/certVIC

Project:
CertVIC — Certified, Confound-Controlled Measurement of Visual Decision Updates in Vision-Language Models.

Hard constraints:
- No paid APIs.
- No paid cloud GPUs.
- No paid datasets.
- No paid annotation.
- No paid credits.
- Use local Mac/M4 CPU, Kaggle free GPU, Colab free fallback, public/free datasets, and open-source models only.
- No fake results, fake citations, or paper numbers not backed by real artifacts.
- No evidence claims from mock/smoke/synthetic/planned/unreviewed/simple-edit-only artifacts.
- Keep tests CPU/local.
- Heavy dependencies must be optional/import-safe.
- Do not weaken quality, detectability, evidence, leakage, claim, or paper-number gates.
- Do not initialize, commit, or tag unless explicitly asked.
- Keep all current results explicitly pilot-only unless the repo's evidence gates say otherwise.

Current real pilot facts to preserve:
- Same 91 reviewed presence/intervention items.
- Same 120 absent-object control items.
- Same protocol across Qwen2.5-VL-7B, InternVL2-8B, and LLaVA-OneVision-7B.
- Qwen2.5-VL-7B: a=0.923, p=0.176, Delta=0.747, CS lower bound=0.364, certified=true, absent control 60/60, present control 50/60.
- InternVL2-8B: a=0.923, p=0.099, Delta=0.824, CS lower bound=0.441, certified=true, absent control 58/60, present control 58/60.
- LLaVA-OneVision-7B: a=0.890, p=0.176, Delta=0.714, CS lower bound=0.331, certified=true, absent control 60/60, present control 58/60.
- The scientific core: open VLMs can detect natural absence, but often fail to revise after controlled low-detectability removals/edits.
- Current status: strong pilot, not paper-grade yet.
- Claude is already working separately on the spurious-flip/control_irrelevant arm. Do not duplicate that work; integrate its outputs only after they exist.

Before coding:
- Inspect existing files and commands.
- Reuse existing infrastructure.
- Do not invent paths.
- Explain briefly what you will do, then execute.

After coding:
- Run relevant CPU tests.
- Run security/privacy/claim guards if docs/results/reporting changed.
- Give exact commands and artifact paths.

## Motivation
The result is certified in the pilot. A larger study needs a preregistered sequential design, stopping rules, and sensitivity analyses.

## Task
Create a statistical sensitivity report and future-study sequential design around Delta = E[a_i - C_i].

## Create/update
- `docs/STATISTICAL_SENSITIVITY_MAIN_STUDY.md`
- `data/results/main_real_200/statistical_sensitivity.json`
- `scripts/main_study_power_and_stopping_plan.py`

## Include
- observed pilot effect sizes per model;
- conservative planning deltas;
- item-level optional-stopping CS plan;
- multiple-model reporting policy;
- per-family analysis policy;
- exclusion/sensitivity policy for human-review uncertainty;
- how to report controls;
- what not to certify.

## Hard rules
- Mark projections as projections.
- Do not use pilot estimates as guaranteed future effect sizes.
- Do not use naive fixed-n CI as the main claim.
- Do not change certification thresholds without explicit rationale.

## Validation
Run:
```bash
python3 -m pytest -q
python3 -m certvic.validation.claim_language_guard --paths docs data/results/main_real_200
```

## Final response
Give planned sample sizes, stopping rules, and conservative design recommendation.
