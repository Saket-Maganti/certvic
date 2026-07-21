# V9 Task Ledger

| Task ID | Status | Evidence status | Summary | Next action |
| --- | --- | --- | --- | --- |
| `V9_00_orientation` | DONE | `BOOTSTRAP_FROM_EXISTING_REAL_ARTIFACTS` | V9 root created; master state records Qwen 12/94 gate failure and Main-500 blocked status. | Run V9_01 preliminary label hygiene migration. |
| `V9_01_prelim_label_hygiene` | DONE | `HYGIENE_REPAIR_ONLY_NO_NEW_RESULTS` | Migrated unsafe preliminary machine label namespace; total replacements 163; Qwen gate unchanged. | Run V9_02 Qwen failure human review packet. |
| `V9_02_qwen_failure_human_review_packet` | BLOCKED | `PENDING_REAL_HUMAN_REVIEW` | Created 12-item review packet with blank human fields; apply script refuses blank sheet and writes blocked report. | Run V9_03 stricter spurious V2 control builder. |
| `V9_03_spurious_v2_builder` | PARTIAL | `DATASET_ONLY_NO_VLM_RESULTS` | Built strict local Spurious V2 dataset with 30 feasible items from 94 local V1 candidates; requested 200-300 is blocked by local candidate pool. | Run V9_04 to prepare T4x2 VLM runbooks for Spurious V2. |
| `V9_04_spurious_v2_t4x2_runbooks` | BLOCKED | `GPU_DEFERRED_RUNBOOK_READY` | Prepared three provider-specific Kaggle T4x2 Spurious V2 notebooks with setup/input validation/execution/output validation/packaging/import/runtime sections. | Run V9_05 ingest gate after Kaggle outputs are downloaded. |
| `V9_05_spurious_v2_ingest_gate_decision` | BLOCKED | `BLOCKED_MISSING_REAL_KAGGLE_OUTPUTS` | No Spurious V2 provider outputs were found; importer writes explicit missing-predictions blocker and has tested scoring path for future real files. | Run V9_06 model-dependent specificity reframe while V2 remains pending. |
| `V9_06_model_dependent_reframe` | DONE | `CLAIM_LANGUAGE_REFRAME_ONLY` | Rendered model-dependent specificity branch because Qwen V1 failed and Spurious V2 predictions are missing. | Run V9_07 Main-500 go/no-go after specificity branch. |
| `V9_07_main500_go_nogo` | DONE | `GO_NOGO_CONTROL_DECISION_ONLY` | Main-500 decision is HOLD_FOR_SPURIOUS_V2; Main-500 must not start from current evidence state. | Run V9_08 planning only; no Main-500 execution. |
| `V9_08_main500_cpu_planning` | BLOCKED | `BLOCKED_MAIN500_GATE_NOT_GO` | Main-500 planning blocked by HOLD_FOR_SPURIOUS_V2 gate. | See V9_FINAL_HANDOFF.md |
| `V9_09_main500_diffusion_pack` | BLOCKED | `GPU_DEFERRED_GATED_RUNBOOK_READY` | Created gated Main-500 diffusion notebook/runbook; execution blocked without planning. | See V9_FINAL_HANDOFF.md |
| `V9_10_main500_quality_review_export` | BLOCKED | `BLOCKED_MISSING_DIFFUSION_OUTPUTS` | Recorded missing diffusion outputs and blank review gallery status. | See V9_FINAL_HANDOFF.md |
| `V9_11_main500_human_validation_iaa` | BLOCKED | `BLOCKED_NO_RATER_LABELS` | Created blank rater sheets and scripts that refuse missing labels. | See V9_FINAL_HANDOFF.md |
| `V9_12_main500_vlm_eval_pack` | BLOCKED | `GPU_DEFERRED_GATED_RUNBOOK_READY` | Created gated Main-500 VLM notebooks/runbook; blocked pending approved review. | See V9_FINAL_HANDOFF.md |
| `V9_13_main500_ingest_certification` | BLOCKED | `BLOCKED_MISSING_MAIN500_VLM_OUTPUTS` | Recorded Main-500 certification/table blocker. | See V9_FINAL_HANDOFF.md |
| `V9_14_second_domain_mini_run` | PARTIAL | `PLAN_ONLY_NO_RESULTS` | Prepared optional second-domain plan and gated notebooks. | See V9_FINAL_HANDOFF.md |
| `V9_15_mechanism_polarity_deep_analysis` | DONE | `DIAGNOSTIC_ONLY_NO_CERTIFICATION_EVIDENCE` | Generated diagnostic-only polarity/mechanism reports. | See V9_FINAL_HANDOFF.md |
| `V9_16_statistical_inference_power_lock` | DONE | `PLAN_LOCK_NO_NEW_RESULTS` | Locked inference and power plan without weakening thresholds. | See V9_FINAL_HANDOFF.md |
| `V9_17_failure_taxonomy_gallery_final` | DONE | `EXISTING_ARTIFACT_QUALITATIVE_ONLY` | Built deterministic failure taxonomy/gallery from existing artifacts. | See V9_FINAL_HANDOFF.md |
| `V9_18_paper_compile_cvpr_scaffold` | DONE | `CLAIM_SAFE_PAPER_SCAFFOLD_COMPILED` | Generated and compiled V9 claim-safe paper scaffold to paper/main_v9.pdf. | See V9_FINAL_HANDOFF.md |
| `V9_19_release_privacy_reproducibility` | DONE | `RELEASE_CANDIDATE_NO_RESULTS_PROMOTION` | Created V9 release candidate zip and manifest. | See V9_FINAL_HANDOFF.md |
| `V9_20_reviewer_attack_rebuttal_sim` | DONE | `REVIEWER_RISK_REPORT` | Created reviewer attack harness and rebuttal skeleton. | See V9_FINAL_HANDOFF.md |
| `V9_21_cvpr_readiness_stop_conditions` | DONE | `READINESS_SCORECARD` | Recommendation HOLD_FOR_SPURIOUS_V2. | See V9_FINAL_HANDOFF.md |
| `V9_22_final_validation_handoff` | DONE | `FINAL_VALIDATED_HANDOFF` | Full pytest passed (657), claim guard passed, privacy audit passed, final handoff written. | See V9_FINAL_HANDOFF.md |
