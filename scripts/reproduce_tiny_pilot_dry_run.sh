#!/usr/bin/env bash
set -euo pipefail
# CertVIC: reproduce the tiny real-pilot orchestrator in DRY-RUN mode.
# No GPU, no downloads, no paid services, no model inference. This plans the
# pilot without generating edits or running models.
#
# REQUIRED USER-PROVIDED PATH:
#   ADE20K_ROOT - absolute path to your local ADE20K directory (pixels are never
#   rehosted; CertVIC only reads them locally). Example:
#     export ADE20K_ROOT=/path/to/ADEChallengeData2016
: "${ADE20K_ROOT:?set ADE20K_ROOT to your local ADE20K directory before running}"

python3 -m certvic.pipeline.run_tiny_pilot \
  --config configs/real_pilot_ade20k.yaml \
  --ade20k-root "${ADE20K_ROOT}" \
  --out-dir data/results/tiny_real_pilot \
  --dry-run

echo "Tiny pilot DRY-RUN complete. No edits generated, no models run, no evidence produced."
