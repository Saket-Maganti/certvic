# 07 — Human Review and IAA Upgrade

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
Current reviewed set likely has limited review depth. A CVPR-grade paper needs clearer human validation, inter-annotator agreement, and uncertainty handling.

## Task
Upgrade human review workflow for paper-grade validation while staying zero-cost.

## Create/update
- `docs/HUMAN_REVIEW_IAA_PROTOCOL.md`
- `scripts/export_second_rater_review.py`
- `scripts/compute_review_iaa.py`
- `data/results/main_real_200/review_iaa/`

## Requirements
Support:
- second-rater export for the same 91 items;
- blinded randomized order;
- no model result leakage in the review sheet by default;
- Cohen's kappa / simple agreement for pass/fail fields;
- item exclusion/sensitivity set if raters disagree;
- report that separates preliminary single-rater vs two-rater results.

## Fields
Include:
- photorealism
- single-factor
- target absent after edit
- answerability
- required answer change unambiguous
- residual target cue visible
- confidence
- notes

## Hard rules
- Do not auto-fill review.
- Do not fabricate reviewers.
- Do not overwrite existing review labels.
- Do not make paper-grade claims until completed IAA exists.

## Validation
Run:
```bash
python3 -m pytest -q
```

## Final response
Give review export paths and exact instructions for the second rater.
