# 11 — Artifact Release and Reproducibility Upgrade

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
If the result becomes a paper, reviewers and artifact evaluators will ask whether someone can reproduce the pipeline without private paths, paid APIs, or hidden notebooks.

## Task
Create a release-readiness plan and reproducibility capsule for the pilot artifacts.

## Create/update
- `docs/ARTIFACT_RELEASE_PLAN.md`
- `docs/REPRODUCE_MAIN200_PILOT.md`
- `scripts/audit_release_candidate.py` or update existing release audit
- `data/results/release_candidate_manifest.json`

## Include
- exact data dependencies;
- which artifacts can be released and which cannot;
- model-weight policy;
- Kaggle notebook reproduction steps;
- local scoring reproduction command;
- hash verification;
- privacy/path scan;
- license/provenance blockers;
- expected runtimes.

## Hard rules
- Do not package ADE20K pixels unless license allows and user explicitly requests.
- Do not package model weights.
- Do not leak local `/Users/...` paths.
- Do not include credentials or Kaggle tokens.
- Do not release unreviewed/raw private files.

## Validation
Run:
```bash
python3 -m pytest -q
python3 -m certvic.security.release_privacy_audit --path .
```

If the exact privacy audit CLI differs, inspect and use the correct one.

## Final response
Give release blockers, safe-to-release artifacts, and exact reproduction command list.
