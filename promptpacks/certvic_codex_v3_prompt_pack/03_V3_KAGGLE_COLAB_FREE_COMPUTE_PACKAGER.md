# CertVIC Codex V3 Prompt 03 — Kaggle/Colab Free-Compute Packager


## Global constraints

- Work in `/Users/saketmaganti/Projects/certVIC`.
- Do not initialize git, commit, or tag.
- Do not use paid APIs, paid cloud, paid datasets, paid annotation, paid credits, or paid tracking.
- Do not download large datasets or model weights.
- Do not run GPU jobs or VLM inference in tests.
- Do not fabricate results or insert fake paper numbers.
- Keep heavy dependencies optional and import-safe.
- Normal tests must run locally without GPU.
- Simulated/pre-run artifacts must be marked non-evidence and blocked from claims.
- Preserve backward compatibility and run `python3 -m pytest -q`.

## Goal

Prepare portable free-compute job bundles for diffusion edits, VLM inference, ablations, and report-only jobs without executing them.

## Inspect first

Kaggle notebook docs, Kaggle VLM config, diffusion preflight, VLM preflight, tiny eval pipeline.

## Build / modify

Create `certvic/compute/kaggle_packager.py`, `colab_packager.py`, `job_bundle.py`. Build job bundles with README, commands, preflight scripts, resume instructions, expected inputs/outputs, zero-cost policy, and file manifest.

## CLI commands to add or verify

`python3 -m certvic.compute.kaggle_packager --job diffusion_tiny --config configs/real_pilot_ade20k.yaml --out-dir compute_bundles/kaggle_diffusion_tiny`

`python3 -m certvic.compute.kaggle_packager --job vlm_tiny --config configs/tiny_reviewed_eval.yaml --out-dir compute_bundles/kaggle_vlm_tiny`

## Outputs / behavior

Support job types: diffusion_tiny, diffusion_200, vlm_tiny, vlm_200, ablations, reports_only. No credentials, no private pixels, no paid endpoints, no execution.

## Tests

Create or update:

`tests/test_v3_kaggle_colab_packager.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/FREE_COMPUTE_BUNDLES.md`, `docs/V3_KAGGLE_COLAB_PACKAGER_REPORT.md`; update Kaggle docs and `docs/REPRO.md`.

## Extra notes

Make bundles copy-safe but path-anonymized by default.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
