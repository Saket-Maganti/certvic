#!/usr/bin/env bash
set -euo pipefail

python3 scripts/build_spurious_flip_control.py \
  --ade20k-root ade20k_root/ADEChallengeData2016 \
  --out-dir data/edits/spurious_flip_control_v2 \
  --split training \
  --n-per 60

python3 -m certvic.validation.edit_detectability \
  --tasks data/edits/spurious_flip_control_v2/pilot_eval_tasks_reviewed.jsonl \
  --out-dir data/results/spurious_flip_control_v2/edit_detectability
