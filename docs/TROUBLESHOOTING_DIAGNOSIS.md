# Troubleshooting Diagnosis

Offline static diagnosis; no external LLM used.

## GPU memory exhausted

Matched pattern: `CUDA out of memory`
Playbook: reduce max-items, shard more aggressively, or use 4-bit model loading
Next command: `python3 -m certvic.eval.run_matrix_planner --num-shards 8 ...`
