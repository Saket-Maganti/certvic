# CertVIC zero-edit Kaggle smoke handoff

These are non-evidence integrity and smoke runs. Do not edit a notebook cell, rename an attached
archive, enable Internet, or reuse a session with different bytes. The notebooks discover exact
private dataset slugs, authenticate every archive and inner file, safely extract canonical ZIPs,
derive all runtime identities from manifests, and fail closed on missing or ambiguous inputs.

The exact local continuation after every unchanged download is:

```bash
python3 scripts/run_all_cpu_workflows.py --resume
```

## 00A environment smoke

| Field | Exact value |
| --- | --- |
| Notebook | `00A_certvic_code_and_environment_smoke.ipynb` |
| Accelerator | Off; zero GPUs required and enforced |
| Internet | Off |
| Private datasets | `certvic/certvic-code`; `certvic/certvic-configs`; `certvic/certvic-execution-tools`; `certvic/certvic-offline-wheelhouse` |
| Attached filenames | `certvic_code_bundle.zip`; `certvic_configs_bundle.zip`; `certvic_execution_tools_bundle.zip`; `certvic_offline_wheelhouse.zip` |
| Expected mounts | `/kaggle/input/certvic-code`; `/kaggle/input/certvic-configs`; `/kaggle/input/certvic-execution-tools`; `/kaggle/input/certvic-offline-wheelhouse` |
| Return ZIP | `/kaggle/working/00A_environment_bundle.zip` |
| Local destination | `data/runtime/00A_environment_bundle.zip` |
| Estimated runtime | 10–20 minutes |
| Stable failures | `KAGGLE_BOOTSTRAP_01_DATASET_NOT_FOUND`; `KAGGLE_BOOTSTRAP_02_AMBIGUOUS_DATASET`; `KAGGLE_BOOTSTRAP_03_BUNDLE_INVALID`; `KAGGLE_BOOTSTRAP_04_WHEELHOUSE_INVALID`; `KAGGLE_BOOTSTRAP_09_UNSAFE_EXTRACTION`; `KAGGLE_BOOTSTRAP_10_AMBIGUOUS_CONTENT`; `KAGGLE_ZERO_EDIT_CPU_ACCELERATOR_MUST_BE_OFF`; `KAGGLE_ZERO_EDIT_EXACT_ENVIRONMENT_NOT_ESTABLISHED` |
| Operator edits | None; attach datasets and click Run All |

## 00B Qwen snapshot smoke

| Field | Exact value |
| --- | --- |
| Notebook | `00B_qwen2_5_vl_7b_snapshot_smoke.ipynb` |
| Accelerator | Off; zero GPUs required and enforced |
| Internet | Off |
| Private datasets | The four 00A datasets plus `certvic/qwen2-5-vl-7b-snapshot` |
| Attached filenames | The four 00A filenames plus `qwen2_5_vl_7b_snapshot.zip` |
| Expected mounts | The four 00A mounts plus `/kaggle/input/qwen2-5-vl-7b-snapshot` |
| Return ZIP | `/kaggle/working/00B_qwen2_5_vl_7b_snapshot_bundle.zip` |
| Local destination | `data/runtime/00B_qwen2_5_vl_7b_snapshot_bundle.zip` |
| Estimated runtime | 15–30 minutes |
| Stable failures | 00A bootstrap codes plus `KAGGLE_BOOTSTRAP_08_RUN_IDENTITY_INCOMPLETE`; `KAGGLE_ZERO_EDIT_SNAPSHOT_INVALID` |
| Operator edits | None; attach datasets and click Run All |

## 00B InternVL snapshot smoke

| Field | Exact value |
| --- | --- |
| Notebook | `00B_internvl_8b_snapshot_smoke.ipynb` |
| Accelerator | Off; zero GPUs required and enforced |
| Internet | Off |
| Private datasets | The four 00A datasets plus `certvic/internvl2-8b-snapshot` |
| Attached filenames | The four 00A filenames plus `internvl2_8b_snapshot.zip` |
| Expected mounts | The four 00A mounts plus `/kaggle/input/internvl2-8b-snapshot` |
| Return ZIP | `/kaggle/working/00B_internvl_8b_snapshot_bundle.zip` |
| Local destination | `data/runtime/00B_internvl_8b_snapshot_bundle.zip` |
| Estimated runtime | 15–30 minutes |
| Stable failures | 00A bootstrap codes plus `KAGGLE_BOOTSTRAP_08_RUN_IDENTITY_INCOMPLETE`; `KAGGLE_ZERO_EDIT_SNAPSHOT_INVALID` |
| Operator edits | None; attach datasets and click Run All |

## 00B LLaVA snapshot smoke

| Field | Exact value |
| --- | --- |
| Notebook | `00B_llava_onevision_7b_snapshot_smoke.ipynb` |
| Accelerator | Off; zero GPUs required and enforced |
| Internet | Off |
| Private datasets | The four 00A datasets plus `certvic/llava-onevision-7b-snapshot` |
| Attached filenames | The four 00A filenames plus `llava_onevision_7b_snapshot.zip` |
| Expected mounts | The four 00A mounts plus `/kaggle/input/llava-onevision-7b-snapshot` |
| Return ZIP | `/kaggle/working/00B_llava_onevision_7b_snapshot_bundle.zip` |
| Local destination | `data/runtime/00B_llava_onevision_7b_snapshot_bundle.zip` |
| Estimated runtime | 15–30 minutes |
| Stable failures | 00A bootstrap codes plus `KAGGLE_BOOTSTRAP_08_RUN_IDENTITY_INCOMPLETE`; `KAGGLE_ZERO_EDIT_SNAPSHOT_INVALID` |
| Operator edits | None; attach datasets and click Run All |

