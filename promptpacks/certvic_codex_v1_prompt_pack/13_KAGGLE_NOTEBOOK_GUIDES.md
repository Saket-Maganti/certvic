# Codex Prompt 13 — Kaggle Notebook Guides and Free-Compute Workflow

Create notebook-style markdown guides for running the project on free Kaggle GPU.

## Goal

The project must be practically runnable under:
- Kaggle free GPU quota
- 12-hour session cap
- limited persistent storage
- no paid services

Create clear guides. Do not create enormous notebooks with brittle outputs; use markdown command guides and small notebook placeholders.

## Files to create/update

```text
notebooks/kaggle/01_make_masks.md
notebooks/kaggle/02_generate_edits.md
notebooks/kaggle/03_quality_filter.md
notebooks/kaggle/04_run_open_vlms.md
notebooks/kaggle/05_run_free_tier_reference.md
notebooks/kaggle/06_build_reports.md
notebooks/kaggle/README.md
docs/REPRO.md
docs/ZERO_COST_POLICY.md
configs/kaggle_masks.yaml
configs/kaggle_edits.yaml
configs/kaggle_quality.yaml
```

## Guide requirements

Each guide should include:
- purpose
- expected inputs
- expected outputs
- commands
- resume behavior
- storage notes
- zero-cost warning
- failure recovery
- how to verify output

## 01_make_masks

Cover:
- using existing dense masks first
- optional SAM/Grounded-SAM
- no paid segmentation APIs
- cache weights
- write mask manifest

## 02_generate_edits

Cover:
- SD2 inpainting optional
- CPU smoke fallback
- batch size tips
- checkpoint after every batch
- write edit manifest

## 03_quality_filter

Cover:
- outside-mask change
- artifact score
- filtering thresholds
- human spot-check sample export

## 04_run_open_vlms

Cover:
- Qwen/InternVL/LLaVA adapters
- 4-bit loading
- sharding
- resume
- JSONL flushing
- no paid APIs

## 05_run_free_tier_reference

Cover:
- disabled by default
- only if genuinely free
- version-date everything
- reference-only, non-core
- never required for reproducibility
- no paid fallback

## 06_build_reports

Cover:
- score predictions
- metrics
- bootstrap
- confseq
- claim ledger
- failure gallery

## Configs

Add config files for:
- masks
- edits
- quality

Make them safe defaults with small pilot settings.

## Finish

Run:
```bash
python -m pytest -q
```

Report:
- files changed
- tests run
- next prompt: `14_PAPER_SCAFFOLD_CVPR_STYLE.md`
