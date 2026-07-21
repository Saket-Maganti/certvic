# CertVIC Canonical Artifact Index

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

Use this index before interpreting a similarly named historical report or package.

## Canonical and superseded artifacts

| Artifact ID | Repository-relative path | V11 class | Status |
|---|---|---|---|
| main91_task_manifest | data/results/main_real_200/pilot_eval_tasks_reviewed_v2.jsonl | MACHINE_ASSISTED_PRELIMINARY | canonical_with_v11_override |
| main91_taskitems | data/results/main_real_200/pilot_eval_taskitems_v2.jsonl | MACHINE_ASSISTED_PRELIMINARY | canonical_with_v11_override |
| v1_specificity_tasks | data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl | MACHINE_ASSISTED_PRELIMINARY | canonical_with_v11_override |
| main91_presence_qwen2_5_vl_7b | data/results/main_real_200/raw_predictions/presence__pred_qwen2_5_vl_7b_merged.jsonl | REAL_OBSERVED_EVIDENCE | canonical_raw |
| v1_specificity_qwen2_5_vl_7b | data/results/main_real_200/kaggle_spurious/pred_qwen2_5_vl_7b_spurious_merged.jsonl | REAL_OBSERVED_EVIDENCE | canonical_raw |
| pilot_report_qwen2_5_vl_7b | data/results/main_real_200/pilot_report/pilot_result.json | DERIVED_FROM_REAL_EVIDENCE | canonical_derived |
| main91_presence_internvl_8b | data/results/main_real_200/raw_predictions__internvl_8b/presence__pred_internvl_8b_presence_merged.jsonl | REAL_OBSERVED_EVIDENCE | canonical_raw |
| v1_specificity_internvl_8b | data/results/main_real_200/kaggle_spurious/pred_internvl_8b_spurious_merged.jsonl | REAL_OBSERVED_EVIDENCE | canonical_raw |
| pilot_report_internvl_8b | data/results/main_real_200/pilot_report__internvl_8b/pilot_result.json | DERIVED_FROM_REAL_EVIDENCE | canonical_derived |
| main91_presence_llava_onevision_7b | data/results/main_real_200/raw_predictions__llava_onevision_7b/presence__pred_llava_onevision_7b_presence_merged.jsonl | REAL_OBSERVED_EVIDENCE | canonical_raw |
| v1_specificity_llava_onevision_7b | data/results/main_real_200/kaggle_spurious/pred_llava_onevision_7b_spurious_merged.jsonl | REAL_OBSERVED_EVIDENCE | canonical_raw |
| pilot_report_llava_onevision_7b | data/results/main_real_200/pilot_report__llava_onevision_7b/pilot_result.json | DERIVED_FROM_REAL_EVIDENCE | canonical_derived |
| qwen_v1_failure_forensics | data/results/main_real_200/v8_1_qwen_spurious_forensics/qwen_spurious_failed_12.jsonl | DIAGNOSTIC_ONLY | canonical_diagnostic |
| spurious_v2_retrospective_tasks | data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl | DIAGNOSTIC_ONLY | retrospective_diagnostic_only |
| spurious_v2_kaggle_bundle | dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip | PLANNED_NOT_EXECUTED | canonical_execution_package |
| human_review_second_rater | data/results/main_real_200/review_iaa/second_rater_review_sheet.csv | HUMAN_REVIEW_PENDING | canonical_pending |
| v11_blinded_review_packet | reports/v11_full_ceiling_audit/human_review_packet/packet_manifest.json | HUMAN_REVIEW_PENDING | canonical_pending |
| main91_detectability_v11 | reports/v11_full_ceiling_audit/analysis/main91_detectability/detectability_summary.json | DIAGNOSTIC_ONLY | canonical_diagnostic |
| v2_retrospective_detectability_v11 | reports/v11_full_ceiling_audit/analysis/v2_retrospective_detectability/detectability_summary.json | DIAGNOSTIC_ONLY | canonical_diagnostic |
| main500_protocol | configs/certvic_v11_protocol.yaml | PLANNED_NOT_EXECUTED | canonical_protocol |
| synthetic_smoke_matrix | data/results/v1_1_smoke_matrix/mock_spurious_flip/predictions.jsonl | SYNTHETIC_TEST_FIXTURE | canonical_test_fixture |
| historical_v9_paper | paper/main_v9.tex | DEPRECATED_OR_STALE | superseded |
| v11_paper_draft | paper/main_v11.pdf | DERIVED_FROM_REAL_EVIDENCE | current_draft |

## Precedence rules

1. Raw prediction JSONL files outrank summaries when numerical values conflict.
2. `configs/certvic_v11_protocol.yaml` governs evidence classes and prospective decisions.
3. Embedded historical review labels in the task and prediction files are superseded by
   the hash-preserving mappings in that protocol.
4. `paper/main_v11.*` supersedes V9 prose but remains a non-eligible pilot draft.
5. The current V2 task package is canonical only as a retrospective diagnostic package;
   it is not the independent confirmatory set required by the protocol.
6. Historical and synthetic artifacts remain available for provenance and software testing,
   not as substitutes for missing real evidence.
