# Model Snapshot Failures

Build each snapshot with `scripts/build_model_snapshot_bundle.py` using one unified model/processor directory and exact 40-hex model and processor commits. The builder rejects missing configuration, weights, tokenizer/processor files, partial shards, symlinks, architecture mismatch, unmanifested files, hash mismatch, and local-files-only processor/config failure.

If a weight shard or index is missing, reacquire the complete immutable revision and rebuild from a new directory. Do not copy a shard from another revision. If tokenizer or processor loading fails, verify all tokenizer, preprocessor, chat-template, special-token, and remote-code files belong to the same revision. Internet fallback is prohibited.

If Kaggle reports a corrupt snapshot dataset, redownload the private dataset, verify the input ZIP locally, and rerun 00B. 00B must pass separately for Qwen2.5-VL-7B, InternVL2-8B, and LLaVA-OneVision-7B before pre-smoke permissions can be built. A declared Hub revision is not equivalent to local byte verification.

