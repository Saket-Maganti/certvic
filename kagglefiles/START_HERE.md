OPEN ONLY THIS FOLDER FOR KAGGLE EXECUTION.
DO NOT NAVIGATE THE REST OF THE REPOSITORY.

# CertVIC Kaggle operator pack

- Repository source commit: `51e957aaabc21205e00db648cf52d021a3691eb2`
- Origin/main at generation: `51e957aaabc21205e00db648cf52d021a3691eb2`
- Doctor state: `READY_FOR_00A`
- Active runtime profile: `kaggle_cp312_2026_07`
- Evidence boundary: `paper_evidence=false`; genuine `human_reviewed=true` count is 0.
- Main: `execution_allowed=false`.
- Second domain: `execution_allowed=false`.

## C4 live-provisioning retry

Delete the four failed Kaggle draft sessions. Pull the latest `main`, then use only the four refreshed notebooks in `runbooks/00_PROVISIONING/` with the refreshed files from `inputs/00_COMMON/`. Use **Accelerator OFF**, **Internet ON**, and click **Run All**. Do not reuse a failed session's working directory.

## Exact first executable action

`BUILD_CP312_WHEELHOUSE`

Open `runbooks/00_PROVISIONING/00_build_certvic_cp312_wheelhouse.ipynb`, attach the three ZIPs from `inputs/00_COMMON/`, set **Accelerator OFF** and **Internet ON**, then click **Run All**. Download `certvic_offline_wheelhouse_cp312.zip` and import it unchanged with:

```bash
python3 kagglefiles/import_kaggle_return.py /path/to/downloaded_return.zip
```

The locally present CPython 3.10 wheelhouse is legacy and is not an active input.

## Chronological run table

