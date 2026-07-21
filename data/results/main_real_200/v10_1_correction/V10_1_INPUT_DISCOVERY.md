# V10.1 Input Discovery

Generated: `2026-07-09`

This is a precise inspection of the V10/V10.1 local artifact surface. Paths are rendered relative to `<PROJECT_ROOT>` where applicable.

## Commands Run

### pwd

```bash
pwd
```

Return code: `0`

```text
<PROJECT_ROOT>
```

### results_tail

```bash
find data/results -maxdepth 4 -type f | sort | tail -200
```

Return code: `0`

```text
data/results/v2_1_sim_matrix/family_specific_failure/v2_report/claim_ledger.json
data/results/v2_1_sim_matrix/family_specific_failure/v2_report/control_edit_table.csv
data/results/v2_1_sim_matrix/family_specific_failure/v2_report/figure_manifest.json
data/results/v2_1_sim_matrix/family_specific_failure/v2_report/main_results_table.csv
data/results/v2_1_sim_matrix/family_specific_failure/v2_report/main_results_table.tex
data/results/v2_1_sim_matrix/family_specific_failure/v2_report/parser_sensitivity_table.csv
data/results/v2_1_sim_matrix/family_specific_failure/v2_report/report.md
data/results/v2_1_sim_matrix/family_specific_failure/v2_report/v2_report_summary.json
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/scenario_config.json
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/simulated_pair_scores.jsonl
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/simulated_predictions.jsonl
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/simulated_run_metadata.json
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/simulated_tasks.jsonl
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/v2_report/by_domain_table.csv
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/v2_report/by_edit_type_table.csv
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/v2_report/by_family_table.csv
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/v2_report/by_family_table.tex
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/v2_report/certification_table.csv
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/v2_report/claim_ledger.json
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/v2_report/control_edit_table.csv
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/v2_report/figure_manifest.json
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/v2_report/main_results_table.csv
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/v2_report/main_results_table.tex
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/v2_report/parser_sensitivity_table.csv
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/v2_report/report.md
data/results/v2_1_sim_matrix/high_accuracy_low_consistency/v2_report/v2_report_summary.json
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/scenario_config.json
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/simulated_pair_scores.jsonl
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/simulated_predictions.jsonl
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/simulated_run_metadata.json
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/simulated_tasks.jsonl
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/v2_report/by_domain_table.csv
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/v2_report/by_edit_type_table.csv
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/v2_report/by_family_table.csv
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/v2_report/by_family_table.tex
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/v2_report/certification_table.csv
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/v2_report/claim_ledger.json
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/v2_report/control_edit_table.csv
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/v2_report/figure_manifest.json
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/v2_report/main_results_table.csv
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/v2_report/main_results_table.tex
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/v2_report/parser_sensitivity_table.csv
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/v2_report/report.md
data/results/v2_1_sim_matrix/low_accuracy_high_consistency/v2_report/v2_report_summary.json
data/results/v2_1_sim_matrix/noisy_realistic_mixed/scenario_config.json
data/results/v2_1_sim_matrix/noisy_realistic_mixed/simulated_pair_scores.jsonl
data/results/v2_1_sim_matrix/noisy_realistic_mixed/simulated_predictions.jsonl
data/results/v2_1_sim_matrix/noisy_realistic_mixed/simulated_run_metadata.json
data/results/v2_1_sim_matrix/noisy_realistic_mixed/simulated_tasks.jsonl
data/results/v2_1_sim_matrix/noisy_realistic_mixed/v2_report/by_domain_table.csv
data/results/v2_1_sim_matrix/noisy_realistic_mixed/v2_report/by_edit_type_table.csv
data/results/v2_1_sim_matrix/noisy_realistic_mixed/v2_report/by_family_table.csv
data/results/v2_1_sim_matrix/noisy_realistic_mixed/v2_report/by_family_table.tex
data/results/v2_1_sim_matrix/noisy_realistic_mixed/v2_report/certification_table.csv
data/results/v2_1_sim_matrix/noisy_realistic_mixed/v2_report/claim_ledger.json
data/results/v2_1_sim_matrix/noisy_realistic_mixed/v2_report/control_edit_table.csv
data/results/v2_1_sim_matrix/noisy_realistic_mixed/v2_report/figure_manifest.json
data/results/v2_1_sim_matrix/noisy_realistic_mixed/v2_report/main_results_table.csv
data/results/v2_1_sim_matrix/noisy_realistic_mixed/v2_report/main_results_table.tex
data/results/v2_1_sim_matrix/noisy_realistic_mixed/v2_report/parser_sensitivity_table.csv
data/results/v2_1_sim_matrix/noisy_realistic_mixed/v2_report/report.md
data/results/v2_1_sim_matrix/noisy_realistic_mixed/v2_report/v2_report_summary.json
data/results/v2_1_sim_matrix/null_gap/scenario_config.json
data/results/v2_1_sim_matrix/null_gap/simulated_pair_scores.jsonl
data/results/v2_1_sim_matrix/null_gap/simulated_predictions.jsonl
data/results/v2_1_sim_matrix/null_gap/simulated_run_metadata.json
data/results/v2_1_sim_matrix/null_gap/simulated_tasks.jsonl
data/results/v2_1_sim_matrix/null_gap/v2_report/by_domain_table.csv
data/results/v2_1_sim_matrix/null_gap/v2_report/by_edit_type_table.csv
data/results/v2_1_sim_matrix/null_gap/v2_report/by_family_table.csv
data/results/v2_1_sim_matrix/null_gap/v2_report/by_family_table.tex
data/results/v2_1_sim_matrix/null_gap/v2_report/certification_table.csv
data/results/v2_1_sim_matrix/null_gap/v2_report/claim_ledger.json
data/results/v2_1_sim_matrix/null_gap/v2_report/control_edit_table.csv
data/results/v2_1_sim_matrix/null_gap/v2_report/figure_manifest.json
data/results/v2_1_sim_matrix/null_gap/v2_report/main_results_table.csv
data/results/v2_1_sim_matrix/null_gap/v2_report/main_results_table.tex
data/results/v2_1_sim_matrix/null_gap/v2_report/parser_sensitivity_table.csv
data/results/v2_1_sim_matrix/null_gap/v2_report/report.md
data/results/v2_1_sim_matrix/null_gap/v2_report/v2_report_summary.json
data/results/v2_1_sim_matrix/parse_failure_heavy/scenario_config.json
data/results/v2_1_sim_matrix/parse_failure_heavy/simulated_pair_scores.jsonl
data/results/v2_1_sim_matrix/parse_failure_heavy/simulated_predictions.jsonl
data/results/v2_1_sim_matrix/parse_failure_heavy/simulated_run_metadata.json
data/results/v2_1_sim_matrix/parse_failure_heavy/simulated_tasks.jsonl
data/results/v2_1_sim_matrix/parse_failure_heavy/v2_report/by_domain_table.csv
data/results/v2_1_sim_matrix/parse_failure_heavy/v2_report/by_edit_type_table.csv
data/results/v2_1_sim_matrix/parse_failure_heavy/v2_report/by_family_table.csv
data/results/v2_1_sim_matrix/parse_failure_heavy/v2_report/by_family_table.tex
data/results/v2_1_sim_matrix/parse_failure_heavy/v2_report/certification_table.csv
data/results/v2_1_sim_matrix/parse_failure_heavy/v2_report/claim_ledger.json
data/results/v2_1_sim_matrix/parse_failure_heavy/v2_report/control_edit_table.csv
data/results/v2_1_sim_matrix/parse_failure_heavy/v2_report/figure_manifest.json
data/results/v2_1_sim_matrix/parse_failure_heavy/v2_report/main_results_table.csv
data/results/v2_1_sim_matrix/parse_failure_heavy/v2_report/main_results_table.tex
data/results/v2_1_sim_matrix/parse_failure_heavy/v2_report/parser_sensitivity_table.csv
data/results/v2_1_sim_matrix/parse_failure_heavy/v2_report/report.md
data/results/v2_1_sim_matrix/parse_failure_heavy/v2_report/v2_report_summary.json
data/results/v2_1_sim_matrix/perfect_consistent/scenario_config.json
data/results/v2_1_sim_matrix/perfect_consistent/simulated_pair_scores.jsonl
data/results/v2_1_sim_matrix/perfect_consistent/simulated_predictions.jsonl
data/results/v2_1_sim_matrix/perfect_consistent/simulated_run_metadata.json
data/results/v2_1_sim_matrix/perfect_consistent/simulated_tasks.jsonl
data/results/v2_1_sim_matrix/perfect_consistent/v2_report/by_domain_table.csv
data/results/v2_1_sim_matrix/perfect_consistent/v2_report/by_edit_type_table.csv
data/results/v2_1_sim_matrix/perfect_consistent/v2_report/by_family_table.csv
data/results/v2_1_sim_matrix/perfect_consistent/v2_report/by_family_table.tex
data/results/v2_1_sim_matrix/perfect_consistent/v2_report/certification_table.csv
data/results/v2_1_sim_matrix/perfect_consistent/v2_report/claim_ledger.json
data/results/v2_1_sim_matrix/perfect_consistent/v2_report/control_edit_table.csv
data/results/v2_1_sim_matrix/perfect_consistent/v2_report/figure_manifest.json
data/results/v2_1_sim_matrix/perfect_consistent/v2_report/main_results_table.csv
data/results/v2_1_sim_matrix/perfect_consistent/v2_report/main_results_table.tex
data/results/v2_1_sim_matrix/perfect_consistent/v2_report/parser_sensitivity_table.csv
data/results/v2_1_sim_matrix/perfect_consistent/v2_report/report.md
data/results/v2_1_sim_matrix/perfect_consistent/v2_report/v2_report_summary.json
data/results/v2_1_sim_matrix/scenario_matrix_report.md
data/results/v2_1_sim_matrix/scenario_matrix_summary.csv
data/results/v2_1_sim_matrix/scenario_matrix_summary.json
data/results/v2_1_sim_matrix/small_gap_borderline/scenario_config.json
data/results/v2_1_sim_matrix/small_gap_borderline/simulated_pair_scores.jsonl
data/results/v2_1_sim_matrix/small_gap_borderline/simulated_predictions.jsonl
data/results/v2_1_sim_matrix/small_gap_borderline/simulated_run_metadata.json
data/results/v2_1_sim_matrix/small_gap_borderline/simulated_tasks.jsonl
data/results/v2_1_sim_matrix/small_gap_borderline/v2_report/by_domain_table.csv
data/results/v2_1_sim_matrix/small_gap_borderline/v2_report/by_edit_type_table.csv
data/results/v2_1_sim_matrix/small_gap_borderline/v2_report/by_family_table.csv
data/results/v2_1_sim_matrix/small_gap_borderline/v2_report/by_family_table.tex
data/results/v2_1_sim_matrix/small_gap_borderline/v2_report/certification_table.csv
data/results/v2_1_sim_matrix/small_gap_borderline/v2_report/claim_ledger.json
data/results/v2_1_sim_matrix/small_gap_borderline/v2_report/control_edit_table.csv
data/results/v2_1_sim_matrix/small_gap_borderline/v2_report/figure_manifest.json
data/results/v2_1_sim_matrix/small_gap_borderline/v2_report/main_results_table.csv
data/results/v2_1_sim_matrix/small_gap_borderline/v2_report/main_results_table.tex
data/results/v2_1_sim_matrix/small_gap_borderline/v2_report/parser_sensitivity_table.csv
data/results/v2_1_sim_matrix/small_gap_borderline/v2_report/report.md
data/results/v2_1_sim_matrix/small_gap_borderline/v2_report/v2_report_summary.json
data/results/v2_1_sim_matrix/spurious_control_flipper/scenario_config.json
data/results/v2_1_sim_matrix/spurious_control_flipper/simulated_pair_scores.jsonl
data/results/v2_1_sim_matrix/spurious_control_flipper/simulated_predictions.jsonl
data/results/v2_1_sim_matrix/spurious_control_flipper/simulated_run_metadata.json
data/results/v2_1_sim_matrix/spurious_control_flipper/simulated_tasks.jsonl
data/results/v2_1_sim_matrix/spurious_control_flipper/v2_report/by_domain_table.csv
data/results/v2_1_sim_matrix/spurious_control_flipper/v2_report/by_edit_type_table.csv
data/results/v2_1_sim_matrix/spurious_control_flipper/v2_report/by_family_table.csv
data/results/v2_1_sim_matrix/spurious_control_flipper/v2_report/by_family_table.tex
data/results/v2_1_sim_matrix/spurious_control_flipper/v2_report/certification_table.csv
data/results/v2_1_sim_matrix/spurious_control_flipper/v2_report/claim_ledger.json
data/results/v2_1_sim_matrix/spurious_control_flipper/v2_report/control_edit_table.csv
data/results/v2_1_sim_matrix/spurious_control_flipper/v2_report/figure_manifest.json
data/results/v2_1_sim_matrix/spurious_control_flipper/v2_report/main_results_table.csv
data/results/v2_1_sim_matrix/spurious_control_flipper/v2_report/main_results_table.tex
data/results/v2_1_sim_matrix/spurious_control_flipper/v2_report/parser_sensitivity_table.csv
data/results/v2_1_sim_matrix/spurious_control_flipper/v2_report/report.md
data/results/v2_1_sim_matrix/spurious_control_flipper/v2_report/v2_report_summary.json
data/results/v2_baseline_audit.json
data/results/v2_full_audit.json
data/results/v3_final_pre_real_run_audit.json
data/results/v4_command_smoke/.DS_Store
data/results/v4_command_smoke/full_2000/command_manifest.json
data/results/v4_command_smoke/full_2000/commands.md
data/results/v4_command_smoke/full_2000/commands.sh
data/results/v4_command_smoke/full_2000/expected_inputs.md
data/results/v4_command_smoke/full_2000/expected_outputs.md
data/results/v4_command_smoke/full_2000/resume_notes.md
data/results/v4_command_smoke/main_200/command_manifest.json
data/results/v4_command_smoke/main_200/commands.md
data/results/v4_command_smoke/main_200/commands.sh
data/results/v4_command_smoke/main_200/expected_inputs.md
data/results/v4_command_smoke/main_200/expected_outputs.md
data/results/v4_command_smoke/main_200/resume_notes.md
data/results/v4_command_smoke/tiny_pilot/command_manifest.json
data/results/v4_command_smoke/tiny_pilot/commands.md
data/results/v4_command_smoke/tiny_pilot/commands.sh
data/results/v4_command_smoke/tiny_pilot/expected_inputs.md
data/results/v4_command_smoke/tiny_pilot/expected_outputs.md
data/results/v4_command_smoke/tiny_pilot/resume_notes.md
data/results/v4_final_all_system_audit.json
data/results/v4_smoke/broken_predictions.jsonl
data/results/v4_smoke/cc0_sources.jsonl
data/results/v4_smoke/edit_plan.jsonl
data/results/v4_smoke/repaired_predictions.jsonl.repair_plan.json
data/results/v4_smoke/run.log
data/results/v4_smoke/visual_review_sheet.csv
data/results/v5_all_commands_smoke.json
data/results/v5_cvpr_ready_except_results_audit.json
data/results/v5_destructive_audit.json
data/results/v5_smoke/ablation_report.json
data/results/v5_smoke/answerability_ratings.csv
data/results/v5_smoke/gold_labels.csv
data/results/v5_smoke/model_card.md
data/results/v5_smoke/rater_training/calibration_quiz_template.csv
data/results/v5_smoke/rater_training/gold_label_rubric_template.csv
data/results/v5_smoke/rater_training/rater_guide.md
data/results/v5_smoke/visual_review_summary.json
data/results/v5_test_smoke.json
data/results/v6_final_directional_audit.json
data/results/v6_reviewer_attacks.json
data/results/v6_stop_condition_audit.json
data/results/v7_post3model_final_audit.json
```

