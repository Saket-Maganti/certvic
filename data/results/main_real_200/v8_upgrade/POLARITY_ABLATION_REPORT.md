# V8 Prompt-Polarity Ablation Report

`status=complete` `evidence_status=DIAGNOSTIC_NON_EVIDENCE` `paper_evidence=false`

These are flat diagnostic predictions. Metrics below are parse rates, answer distributions, and row accuracy scored against the current deterministic task manifests.

| provider | family | rows | parse rate | row accuracy | pair update rate | both rows correct |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `qwen2_5_vl_7b` | negative | 182 | 1.0 | 0.544 | 0.0879 | 0.0879 |
| `qwen2_5_vl_7b` | pixel_only | 182 | 1.0 | 0.5824 | 0.1868 | 0.1758 |
| `qwen2_5_vl_7b` | positive | 182 | 1.0 | 0.6154 | 0.2308 | 0.2308 |
| `qwen2_5_vl_7b` | short | 182 | 0.7967 | 0.4396 | 0.0 | 0.0 |
| `internvl_8b` | negative | 182 | 1.0 | 0.522 | 0.044 | 0.044 |
| `internvl_8b` | pixel_only | 182 | 1.0 | 0.5714 | 0.1648 | 0.1538 |
| `internvl_8b` | positive | 182 | 1.0 | 0.5824 | 0.1868 | 0.1758 |
| `internvl_8b` | short | 182 | 0.0 | 0.0 | 0.0 | 0.0 |
| `llava_onevision_7b` | negative | 182 | 1.0 | 0.544 | 0.1319 | 0.1099 |
| `llava_onevision_7b` | pixel_only | 182 | 1.0 | 0.5604 | 0.1209 | 0.1209 |
| `llava_onevision_7b` | positive | 182 | 1.0 | 0.544 | 0.1538 | 0.1209 |
| `llava_onevision_7b` | short | 182 | 1.0 | 0.533 | 0.1319 | 0.0989 |

## Integrity

- `qwen2_5_vl_7b`: rows=728 expected=728 provider_ok=True duplicates=0 missing_task_gold=0 raw_gold_mismatches=360
- `internvl_8b`: rows=728 expected=728 provider_ok=True duplicates=0 missing_task_gold=0 raw_gold_mismatches=360
- `llava_onevision_7b`: rows=728 expected=728 provider_ok=True duplicates=0 missing_task_gold=0 raw_gold_mismatches=360

## Limits

- Diagnostic-only, not paper evidence.
- No accuracy metric is computed without task-manifest gold or a deterministic parse rule.
- Embedded raw-prediction gold is an audited provenance field, not the scoring authority.
