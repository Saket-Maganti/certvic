#!/usr/bin/env bash
set -euo pipefail

# Stage 05: VLM eval only AFTER detectability, quality, human review, and certificates pass.
# Review docs/TINY_PILOT_GO_NO_GO.md and data/results/tiny_pilot_go_no_go.json before running.
python3 -m certvic.eval.run_matrix_planner --tasks data/results/tiny_real_pilot/pilot_eval_tasks_reviewed.jsonl --providers qwen2_5_vl_7b internvl_8b llava_onevision_7b --out-dir data/results/tiny_real_pilot/model_run_matrix --config configs/kaggle_open_vlm.yaml --pred-root data/predictions/tiny_real_pilot --max-items 20 --num-shards 2
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/results/tiny_real_pilot/pilot_eval_tasks_reviewed.jsonl --out data/predictions/tiny_real_pilot/qwen2_5_vl_7b_shard0.jsonl --provider qwen2_5_vl_7b --run-id tiny_pilot_qwen2_5_vl_7b_shard0 --max-items 20 --shard-index 0 --num-shards 2 --dry-run --strict-leakage --fail-fast