### v10_privacy_files

```bash
find . -maxdepth 5 -type f \( -name "*v10*" -o -name "AUTORUN_*" -o -name "*privacy*" \) | sort
```

Return code: `0`

```text
./AUTORUN_BLOCKERS.md
./AUTORUN_BLOCKERS_V2.md
./AUTORUN_LEDGER.jsonl
./AUTORUN_LEDGER_V2.jsonl
./AUTORUN_STATUS.md
./AUTORUN_STATUS_V2.md
./certvic/security/__pycache__/release_privacy_audit.cpython-311.pyc
./certvic/security/release_privacy_audit.py
./data/dashboard/v10_execution_dashboard.html
./data/dashboard/v10_status_cards.json
./data/results/main_real_200/v10_1_correction/claim_guard_v10_1.json
./data/results/main_real_200/v10_1_correction/privacy_audit_after_fix.json
./data/results/main_real_200/v10_1_correction/privacy_audit_after_fix.md
./data/results/main_real_200/v10_1_correction/privacy_audit_after_script_fix.json
./data/results/main_real_200/v10_1_correction/privacy_audit_after_script_fix.md
./data/results/main_real_200/v10_1_correction/privacy_audit_before_fix.json
./data/results/main_real_200/v10_1_correction/privacy_audit_before_fix.md
./data/results/main_real_200/v10_1_correction/privacy_audit_v10_1.json
./data/results/main_real_200/v10_1_correction/privacy_audit_v10_1.md
./data/results/main_real_200/v10_1_correction/privacy_fix_manifest.json
./data/results/main_real_200/v10_1_correction/pytest_v10_1_full.log
./data/results/main_real_200/v10_1_correction/pytest_v10_1_selected.log
./data/results/main_real_200/v10_1_correction/v10_1_final_handoff.json
./data/results/main_real_200/v10_1_correction/v10_1_input_discovery.json
./data/results/main_real_200/v10_1_correction/v10_partials_resolution_table.json
./data/results/main_real_200/v8_1_qwen_spurious_forensics/privacy_audit_v8_1.json
./data/results/main_real_200/v8_1_qwen_spurious_forensics/privacy_audit_v8_1.md
./data/results/main_real_200/v8_upgrade/privacy_audit_final.json
./data/results/main_real_200/v8_upgrade/privacy_audit_final.md
./data/results/main_real_200/v9_mega_upgrade/privacy_audit_v9_final.json
./data/results/main_real_200/v9_mega_upgrade/privacy_audit_v9_final.md
./data/results/main_real_200/v9_mega_upgrade/privacy_v9_label_hygiene.json
./data/results/main_real_200/v9_mega_upgrade/privacy_v9_label_hygiene.md
./data/results/privacy_audit_after_remaining_runbooks.json
./data/results/v10_claim_language_guard.json
./data/results/v10_privacy_audit.json
./dist/certvic_v10_execution_ready_handoff.zip
./notebooks/kaggle/v10_execution_ready_handoff_t4x2.ipynb
./scripts/build_v10_1_correction.py
./tests/__pycache__/test_v3_security_privacy_audit.cpython-311-pytest-9.0.2.pyc
./tests/test_v3_security_privacy_audit.py
```

