# V3 Prompt 03 — Kaggle/Colab Free-Compute Packager Report

## Goal

Prepare portable free-compute job bundles for diffusion edits, VLM inference,
ablations, and report-only jobs without executing them.

## What was built

- `certvic/compute/job_bundle.py` — shared job specs for all six job types, `anonymize()` (collapses private absolute paths to `<LOCAL_PATH>`), a forbidden-marker safety scan (API keys / tokens / paid endpoints), and the bundle writer (README, commands.sh, preflight.sh, expected_inputs/outputs.md, ZERO_COST_POLICY.txt, manifest.json with file hashes and `evidence_status=JOB_PLANNED_ONLY`).
- `certvic/compute/kaggle_packager.py` — Kaggle wrapper (T4/P100, ~12 h, `/kaggle/input` read-only, `/kaggle/working` ~20 GB, internet off).
- `certvic/compute/colab_packager.py` — Colab wrapper (free T4, idle timeouts, `/content`, optional Drive).

## Tests

`tests/test_v3_kaggle_colab_packager.py` — 11 tests: all six job types build with required files; unknown job rejected; non-execution / non-evidence flags; default anonymization scrubs a private home subpath; `--no-anonymize`; forbidden-marker scan blocks (monkeypatched poison); `reports_only` is CPU; Kaggle vs Colab notes differ; resume instructions present; file hashes recorded; no heavy imports.

## Verification

- `python3 -m pytest -q` — full suite green (286 passed; was 275).
- CLI smoke: built `kaggle_diffusion_tiny`, `kaggle_vlm_tiny`, and `colab_reports_only` bundles under `compute_bundles/`; all `safe: true`, `evidence_status: JOB_PLANNED_ONLY`.

## Evidence / cost discipline

No execution, no downloads, no GPU, no paid services, no credentials, no pixels.
Bundles are planning artifacts marked `JOB_PLANNED_ONLY`; the safety scan refuses
to write a bundle containing any credential/paid marker. No heavy imports.

## Status

**PASSED.**

## Remaining blockers

None. The `diffusion_200` bundle references the diffusion job queue
(`docs/DIFFUSION_JOB_QUEUE.md`), which is built in V3 prompt 04; the command is
templated and inert until then.
