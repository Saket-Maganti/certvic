# 04 — Residual Cue and Human Edited-Absence Audit

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
Absent-object controls show models can perceive natural absence. The remaining mechanism concern is whether edited images contain subtle residual cues that humans miss but VLMs exploit, or whether models are context-anchored.

## Task
Create an audit workflow where humans explicitly judge edited images for residual target-object evidence.

This is separate from the original visual review. It asks: “After the edit, is any visible trace/sign of the target still present?”

## Create/update
- `scripts/export_residual_cue_review.py`
- `scripts/apply_residual_cue_review.py`
- `docs/MAIN200_RESIDUAL_CUE_REVIEW_INSTRUCTIONS.md`
- `data/results/main_real_200/residual_cue_review/`

## Review columns
- item_id
- edit_id
- model_fail_count if available across models
- original_image_path
- edited_image_path
- target_object
- edit_type
- residual_target_visible: yes/no/uncertain
- residual_type: none / silhouette / texture / shadow / partial object / context-only / other
- human_absence_confident: yes/no/uncertain
- notes
- reviewer_id

## Analysis after review exists
Implement a summarizer that reports:
- residual cue rate
- model failure rate when human_absence_confident=yes
- per-edit-type breakdown
- uncertain rows to exclude from strong claims

## Hard rules
- Do not auto-fill human labels.
- Do not treat unreviewed rows as evidence.
- Do not remove items from the canonical pilot result unless explicitly asked; produce an alternate sensitivity report.

## Validation
Run:
```bash
python3 -m pytest -q
```

## Final response
Give review export path, row counts, and exact human review workflow.