### kaggle_notebooks

```bash
find notebooks/kaggle -maxdepth 1 -type f | sort
```

Return code: `0`

```text
notebooks/kaggle/00_precache_weights.ipynb
notebooks/kaggle/01_make_masks.md
notebooks/kaggle/02_generate_edits.md
notebooks/kaggle/03_quality_filter.md
notebooks/kaggle/04_run_open_vlms.md
notebooks/kaggle/05_run_free_tier_reference.md
notebooks/kaggle/06_build_reports.md
notebooks/kaggle/07_mechanism_probes.md
notebooks/kaggle/README.md
notebooks/kaggle/certvic_internvl_T4_eval.ipynb
notebooks/kaggle/certvic_internvl_T4_eval_SELF_DOWNLOAD.ipynb
notebooks/kaggle/certvic_llava_ov_T4_eval_SELF_DOWNLOAD.ipynb
notebooks/kaggle/certvic_main200_diffusion_T4x2.ipynb
notebooks/kaggle/certvic_main200_vlm_T4x2_AFTER_GATES.ipynb
notebooks/kaggle/diffusion_main_scale_T4x2_TEMPLATE.ipynb
notebooks/kaggle/main500_diffusion_T4x2.ipynb
notebooks/kaggle/main500_internvl_8b_T4x2.ipynb
notebooks/kaggle/main500_llava_onevision_7b_T4x2.ipynb
notebooks/kaggle/main500_qwen2_5_vl_7b_T4x2.ipynb
notebooks/kaggle/second_domain_mini_diffusion_T4x2.ipynb
notebooks/kaggle/second_domain_mini_vlm_T4x2.ipynb
notebooks/kaggle/v10_execution_ready_handoff_t4x2.ipynb
notebooks/kaggle/vlm_internvl_8b_T4x2_parallel.ipynb
notebooks/kaggle/vlm_internvl_8b_spurious_v2_T4x2.ipynb
notebooks/kaggle/vlm_llava_onevision_7b_T4x2_parallel.ipynb
notebooks/kaggle/vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb
notebooks/kaggle/vlm_qwen2_5_vl_7b_T4x2_parallel.ipynb
notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb
```

