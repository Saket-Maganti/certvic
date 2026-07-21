#!/usr/bin/env bash
set -euo pipefail

# Stage 01: CPU readiness only. Stop and inspect outputs before moving on.
python3 -m certvic.v6.final_directional_audit --out docs/V6_FINAL_DIRECTIONAL_AUDIT.md --json-out data/results/v6_final_directional_audit.json
python3 -m certvic.pipeline.main_study_dry_run --scale 20 --out-dir data/results/main_study_dry_run_20
