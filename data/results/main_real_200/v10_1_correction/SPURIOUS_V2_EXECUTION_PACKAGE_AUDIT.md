# Spurious V2 Execution Package Audit

Verdict: `READY_TO_RUN_ON_KAGGLE`
Ready to import results: `false`

## Core Counts

| Check | Value |
| --- | ---: |
| Expected strict V2 rows | 30 |
| Local task rows | 30 |
| Local image files | 60 |
| Zip task rows | 30 |
| Zip image files | 60 |

## Package Requirements

| Requirement | Status |
| --- | --- |
| Code bundle exists | `true` |
| Spurious V2 bundle exists | `true` |
| Zip is readable | `true` |
| Task JSONL exists in zip | `true` |
| Spurious V2 manifest exists in zip | `true` |
| Bundle manifest exists in zip | `true` |
| Row count equals strict V2 count | `true` |
| Image count equals two images per row | `true` |
| Notebooks valid and portable | `true` |
| Provider output names match importer expectations | `true` |
| `paper_evidence` remains false | `true` |

## Quality Carry-Forward

- Bbox overlap count: `0`
- Mask overlap count: `0`
- Min bbox distance: `75.0` px
- Quality pass: `True`
- Requested target: `200-300`
- Local status: `INSUFFICIENT_LOCAL_CANDIDATES_MAX_FEASIBLE_FILTERED_SET`

## Missing Runtime Outputs

- `qwen2_5_vl_7b`: missing Kaggle output zip / merged JSONL
- `internvl_8b`: missing Kaggle output zip / merged JSONL
- `llava_onevision_7b`: missing Kaggle output zip / merged JSONL

## Limitation

The package is ready to run on Kaggle, but it is not ready to import results until the three provider outputs are downloaded.