### dist_tail

```bash
find dist -maxdepth 3 -type f | sort | tail -100
```

Return code: `0`

```text
dist/.DS_Store
dist/certvic_absent_object_control.zip
dist/certvic_kaggle_main200_bundle.zip
dist/certvic_kaggle_main200_bundle_manifest.json
dist/certvic_main200_session2_data.zip
dist/certvic_perception_control_scaled.zip
dist/certvic_remaining_kaggle_runbooks.zip
dist/certvic_spurious_flip_control.zip
dist/certvic_v10_execution_ready_handoff.zip
dist/certvic_v9_artifact_manifest.json
dist/certvic_v9_release_candidate.zip
dist/kaggle_remaining_runs/INPUTS_MATRIX.md
dist/kaggle_remaining_runs/LOCAL_INGEST_COMMANDS.md
dist/kaggle_remaining_runs/OUTPUTS_MATRIX.md
dist/kaggle_remaining_runs/README_RUN_ORDER.md
dist/kaggle_remaining_runs/RUN_TIME_ESTIMATES.md
dist/kaggle_remaining_runs/SPURIOUS_V2_INPUTS_MATRIX.md
dist/kaggle_remaining_runs/SPURIOUS_V2_LOCAL_INGEST_COMMANDS.md
dist/kaggle_remaining_runs/certvic_mechanism_probes.zip
dist/kaggle_remaining_runs/certvic_perception_control_scaled.zip
dist/kaggle_remaining_runs/certvic_polarity_ablations.zip
dist/kaggle_remaining_runs/certvic_spurious_flip_control.zip
dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip
dist/kaggle_remaining_runs/manifest.json
dist/kaggle_remaining_runs/notebooks/diffusion_main_scale_T4x2_TEMPLATE.ipynb
dist/kaggle_remaining_runs/notebooks/vlm_internvl_8b_T4x2_parallel.ipynb
dist/kaggle_remaining_runs/notebooks/vlm_llava_onevision_7b_T4x2_parallel.ipynb
dist/kaggle_remaining_runs/notebooks/vlm_qwen2_5_vl_7b_T4x2_parallel.ipynb
dist/main500_diffusion_kaggle_inputs.BLOCKED.txt
dist/main500_vlm_eval_bundle.BLOCKED.txt
```

