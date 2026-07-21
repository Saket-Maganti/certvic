# Outputs matrix

| RUN_TAG | shard files | merged file to ingest | zip to download |
|---|---|---|---|
| spurious | `pred_<provider>_spurious_shard0.jsonl`, `pred_<provider>_spurious_shard1.jsonl` | `pred_<provider>_spurious_merged.jsonl` | `<provider>_spurious_preds.zip` |
| perception_scaled | `pred_<provider>_perception_scaled_shard0.jsonl`, `pred_<provider>_perception_scaled_shard1.jsonl` | `pred_<provider>_perception_scaled_merged.jsonl` | `<provider>_perception_scaled_preds.zip` |
| polarity | `pred_<provider>_polarity_shard0.jsonl`, `pred_<provider>_polarity_shard1.jsonl` | `pred_<provider>_polarity.jsonl` | `<provider>_polarity_preds.zip` |
| mechanism | `pred_<provider>_mechanism_shard0.jsonl`, `pred_<provider>_mechanism_shard1.jsonl` | `pred_<provider>_mechanism.jsonl` | `<provider>_mechanism_preds.zip` |

Each zip also includes `log_<provider>_<run_tag>_shard*.txt`,
`summary_<provider>_<run_tag>.json`, and
`runtime_manifest_<provider>_<run_tag>.json`. Model caches and weights are not zipped.
