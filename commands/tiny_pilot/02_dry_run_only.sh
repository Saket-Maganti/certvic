#!/usr/bin/env bash
set -euo pipefail

# Stage 02: ADE20K dry-run only. Do not generate edits or run VLM inference here.
python3 -m certvic.pipeline.run_tiny_pilot --config configs/real_pilot_ade20k.yaml --ade20k-root "${ADE20K_ROOT:?set ADE20K_ROOT}" --out-dir data/results/tiny_real_pilot --max-items 20 --seed 0 --dry-run
