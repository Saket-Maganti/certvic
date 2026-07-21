# 03 — Mechanism Probes: Context Anchoring vs Visual Update

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
The core result is robust across three models, but the mechanism is still open. A reviewer will ask: are models anchored by scene context, residual cues, or prompt priors?

## Task
Design and implement CPU-side task-generation support for mechanism probes that can be run later on Kaggle with the same VLM notebook style.

Do not run GPU inference unless explicitly asked. Do not fabricate results.

## Probe families
Create task manifests for the same reviewed 91 items where feasible:

1. Object-list probe
   - Prompt: “List the clearly visible objects in this image.”
   - Scoring later checks whether removed target is listed.
2. Region-focused probe
   - Use crop or bbox/mask-derived region around the edit area.
   - Prompt asks whether target object is visible in the region.
3. Two-step describe-then-answer probe
   - Prompt first asks for brief visual description, then yes/no.
4. Context-suppression prompt
   - Prompt explicitly warns: “Do not infer from scene context; answer only from visible pixels.”
5. Original-vs-edited forced comparison if both images can be shown to a model later; if current model interface is single-image only, just generate the planned spec and mark blocked.

## Create/update
- `scripts/build_mechanism_probe_tasks.py`
- `data/results/main_real_200/mechanism_probes/`
- `docs/MAIN200_MECHANISM_PROBES_PLAN.md`
- `notebooks/kaggle/` instructions or runbook update for future probe inference

## Requirements
- Every generated task must trace back to a reviewed item.
- Do not mark probes as evidence by default.
- Use distinct run labels.
- Include scoring specs, not fake results.
- Include a refusal if reviewed source tasks are missing.

## Validation
Run:
```bash
python3 -m pytest -q
```

## Final response
Give generated task counts, probe types, paths, and exact next GPU command/notebook steps if the user wants to run probes.
