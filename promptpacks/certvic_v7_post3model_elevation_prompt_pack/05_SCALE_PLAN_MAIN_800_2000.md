# 05 — Scale Plan: Main-800 to Main-2000 Without Breaking Gates

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
The current n=91 pilot is strong but too small for a full CVPR claim. Scaling must preserve validity, not just generate more images.

## Task
Create a scale plan and command generator for a larger real run with explicit stop/go gates.

Do not run large GPU jobs. Do not create fake expected results.

## Targets
Support plans for:
- main_500
- main_800
- main_1000
- main_2000

## Create/update
- `docs/SCALE_PLAN_MAIN_800_2000.md`
- `scripts/plan_scaled_main_run.py`
- `data/results/scale_plans/`
- Kaggle shard plan templates under `commands/scale/`

## Requirements
For each target size estimate:
- source items required
- planned edits
- expected reviewed survivors based on observed pilot survival rate, clearly marked as projection not result
- GPU sessions required for diffusion
- GPU sessions required per model
- human review hours
- storage footprint
- cost: must be zero-cost/free-tier only

## Stop/go gates
Scaling must halt if:
- detectability AUC exceeds threshold;
- human review pass rate collapses;
- controls fail;
- parse failures exceed threshold;
- result ledger cannot hash all artifacts.

## Avoid
- Do not launch GPU jobs.
- Do not weaken quality or detectability thresholds.
- Do not use generated projections as paper numbers.

## Validation
Run:
```bash
python3 -m pytest -q
python3 -m certvic.validation.claim_language_guard --paths docs data/results/scale_plans
```

## Final response
Give scale plan paths, estimated runtime/storage, and exact first safe scale command.
