#!/usr/bin/env bash
set -euo pipefail
# Run commands

python3 -m certvic.pipeline.run_tiny_eval --config configs/tiny_reviewed_eval.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --provider qwen2_5_vl_7b --out-dir data/results/tiny_eval_qwen --max-items 20
