# 08 — Question Polarity and Prompt Ablations

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
The current v2 task set includes mixed positive and negated phrasing. A reviewer may argue that the effect depends on awkward prompt polarity.

## Task
Build prompt-ablation task manifests and scoring plans to test whether the effect survives cleaner question phrasing.

Do not run GPU inference unless explicitly asked.

## Ablations
Generate task files for the 91 reviewed items:
1. Positive-only question form:
   - “Is there a clearly visible {object} in the image? Answer yes or no.”
2. Negative-only form:
   - “Is the {object} absent from the image? Answer yes or no.”
3. Explicit pixel-only form:
   - “Answer from visible pixels only, not scene context: is there a clearly visible {object}?”
4. Short form:
   - “Visible {object}? yes/no.”

## Create/update
- `scripts/build_prompt_ablation_tasks.py`
- `data/results/main_real_200/prompt_ablations/`
- `docs/MAIN200_PROMPT_ABLATION_PLAN.md`

## Requirements
- Preserve original/edited image paths and gold answers correctly under polarity changes.
- Add a polarity validator: if question asks “absent,” yes/no gold must invert appropriately.
- Include task hashes and provenance.
- Distinct run labels for every ablation.

## Validation
Run:
```bash
python3 -m pytest -q
```

## Final response
Give generated ablation task counts and exact next GPU run instructions.
