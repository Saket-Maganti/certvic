#!/usr/bin/env bash
set -euo pipefail
# Generated CertVIC model run matrix commands.

# qwen2_5_vl_7b_default_s0of4 (mem ~7.2 GB 4-bit)
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/predictions/qwen2_5_vl_7b/qwen2_5_vl_7b_default_s0of4.jsonl --provider qwen2_5_vl_7b --run-id qwen2_5_vl_7b_default_s0of4 --max-items 200 --shard-index 0 --num-shards 4 --evidence-run
# qwen2_5_vl_7b_default_s1of4 (mem ~7.2 GB 4-bit)
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/predictions/qwen2_5_vl_7b/qwen2_5_vl_7b_default_s1of4.jsonl --provider qwen2_5_vl_7b --run-id qwen2_5_vl_7b_default_s1of4 --max-items 200 --shard-index 1 --num-shards 4 --evidence-run
# qwen2_5_vl_7b_default_s2of4 (mem ~7.2 GB 4-bit)
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/predictions/qwen2_5_vl_7b/qwen2_5_vl_7b_default_s2of4.jsonl --provider qwen2_5_vl_7b --run-id qwen2_5_vl_7b_default_s2of4 --max-items 200 --shard-index 2 --num-shards 4 --evidence-run
# qwen2_5_vl_7b_default_s3of4 (mem ~7.2 GB 4-bit)
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/predictions/qwen2_5_vl_7b/qwen2_5_vl_7b_default_s3of4.jsonl --provider qwen2_5_vl_7b --run-id qwen2_5_vl_7b_default_s3of4 --max-items 200 --shard-index 3 --num-shards 4 --evidence-run
# internvl_8b_default_s0of4 (mem ~8.1 GB 4-bit)
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/predictions/internvl_8b/internvl_8b_default_s0of4.jsonl --provider internvl_8b --run-id internvl_8b_default_s0of4 --max-items 200 --shard-index 0 --num-shards 4 --evidence-run
# internvl_8b_default_s1of4 (mem ~8.1 GB 4-bit)
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/predictions/internvl_8b/internvl_8b_default_s1of4.jsonl --provider internvl_8b --run-id internvl_8b_default_s1of4 --max-items 200 --shard-index 1 --num-shards 4 --evidence-run
# internvl_8b_default_s2of4 (mem ~8.1 GB 4-bit)
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/predictions/internvl_8b/internvl_8b_default_s2of4.jsonl --provider internvl_8b --run-id internvl_8b_default_s2of4 --max-items 200 --shard-index 2 --num-shards 4 --evidence-run
# internvl_8b_default_s3of4 (mem ~8.1 GB 4-bit)
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/predictions/internvl_8b/internvl_8b_default_s3of4.jsonl --provider internvl_8b --run-id internvl_8b_default_s3of4 --max-items 200 --shard-index 3 --num-shards 4 --evidence-run
# llava_onevision_7b_default_s0of4 (mem ~7.2 GB 4-bit)
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/predictions/llava_onevision_7b/llava_onevision_7b_default_s0of4.jsonl --provider llava_onevision_7b --run-id llava_onevision_7b_default_s0of4 --max-items 200 --shard-index 0 --num-shards 4 --evidence-run
# llava_onevision_7b_default_s1of4 (mem ~7.2 GB 4-bit)
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/predictions/llava_onevision_7b/llava_onevision_7b_default_s1of4.jsonl --provider llava_onevision_7b --run-id llava_onevision_7b_default_s1of4 --max-items 200 --shard-index 1 --num-shards 4 --evidence-run
# llava_onevision_7b_default_s2of4 (mem ~7.2 GB 4-bit)
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/predictions/llava_onevision_7b/llava_onevision_7b_default_s2of4.jsonl --provider llava_onevision_7b --run-id llava_onevision_7b_default_s2of4 --max-items 200 --shard-index 2 --num-shards 4 --evidence-run
# llava_onevision_7b_default_s3of4 (mem ~7.2 GB 4-bit)
python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/predictions/llava_onevision_7b/llava_onevision_7b_default_s3of4.jsonl --provider llava_onevision_7b --run-id llava_onevision_7b_default_s3of4 --max-items 200 --shard-index 3 --num-shards 4 --evidence-run
