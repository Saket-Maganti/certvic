# 02 — Multi-Model Report and Paper-Ready Tables

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
The 3-model result needs a paper-safe report and tables, not ad hoc chat summaries.

## Task
Create a provenance-aware multi-model pilot report that uses only canonical artifacts and emits paper-ready tables/figures with pilot-only language.

## Create/update
- `docs/MAIN200_MULTIMODEL_PILOT_REPORT.md`
- `data/results/main_real_200/tables/main200_multimodel_results.csv`
- `data/results/main_real_200/tables/main200_multimodel_results.tex`
- `data/results/main_real_200/tables/main200_control_results.csv`
- `data/results/main_real_200/tables/main200_per_edit_type.csv`
- optional simple figures under `data/results/main_real_200/figures/`

## Required tables
1. Model-level intervention table:
   - model
   - provider
   - n_items
   - original accuracy a
   - consistency p
   - Delta
   - CS lower
   - CS upper
   - certified
   - parse failures
2. Absent-object control table:
   - absent accuracy
   - present accuracy
   - n_absent/n_present
3. Per-edit-type table:
   - remove
   - occlude
   - displace
   - control_irrelevant if available; otherwise blocked/not_available

## Language rules
Use:
- “pilot”
- “evidence candidate” only if gates allow
- “certified under the pilot protocol”

Do not use:
- “final result”
- “paper-grade evidence”
- “proves VLMs fail”
- any claim unsupported by artifacts

## Validation
Run:
```bash
python3 -m pytest -q
python3 -m certvic.validation.paper_numbers_guard --paths docs data/results/main_real_200/tables
python3 -m certvic.validation.claim_language_guard --paths docs data/results/main_real_200
```

## Final response
List generated tables, exact values, and whether report is pilot-only.
