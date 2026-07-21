# CertVIC Kaggle Dataset Map

Do not rename ZIPs, edit manifests, or guess mounts. Publish each ZIP as the private dataset slug stored in its `bundle_manifest.json`; the shared bootstrap discovers and verifies exactly one match.

## Repository-byte datasets

| ZIP | Private dataset slug | Mount |
| --- | --- | --- |
| `certvic_code_bundle.zip` | `certvic/certvic-code` | `/kaggle/input/certvic-code` |
| `certvic_notebooks_bundle.zip` | `certvic/certvic-runbooks` | `/kaggle/input/certvic-runbooks` |
| `certvic_configs_bundle.zip` | `certvic/certvic-configs` | `/kaggle/input/certvic-configs` |
| `certvic_execution_tools_bundle.zip` | `certvic/certvic-execution-tools` | `/kaggle/input/certvic-execution-tools` |
| `certvic_synthetic_validation_bundle.zip` | `certvic/certvic-synthetic-validation` | `/kaggle/input/certvic-synthetic-validation` |
| `certvic_offline_wheelhouse.zip` | `certvic/certvic-offline-wheelhouse` | `/kaggle/input/certvic-offline-wheelhouse` |
| `qwen2_5_vl_7b_snapshot.zip` | `certvic/qwen2-5-vl-7b-snapshot` | `/kaggle/input/qwen2-5-vl-7b-snapshot` |
| `internvl2_8b_snapshot.zip` | `certvic/internvl2-8b-snapshot` | `/kaggle/input/internvl2-8b-snapshot` |
| `llava_onevision_7b_snapshot.zip` | `certvic/llava-onevision-7b-snapshot` | `/kaggle/input/llava-onevision-7b-snapshot` |
| `certvic_real_two_item_smoke_bundle.zip` | `certvic/certvic-real-two-item-smoke` | `/kaggle/input/certvic-real-two-item-smoke` |
| `certvic_pre_smoke_permissions.zip` | `certvic/certvic-pre-smoke-permissions` | `/kaggle/input/certvic-pre-smoke-permissions` |

## Execution order

The seven 00A/00B/00C2 notebooks require no manual configuration edits.

1. Attach code, configs, tools, and the Linux wheelhouse; run 00A.
2. Attach one immutable snapshot at a time; run 00B for all three providers.
3. Build permissions only from returned 00A/00B bytes and the real two-item smoke bundle.
4. Run 00C2 for Qwen, InternVL, and LLaVA; import all returns through the transactional handoff.
5. Create scientific input datasets only after their upstream review/authorization gates pass.
