# OOM and Resume

The prospective recovery order is fixed: reduce batch size; switch to the already approved attention implementation; use the conservative locked dtype/config; run the two logical shards sequentially on one T4; then stop and report. Never change prompts, task membership, expected answers, decoding rules, thresholds, or analysis policy to make a run finish.

On OOM, preserve shard outputs, runtime events, environment/snapshot/code identities, logs, and resume ledger. Confirm the process released the model and cleared CUDA state. Restart the kernel when native allocations remain, reattach the same datasets, and rerun with the same run identity. Completed shards are skipped only after exact validation.

For partial or corrupt shards, delete no final evidence. Quarantine the invalid shard file, retain its logs, and rerun only that deterministic shard. Disk-full failures require removing disposable caches or unused attached datasets, not scientific artifacts. ZIP promotion is atomic; an existing final ZIP with a committed permission is immutable, while a temporary/failed package may be retried from the same verified outputs.

