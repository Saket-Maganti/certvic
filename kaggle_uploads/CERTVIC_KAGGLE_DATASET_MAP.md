# CertVIC Kaggle Dataset Map

Upload identical authenticated bundle bytes to any Kaggle account under any dataset title, archive name, extension, mount, or nesting. Canonical labels below are recommendations only. Never edit authenticated bundle contents or manifests.

## Repository-byte datasets

| Recommended ZIP label | Recommended dataset label | Discovery role |
| --- | --- | --- |
| `certvic_code_bundle.zip` | `certvic-code` | `CODE` |
| `certvic_notebooks_bundle.zip` | `certvic-runbooks` | `NOTEBOOKS` |
| `certvic_configs_bundle.zip` | `certvic-configs` | `CONFIGS` |
| `certvic_execution_tools_bundle.zip` | `certvic-execution-tools` | `EXECUTION_TOOLS` |
| `certvic_synthetic_validation_bundle.zip` | `certvic-synthetic-validation` | `SYNTHETIC_VALIDATION` |
| `certvic_offline_wheelhouse.zip` | `certvic-offline-wheelhouse` | `OFFLINE_LINUX_WHEELHOUSE` |
| `qwen2_5_vl_7b_snapshot.zip` | `qwen2-5-vl-7b-snapshot` | `MODEL_SNAPSHOT` |
| `internvl2_8b_snapshot.zip` | `internvl2-8b-snapshot` | `MODEL_SNAPSHOT` |
| `llava_onevision_7b_snapshot.zip` | `llava-onevision-7b-snapshot` | `MODEL_SNAPSHOT` |
| `certvic_real_two_item_smoke_bundle.zip` | `certvic-real-two-item-smoke` | `REAL_TWO_ITEM_SMOKE` |
| `certvic_pre_smoke_permissions.zip` | `certvic-pre-smoke-permissions` | `PRE_SMOKE_PERMISSIONS` |

## Execution order

All 20 active notebooks require no manual path, owner, slug, filename, hash, provider, or permission edits.

1. Attach CODE, CONFIGS, EXECUTION_TOOLS, and OFFLINE_LINUX_WHEELHOUSE under any names; run 00A.
2. Attach one immutable snapshot at a time; run 00B for all three providers.
3. Build permissions only from returned 00A/00B bytes and the real two-item smoke bundle.
4. Run 00C2 for Qwen, InternVL, and LLaVA; import all returns through the transactional handoff.
5. Create scientific input datasets only after their upstream review/authorization gates pass.
