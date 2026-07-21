# T4×2 Parallel Execution

Heavy notebooks call the common topology contract before model load. Two NVIDIA T4 devices select two independent concurrent workers, one per deterministic hash shard, each pinned with `CUDA_VISIBLE_DEVICES`. One T4 selects the validated sequential fallback: the same two logical shards run in order on GPU 0. Zero GPUs or an unexpected accelerator fails before model load. 00C2 intentionally uses one logical shard because its contract contains exactly two smoke tasks.

Seeds form a prospective hash hierarchy: global → study → provider → GPU → shard → task → generation attempt. The output `seed_manifest.json` records every derived value and collision check. Sharding and seeds do not depend on model answers, failures, or metrics.

Each shard owns separate predictions/generated artifacts, logs, runtime events, and resume state. Resume skips a shard only if its exact item universe, row count, identities, and provenance validate. Merge rejects missing/extra/duplicate item-variant keys and runs only after every shard passes. Independent sharding is used instead of DDP.

Progress should report completed/expected items, shard state, elapsed time, peak VRAM, OOM events, and output-disk use. Preserve `/kaggle/working` on failure and rerun the same notebook/config; do not change prompts, items, expected answers, filters, or scientific rules.

