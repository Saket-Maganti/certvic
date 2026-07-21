#!/usr/bin/env bash
set -euo pipefail
# Preflight (no heavy work)

python3 -m certvic.edit.diffusion_preflight --edit-plan data/manifests/pilot_edit_plan.jsonl --engine diffusers_inpaint_optional --config configs/real_pilot_ade20k.yaml --weights-dir <WEIGHTS_DIR> --check-gpu
