#!/usr/bin/env bash
set -euo pipefail
# Preflight (no heavy work)

python3 -m certvic.eval.vlm_preflight --config configs/tiny_reviewed_eval.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --provider qwen2_5_vl_7b --check-gpu
