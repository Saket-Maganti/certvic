# V3 Prompt 02 — Dataset Root and Storage Planning Report

## Goal

Prevent disk blowups, private-path leaks, broken symlinks, duplicate output
roots, and release packaging mistakes before large studies.

## What was built

- `certvic/storage/path_policy.py` — `is_private_absolute`, `is_kaggle_safe` / `kaggle_unsafe_reason`, `is_symlink_escape`, `is_unsafe_overwrite_root`, `audit_path(s)`, and `collect_output_paths(config)`.
- `certvic/storage/dataset_roots.py` — recipe-first dataset-root policy (markdown + structured), opt-in `validate_root` that flags missing/non-dir/inside-repo roots **without scanning pixels**.
- `certvic/storage/plan_storage.py` — conservative per-category storage estimate at any scale, free-tier (Kaggle/Colab) fit checks, rejected-pixel and weight-cache warnings, and a path-policy audit of the config's declared outputs.

## Tests

`tests/test_v3_storage_planner.py` — 15 tests: private-path/Kaggle-name/symlink/overwrite-root detection, config output-path collection, scale monotonicity, large-scale + rejected-pixel warnings, real-config path audit (clean), JSON CLI output, dataset-root policy + validation (missing / inside-repo), and a no-heavy-import guard.

## Verification

- `python3 -m pytest -q` — full suite green (275 passed; was 260).
- CLI smoke: storage plans for scale 200 (~0.18 GB) and 2000 (~1.8 GB) both fit Kaggle's ~20 GB working disk; dataset-root policy doc written; config output paths audited clean.

## Evidence / cost discipline

No real dataset scanning (root validation never scans/copies pixels), no
downloads, no GPU, no paid services, no evidence claims. No heavy imports
(`torch`/`diffusers` not loaded).

## Status

**PASSED.**

## Remaining blockers

None. Estimates are intentionally conservative; once a real ADE20K root and a
chosen diffusion model are fixed, re-run with `--weights-cache-gb` set to the
actual cache size for a precise free-tier fit check.