## 00C2 Qwen real-model two-item smoke

| Field | Exact value |
| --- | --- |
| Notebook | `00C2_qwen2_5_vl_7b_real_model_two_item_smoke.ipynb` |
| Accelerator | T4×2; one T4 is the allowed deterministic fallback |
| Internet | Off |
| Private datasets | The four 00A datasets; `certvic/qwen2-5-vl-7b-snapshot`; `certvic/certvic-real-two-item-smoke`; `certvic/certvic-pre-smoke-permissions` |
| Attached filenames | The four 00A filenames; `qwen2_5_vl_7b_snapshot.zip`; `certvic_real_two_item_smoke_bundle.zip`; `certvic_pre_smoke_permissions.zip` |
| Expected mounts | The four 00A mounts; `/kaggle/input/qwen2-5-vl-7b-snapshot`; `/kaggle/input/certvic-real-two-item-smoke`; `/kaggle/input/certvic-pre-smoke-permissions` |
| Return ZIP | `/kaggle/working/00C2_qwen2_5_vl_7b_real_model_smoke.zip` |
| Local destination | `data/runtime/00C2_qwen2_5_vl_7b_real_model_smoke.zip` |
| Estimated runtime | 20–60 minutes |
| Stable failures | 00A/00B codes plus `KAGGLE_ZERO_EDIT_00C2_TASK_CARDINALITY_INVALID`; `KAGGLE_ZERO_EDIT_00C2_PERMISSION_ARTIFACT_INVALID`; `KAGGLE_ZERO_EDIT_00C2_PERMISSION_BINDING_MISSING`; `KAGGLE_ZERO_EDIT_00C2_PERMISSION_IDENTITY_MISMATCH`; `KAGGLE_BOOTSTRAP_07_GPU_CONTRACT_FAILED` |
| Operator edits | None; attach datasets, select T4×2 or one T4, and click Run All |

## 00C2 InternVL real-model two-item smoke

| Field | Exact value |
| --- | --- |
| Notebook | `00C2_internvl_8b_real_model_two_item_smoke.ipynb` |
| Accelerator | T4×2; one T4 is the allowed deterministic fallback |
| Internet | Off |
| Private datasets | The four 00A datasets; `certvic/internvl2-8b-snapshot`; `certvic/certvic-real-two-item-smoke`; `certvic/certvic-pre-smoke-permissions` |
| Attached filenames | The four 00A filenames; `internvl2_8b_snapshot.zip`; `certvic_real_two_item_smoke_bundle.zip`; `certvic_pre_smoke_permissions.zip` |
| Expected mounts | The four 00A mounts; `/kaggle/input/internvl2-8b-snapshot`; `/kaggle/input/certvic-real-two-item-smoke`; `/kaggle/input/certvic-pre-smoke-permissions` |
| Return ZIP | `/kaggle/working/00C2_internvl_8b_real_model_smoke.zip` |
| Local destination | `data/runtime/00C2_internvl_8b_real_model_smoke.zip` |
| Estimated runtime | 20–60 minutes |
| Stable failures | The same stable 00C2 failures listed on the Qwen card |
| Operator edits | None; attach datasets, select T4×2 or one T4, and click Run All |

## 00C2 LLaVA real-model two-item smoke

| Field | Exact value |
| --- | --- |
| Notebook | `00C2_llava_onevision_7b_real_model_two_item_smoke.ipynb` |
| Accelerator | T4×2; one T4 is the allowed deterministic fallback |
| Internet | Off |
| Private datasets | The four 00A datasets; `certvic/llava-onevision-7b-snapshot`; `certvic/certvic-real-two-item-smoke`; `certvic/certvic-pre-smoke-permissions` |
| Attached filenames | The four 00A filenames; `llava_onevision_7b_snapshot.zip`; `certvic_real_two_item_smoke_bundle.zip`; `certvic_pre_smoke_permissions.zip` |
| Expected mounts | The four 00A mounts; `/kaggle/input/llava-onevision-7b-snapshot`; `/kaggle/input/certvic-real-two-item-smoke`; `/kaggle/input/certvic-pre-smoke-permissions` |
| Return ZIP | `/kaggle/working/00C2_llava_onevision_7b_real_model_smoke.zip` |
| Local destination | `data/runtime/00C2_llava_onevision_7b_real_model_smoke.zip` |
| Estimated runtime | 20–60 minutes |
| Stable failures | The same stable 00C2 failures listed on the Qwen card |
| Operator edits | None; attach datasets, select T4×2 or one T4, and click Run All |

00C2 is not authorized or executed by this handoff. It remains blocked until the real licensed
two-item bundle and current provider-specific pre-smoke permission artifacts exist. Main and COCO
remain unauthorized. `paper_evidence=false`; genuine `human_reviewed=true` count remains zero.
