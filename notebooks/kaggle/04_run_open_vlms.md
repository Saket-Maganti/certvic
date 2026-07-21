# 04 Run Open VLMs

Purpose: run open local VLM adapters on free Kaggle GPU.

Use:

```bash
python -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/tasks.jsonl --out data/predictions/kaggle_open_vlm.jsonl --provider qwen2_5_vl_7b --run-id kaggle_qwen_v1 --shard-index 0 --num-shards 1
```

Tips:

- enable 4-bit loading when needed
- cache weights in Kaggle working storage when permitted
- use sharding for parallel sessions
- JSONL predictions flush after every item
- no paid APIs or paid cloud fallback

## V2 preflight before inference

Run the preflight before loading any model on Kaggle free GPU:

```bash
python3 -m certvic.eval.vlm_preflight --provider qwen2_5_vl_7b \
  --config configs/tiny_reviewed_eval.yaml \
  --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl \
  --out data/results/vlm_preflight_qwen.json --check-gpu
```

Provider metadata (expected_gpu_memory_gb, supports_4bit, supports_batching) is in
`certvic.providers.registry.PROVIDER_METADATA`. Only open-local providers are
evidence-eligible; mock/baseline providers cannot produce evidence.

## Plan the run matrix first (V3)

Before burning free GPU, plan providers × shards and track completion so dead
sessions don't cause re-runs:

```bash
python3 -m certvic.eval.run_matrix_planner --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --providers qwen2_5_vl_7b internvl_8b llava_onevision_7b --out-dir data/results/model_run_matrix --max-items 200 --num-shards 4
python3 -m certvic.eval.run_status --matrix data/results/model_run_matrix/run_matrix.json --pred-root data/predictions --out data/results/model_run_matrix/status.json
```

`commands.sh` holds one resumable `run_eval` per cell; `run_status` shows which
cells still need running. See `docs/MODEL_RUN_MATRIX.md`.
