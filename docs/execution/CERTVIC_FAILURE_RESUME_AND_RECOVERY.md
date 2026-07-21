# Failure, Resume, and Recovery

Workers write shard-local partial JSONL, validate exact keys, then atomically promote. A rerun skips
verified rows, quarantines a corrupt final line, reruns only missing/corrupt keys, and refuses a
conflicting completed output. OOM recovery halves the batch and clears cache; batch size 1 failure is
terminal. One completed shard is retained while the other resumes. Hash, revision, provider, run-tag,
image, task, duplicate, or variant mismatches are terminal until the input is corrected. A single T4
may run shards sequentially under the same contract. Raw archives and sheets are never overwritten.
