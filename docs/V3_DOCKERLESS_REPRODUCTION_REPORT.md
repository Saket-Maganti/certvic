# V3 Prompt 15 — Dockerless Reproduction Scripts Report

## Goal

Prepare normal-shell reproduction scripts for smoke, simulation, dry-run, and
reports without Docker or downloads by default.

## What was built

- `scripts/reproduce_smoke.sh` — tests + full CPU smoke pipeline (MOCK_ONLY).
- `scripts/reproduce_simulation.sh` — anytime-validity stress lab (SIMULATED_ONLY).
- `scripts/reproduce_tiny_pilot_dry_run.sh` — tiny pilot orchestrator dry-run; requires `ADE20K_ROOT` (fails fast if unset).
- `scripts/reproduce_reports.sh` — storage/scale plans, dashboard, number guard, reviewer simulation.
- `certvic/release/reproduction_audit.py` — static audit: shebang + `set -euo pipefail`, no destructive `rm -rf`, no paid/credential markers, dockerless, documented user paths; exits non-zero on violation.

All scripts use `set -euo pipefail` and are executable.

## Tests

`tests/test_v3_reproduction_scripts.py` — 10 tests: all 4 scripts exist + executable; shebang + strict mode; audit passes on the real scripts (no paid/destructive/Docker); dataset-root script documents the user path; audit flags destructive/paid/Docker and an undocumented dataset root; report renders; no heavy imports.

## Verification

- `python3 -m pytest -q` — full suite green (396 passed; was 386).
- Audit CLI: 4/4 scripts clean, `passed: true`. Executed `reproduce_smoke.sh` (exit 0, full CPU pipeline) and `reproduce_reports.sh` (exit 0) end-to-end on this machine.

## Evidence / cost discipline

No Docker, no downloads by default, no paid services. Smoke outputs are MOCK_ONLY,
simulation outputs SIMULATED_ONLY; neither is evidence. The dataset-root script is
dry-run only. No heavy imports.

## Status

**PASSED.**

## Remaining blockers

None. The dry-run pilot script needs a local `ADE20K_ROOT` to exercise (by design);
the smoke, simulation, and reports scripts run with no external inputs.
