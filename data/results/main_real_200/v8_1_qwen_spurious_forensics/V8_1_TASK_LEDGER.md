# V8.1 Task Ledger

`paper_evidence=false` `control_spurious_flip_max=0.10`

| Task | Status | Evidence | Summary |
| --- | --- | --- | --- |
| `V8_1_00_input_discovery` | DONE | `ARTIFACT_DISCOVERY_NON_EVIDENCE` | Inputs discovered. Repository folder is not a Git checkout; V8 spurious and newruns artifacts are present. |
| `V8_1_01_qwen_failure_extraction` | DONE | `REAL_ARTIFACT_RECOMPUTE_NON_EVIDENCE` | Extracted 12 Qwen flips from 94 paired items. |
| `V8_1_02_failure_gallery` | DONE | `FORENSIC_GALLERY_NON_EVIDENCE` | Built 12-item side-by-side gallery with copied local images, heatmaps, and overlays. |
| `V8_1_03_machine_preliminary_eval` | DONE | `CODEX_PRELIMINARY_EVAL_TRIAGE_ONLY` | Assigned CODEX_PRELIMINARY_EVAL triage labels: {'CODEX_PRELIM_PATCH_NEAR_TARGET': 6, 'CODEX_PRELIM_PATCH_TOO_SALIENT': 2, 'CODEX_PRELIM_OBJECT_REGION_AFFECTED': 2, 'CODEX_PRELIM_VALID_FAILURE': 2}. |
| `V8_1_04_rule_based_recompute` | DONE | `RULE_BASED_RECOMPUTE_NON_EVIDENCE` | Raw gate remains 12/94 = 0.1277; claim-valid pass exists: False. |
| `V8_1_05_cross_model_comparison` | DONE | `CROSS_MODEL_DIAGNOSTIC_NON_EVIDENCE` | Only-Qwen flips on Qwen-failed set: 12/12. |
| `V8_1_06_parser_and_provenance_audit` | DONE | `PROVENANCE_AUDIT_NON_EVIDENCE` | Rows/provider and pairing OK; issue could affect Qwen 12/94: False. |
| `V8_1_07_spurious_control_quality_audit` | DONE | `CPU_GEOMETRY_DIAGNOSTIC_NON_EVIDENCE` | Mask overlap items: 0; bbox-intersection items: 20. |
| `V8_1_08_stricter_spurious_v2_design` | DONE | `DESIGN_ONLY_NON_EVIDENCE` | Designed stricter V2 control and runbooks; no GPU run performed. |
| `V8_1_09_paper_claim_reframe` | DONE | `CLAIM_REFRAME_NON_EVIDENCE` | Wrote claim-safe text: Qwen fails specificity; clean all-model specificity is blocked. |
| `V8_1_10_go_nogo_decision` | DONE | `GO_NOGO_NON_EVIDENCE` | Decision: GO_HUMAN_AUDIT_FIRST; Main-500 should not start now. |
| `V8_1_11_tests_and_guards` | DONE | `VALIDATION_STATUS` | Test/guard logs detected. |

Main-500 should not start now. Qwen raw specificity remains failed unless resolved by real human review, a preregistered V2 control, or an honest paper reframe.