| Order | Stage | Runbook | Matching input | Attach | Accelerator | Internet | Estimate | Expected output | Local destination | Resume | Readiness |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `BUILD_CP312_WHEELHOUSE` | `00_build_certvic_cp312_wheelhouse.ipynb` | `inputs/01_CP312_WHEELHOUSE` | `CODE;CONFIGS;EXECUTION_TOOLS` | OFF | ON | PLANNING_ESTIMATE: 45-120 min typical; up to 3 h | `certvic_offline_wheelhouse_cp312.zip` | `kagglefiles/inputs/01_CP312_WHEELHOUSE/certvic_offline_wheelhouse_cp312.zip` | `bash kagglefiles/run_local_resume.sh` | `READY_NOW` |
| 2 | `BUILD_MODEL_SNAPSHOT` | `01_build_qwen2_5_vl_7b_snapshot.ipynb` | `inputs/02_QWEN_SNAPSHOT` | `CODE` | OFF | ON | PLANNING_ESTIMATE: 2-6 h/provider | `qwen2_5_vl_7b_snapshot.zip` | `kagglefiles/inputs/02_QWEN_SNAPSHOT/qwen2_5_vl_7b_snapshot.zip` | `bash kagglefiles/run_local_resume.sh` | `READY_NOW` |
| 3 | `BUILD_MODEL_SNAPSHOT` | `02_build_internvl_8b_snapshot.ipynb` | `inputs/03_INTERNVL_SNAPSHOT` | `CODE` | OFF | ON | PLANNING_ESTIMATE: 2-6 h/provider | `internvl2_8b_snapshot.zip` | `kagglefiles/inputs/03_INTERNVL_SNAPSHOT/internvl2_8b_snapshot.zip` | `bash kagglefiles/run_local_resume.sh` | `READY_NOW` |
| 4 | `BUILD_MODEL_SNAPSHOT` | `03_build_llava_onevision_7b_snapshot.ipynb` | `inputs/04_LLAVA_SNAPSHOT` | `CODE` | OFF | ON | PLANNING_ESTIMATE: 2-6 h/provider | `llava_onevision_7b_snapshot.zip` | `kagglefiles/inputs/04_LLAVA_SNAPSHOT/llava_onevision_7b_snapshot.zip` | `bash kagglefiles/run_local_resume.sh` | `READY_NOW` |
| 5 | `CODE_SMOKE` | `00A_certvic_code_and_environment_smoke.ipynb` | `inputs/01_CP312_WHEELHOUSE` | `CODE;CONFIGS;EXECUTION_TOOLS;CP312_WHEELHOUSE` | OFF | OFF | PLANNING_ESTIMATE: 15-35 min | `00A_environment_bundle.zip` | `data/runtime/00A_environment_bundle.zip` | `bash kagglefiles/run_local_resume.sh` | `WAITING_FOR_EXTERNAL_BYTES` |
| 6 | `SNAPSHOT_SMOKE` | `00B_qwen2_5_vl_7b_snapshot_smoke.ipynb` | `inputs/02_QWEN_SNAPSHOT` | `CODE;CONFIGS;EXECUTION_TOOLS;CP312_WHEELHOUSE;MODEL_SNAPSHOT` | OFF | OFF | PLANNING_ESTIMATE: 15-30 min/provider | `00B_qwen2_5_vl_7b_snapshot_bundle.zip` | `data/runtime/00B_qwen2_5_vl_7b_snapshot_bundle.zip` | `bash kagglefiles/run_local_resume.sh` | `WAITING_FOR_PRIOR_RETURN` |
| 7 | `SNAPSHOT_SMOKE` | `00B_internvl_8b_snapshot_smoke.ipynb` | `inputs/03_INTERNVL_SNAPSHOT` | `CODE;CONFIGS;EXECUTION_TOOLS;CP312_WHEELHOUSE;MODEL_SNAPSHOT` | OFF | OFF | PLANNING_ESTIMATE: 15-30 min/provider | `00B_internvl_8b_snapshot_bundle.zip` | `data/runtime/00B_internvl_8b_snapshot_bundle.zip` | `bash kagglefiles/run_local_resume.sh` | `WAITING_FOR_PRIOR_RETURN` |
| 8 | `SNAPSHOT_SMOKE` | `00B_llava_onevision_7b_snapshot_smoke.ipynb` | `inputs/04_LLAVA_SNAPSHOT` | `CODE;CONFIGS;EXECUTION_TOOLS;CP312_WHEELHOUSE;MODEL_SNAPSHOT` | OFF | OFF | PLANNING_ESTIMATE: 15-30 min/provider | `00B_llava_onevision_7b_snapshot_bundle.zip` | `data/runtime/00B_llava_onevision_7b_snapshot_bundle.zip` | `bash kagglefiles/run_local_resume.sh` | `WAITING_FOR_PRIOR_RETURN` |
| 9 | `REAL_MODEL_SMOKE` | `00C2_qwen2_5_vl_7b_real_model_two_item_smoke.ipynb` | `inputs/06_PRE_SMOKE_PERMISSIONS` | `CODE;CONFIGS;EXECUTION_TOOLS;CP312_WHEELHOUSE;MODEL_SNAPSHOT;REAL_TWO_ITEM_SMOKE;PRE_SMOKE_PROVIDER_PERMISSION` | T4x2 | OFF | PLANNING_ESTIMATE: 15-45 min/provider | `00C2_qwen2_5_vl_7b_real_model_smoke.zip` | `data/runtime/00C2_qwen2_5_vl_7b_real_model_smoke.zip` | `bash kagglefiles/run_local_resume.sh` | `WAITING_FOR_EXTERNAL_BYTES` |
| 10 | `REAL_MODEL_SMOKE` | `00C2_internvl_8b_real_model_two_item_smoke.ipynb` | `inputs/06_PRE_SMOKE_PERMISSIONS` | `CODE;CONFIGS;EXECUTION_TOOLS;CP312_WHEELHOUSE;MODEL_SNAPSHOT;REAL_TWO_ITEM_SMOKE;PRE_SMOKE_PROVIDER_PERMISSION` | T4x2 | OFF | PLANNING_ESTIMATE: 15-45 min/provider | `00C2_internvl_8b_real_model_smoke.zip` | `data/runtime/00C2_internvl_8b_real_model_smoke.zip` | `bash kagglefiles/run_local_resume.sh` | `WAITING_FOR_EXTERNAL_BYTES` |
| 11 | `REAL_MODEL_SMOKE` | `00C2_llava_onevision_7b_real_model_two_item_smoke.ipynb` | `inputs/06_PRE_SMOKE_PERMISSIONS` | `CODE;CONFIGS;EXECUTION_TOOLS;CP312_WHEELHOUSE;MODEL_SNAPSHOT;REAL_TWO_ITEM_SMOKE;PRE_SMOKE_PROVIDER_PERMISSION` | T4x2 | OFF | PLANNING_ESTIMATE: 15-45 min/provider | `00C2_llava_onevision_7b_real_model_smoke.zip` | `data/runtime/00C2_llava_onevision_7b_real_model_smoke.zip` | `bash kagglefiles/run_local_resume.sh` | `WAITING_FOR_EXTERNAL_BYTES` |
| 12 | `GENERATION` | `01_specificity_confirmatory_generation_T4x2.ipynb` | `inputs/07_CONFIRMATORY_GENERATION` | `COMMON;CP312_WHEELHOUSE;CONFIRMATORY_GENERATION_INPUT` | T4x2 | OFF | PLANNING_ESTIMATE: 2-8 h | `confirmatory_generation_return.zip` | `local_inputs/provider_returns/specificity_confirmatory_cvpr/confirmatory_generation_return.zip` | `bash kagglefiles/run_local_resume.sh` | `WAITING_FOR_EXTERNAL_BYTES` |
| 13 | `EVALUATION` | `02_qwen_specificity_confirmatory_T4x2.ipynb` | `inputs/08_CONFIRMATORY_QWEN` | `COMMON;CP312_WHEELHOUSE;MODEL_SNAPSHOT;CONFIRMATORY_PROVIDER_INPUT;PERMISSION` | T4x2 | OFF | PLANNING_ESTIMATE: 2-5 h | `confirmatory_qwen_return.zip` | `local_inputs/provider_returns/specificity_confirmatory_cvpr/confirmatory_qwen_return.zip` | `bash kagglefiles/run_local_resume.sh` | `WAITING_FOR_HUMAN_REVIEW` |
| 14 | `EVALUATION` | `03_internvl_specificity_confirmatory_T4x2.ipynb` | `inputs/09_CONFIRMATORY_INTERNVL` | `COMMON;CP312_WHEELHOUSE;MODEL_SNAPSHOT;CONFIRMATORY_PROVIDER_INPUT;PERMISSION` | T4x2 | OFF | PLANNING_ESTIMATE: 3-7 h | `confirmatory_internvl_return.zip` | `local_inputs/provider_returns/specificity_confirmatory_cvpr/confirmatory_internvl_return.zip` | `bash kagglefiles/run_local_resume.sh` | `WAITING_FOR_HUMAN_REVIEW` |
| 15 | `EVALUATION` | `04_llava_specificity_confirmatory_T4x2.ipynb` | `inputs/10_CONFIRMATORY_LLAVA` | `COMMON;CP312_WHEELHOUSE;MODEL_SNAPSHOT;CONFIRMATORY_PROVIDER_INPUT;PERMISSION` | T4x2 | OFF | PLANNING_ESTIMATE: 2-5 h | `confirmatory_llava_return.zip` | `local_inputs/provider_returns/specificity_confirmatory_cvpr/confirmatory_llava_return.zip` | `bash kagglefiles/run_local_resume.sh` | `WAITING_FOR_HUMAN_REVIEW` |
| 16 | `GENERATION` | `10_main_study_generation_T4x2.ipynb` | `inputs/11_MAIN_GENERATION` | `COMMON;CP312_WHEELHOUSE;MAIN_GO;MAIN_INPUT` | T4x2 | OFF | PLANNING_ESTIMATE: 4-10 h; 8-18 h reserve | `main_generation_return.zip` | `local_inputs/provider_returns/main_study_cvpr/main_generation_return.zip` | `bash kagglefiles/run_local_resume.sh` | `CONDITIONAL_NOT_AUTHORIZED` |
| 17 | `EVALUATION` | `11_qwen_main_study_T4x2.ipynb` | `inputs/12_MAIN_QWEN` | `COMMON;CP312_WHEELHOUSE;MAIN_GO;MAIN_INPUT` | T4x2 | OFF | PLANNING_ESTIMATE: 5-10 h | `main_qwen_return.zip` | `local_inputs/provider_returns/main_study_cvpr/main_qwen_return.zip` | `bash kagglefiles/run_local_resume.sh` | `CONDITIONAL_NOT_AUTHORIZED` |
| 18 | `EVALUATION` | `12_internvl_main_study_T4x2.ipynb` | `inputs/13_MAIN_INTERNVL` | `COMMON;CP312_WHEELHOUSE;MAIN_GO;MAIN_INPUT` | T4x2 | OFF | PLANNING_ESTIMATE: 8-16 h | `main_internvl_return.zip` | `local_inputs/provider_returns/main_study_cvpr/main_internvl_return.zip` | `bash kagglefiles/run_local_resume.sh` | `CONDITIONAL_NOT_AUTHORIZED` |
| 19 | `EVALUATION` | `13_llava_main_study_T4x2.ipynb` | `inputs/14_MAIN_LLAVA` | `COMMON;CP312_WHEELHOUSE;MAIN_GO;MAIN_INPUT` | T4x2 | OFF | PLANNING_ESTIMATE: 5-10 h | `main_llava_return.zip` | `local_inputs/provider_returns/main_study_cvpr/main_llava_return.zip` | `bash kagglefiles/run_local_resume.sh` | `CONDITIONAL_NOT_AUTHORIZED` |
| 20 | `GENERATION` | `20_second_domain_generation_T4x2.ipynb` | `inputs/15_SECOND_DOMAIN_GENERATION` | `COMMON;CP312_WHEELHOUSE;SECOND_DOMAIN_AUTHORIZATION;SECOND_DOMAIN_INPUT` | T4x2 | OFF | PLANNING_ESTIMATE: 2-5 h | `coco_generation_return.zip` | `local_inputs/provider_returns/second_domain_cvpr/coco_generation_return.zip` | `bash kagglefiles/run_local_resume.sh` | `CONDITIONAL_NOT_AUTHORIZED` |
| 21 | `EVALUATION` | `21_second_domain_qwen_T4x2.ipynb` | `inputs/16_SECOND_DOMAIN_QWEN` | `COMMON;CP312_WHEELHOUSE;SECOND_DOMAIN_AUTHORIZATION;SECOND_DOMAIN_INPUT` | T4x2 | OFF | PLANNING_ESTIMATE: 1-2 h | `coco_qwen_return.zip` | `local_inputs/provider_returns/second_domain_cvpr/coco_qwen_return.zip` | `bash kagglefiles/run_local_resume.sh` | `CONDITIONAL_NOT_AUTHORIZED` |
| 22 | `EVALUATION` | `22_second_domain_internvl_T4x2.ipynb` | `inputs/17_SECOND_DOMAIN_INTERNVL` | `COMMON;CP312_WHEELHOUSE;SECOND_DOMAIN_AUTHORIZATION;SECOND_DOMAIN_INPUT` | T4x2 | OFF | PLANNING_ESTIMATE: 1.5-3 h | `coco_internvl_return.zip` | `local_inputs/provider_returns/second_domain_cvpr/coco_internvl_return.zip` | `bash kagglefiles/run_local_resume.sh` | `CONDITIONAL_NOT_AUTHORIZED` |
| 23 | `EVALUATION` | `23_second_domain_llava_T4x2.ipynb` | `inputs/18_SECOND_DOMAIN_LLAVA` | `COMMON;CP312_WHEELHOUSE;SECOND_DOMAIN_AUTHORIZATION;SECOND_DOMAIN_INPUT` | T4x2 | OFF | PLANNING_ESTIMATE: 1-2 h | `coco_llava_return.zip` | `local_inputs/provider_returns/second_domain_cvpr/coco_llava_return.zip` | `bash kagglefiles/run_local_resume.sh` | `CONDITIONAL_NOT_AUTHORIZED` |

## Parallel execution

Only rows sharing the same nonempty `can_run_in_parallel_with` value in `RUN_ORDER.csv` are explicit parallel groups. Provider permissions remain distinct and single-use.

## After every download

```bash
python3 kagglefiles/import_kaggle_return.py /path/to/downloaded_return.zip
bash kagglefiles/run_local_resume.sh
```

Never rename archive contents, edit a runbook configuration cell, bypass a permission gate, or treat a planning estimate as an observed runtime.
