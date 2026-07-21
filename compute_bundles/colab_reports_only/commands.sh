#!/usr/bin/env bash
set -euo pipefail
# Run commands

python3 -m certvic.reporting.build_report --tasks data/manifests/tasks.jsonl --scores data/results/pair_scores.jsonl --preds data/predictions/run.jsonl --out-dir data/results/report --alpha 0.05 --gap-threshold 0.05
