# Model Run Matrix

Generated: 2026-06-22

Tasks: `data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl`  |  config: `configs/kaggle_open_vlm.yaml`
Cells: 12 (3 providers × 1 prompt variants × 4 shards)
Max items per shard run: 200

No inference is run here. Commands resume from existing predictions + run manifest.

## Providers

| Provider | Type | Cost | Evidence-eligible | GPU (full) | GPU (4-bit) |
| --- | --- | --- | --- | --- | --- |
| `qwen2_5_vl_7b` | open_local | zero_cost_open_local | True | 16.0 GB | 7.2 GB |
| `internvl_8b` | open_local | zero_cost_open_local | True | 18.0 GB | 8.1 GB |
| `llava_onevision_7b` | open_local | zero_cost_open_local | True | 16.0 GB | 7.2 GB |

## Run cells

| Run ID | Provider | Variant | Shard | Output |
| --- | --- | --- | --- | --- |
| `qwen2_5_vl_7b_default_s0of4` | qwen2_5_vl_7b | default | 0/4 | `data/predictions/qwen2_5_vl_7b/qwen2_5_vl_7b_default_s0of4.jsonl` |
| `qwen2_5_vl_7b_default_s1of4` | qwen2_5_vl_7b | default | 1/4 | `data/predictions/qwen2_5_vl_7b/qwen2_5_vl_7b_default_s1of4.jsonl` |
| `qwen2_5_vl_7b_default_s2of4` | qwen2_5_vl_7b | default | 2/4 | `data/predictions/qwen2_5_vl_7b/qwen2_5_vl_7b_default_s2of4.jsonl` |
| `qwen2_5_vl_7b_default_s3of4` | qwen2_5_vl_7b | default | 3/4 | `data/predictions/qwen2_5_vl_7b/qwen2_5_vl_7b_default_s3of4.jsonl` |
| `internvl_8b_default_s0of4` | internvl_8b | default | 0/4 | `data/predictions/internvl_8b/internvl_8b_default_s0of4.jsonl` |
| `internvl_8b_default_s1of4` | internvl_8b | default | 1/4 | `data/predictions/internvl_8b/internvl_8b_default_s1of4.jsonl` |
| `internvl_8b_default_s2of4` | internvl_8b | default | 2/4 | `data/predictions/internvl_8b/internvl_8b_default_s2of4.jsonl` |
| `internvl_8b_default_s3of4` | internvl_8b | default | 3/4 | `data/predictions/internvl_8b/internvl_8b_default_s3of4.jsonl` |
| `llava_onevision_7b_default_s0of4` | llava_onevision_7b | default | 0/4 | `data/predictions/llava_onevision_7b/llava_onevision_7b_default_s0of4.jsonl` |
| `llava_onevision_7b_default_s1of4` | llava_onevision_7b | default | 1/4 | `data/predictions/llava_onevision_7b/llava_onevision_7b_default_s1of4.jsonl` |
| `llava_onevision_7b_default_s2of4` | llava_onevision_7b | default | 2/4 | `data/predictions/llava_onevision_7b/llava_onevision_7b_default_s2of4.jsonl` |
| `llava_onevision_7b_default_s3of4` | llava_onevision_7b | default | 3/4 | `data/predictions/llava_onevision_7b/llava_onevision_7b_default_s3of4.jsonl` |
