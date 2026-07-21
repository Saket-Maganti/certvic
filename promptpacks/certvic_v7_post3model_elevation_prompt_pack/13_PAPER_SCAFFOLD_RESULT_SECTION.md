# 13 — Paper Scaffold: Pilot Result Section and Figure Plan

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
The result should be written up while it is fresh, but with strict pilot-only language and no overclaiming.

## Task
Draft a paper-style pilot result section and figure/table plan grounded only in canonical artifacts.

## Create/update
- `paper/sections/pilot_results_main200.tex` or markdown equivalent if LaTeX scaffold differs
- `paper/sections/limitations_current_pilot.tex` or markdown equivalent
- `docs/PAPER_FIGURE_TABLE_PLAN_POST3MODEL.md`

## Required content
- Method recap in 1 paragraph.
- 3-model result table.
- Absent-object control table.
- Per-edit-type discussion.
- Natural absence vs edited absence dissociation.
- Caveats:
  - pilot scale
  - single dataset
  - human review limitations
  - control_irrelevant pending
  - prompt polarity wart
  - residual cue concern
- “What this result does not show” subsection.

## Hard rules
- No citations unless already present and verified.
- No final paper claims.
- No unverifiable numbers.
- No “state of the art” language.
- Include artifact references/comments so numbers can be traced.

## Validation
Run:
```bash
python3 -m pytest -q
python3 -m certvic.validation.paper_numbers_guard --paths paper docs
python3 -m certvic.validation.claim_language_guard --paths paper docs
```

## Final response
Give changed paper files and exact claim language used.
