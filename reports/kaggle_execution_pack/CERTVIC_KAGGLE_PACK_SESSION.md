# CertVIC Kaggle Pack Session

Phase A built the complete local packaging layer without launching any real Kaggle/GPU scientific run. The live checkout was authoritative and was not a Git working tree. Baseline validation before edits: **857 passed, 1 skipped**.

## Repository ZIPs

| Path | Bytes | SHA-256 | Status |
| --- | ---: | --- | --- |
| `kaggle_uploads/00_code/certvic_code_bundle.zip` | 1233221 | `ef7fe5bd0d971e0d6ef232b9c231864f690839c7e368bad4ff78415ec982e908` | CREATED_AND_VALIDATED |
| `kaggle_uploads/00_code/certvic_notebooks_bundle.zip` | 207365 | `d2304331a346cc29484b38062e459da8f3dd098c5a0961776a16fd1338ce82e9` | CREATED_AND_VALIDATED |
| `kaggle_uploads/00_code/certvic_configs_bundle.zip` | 46527 | `64df5cb66455f72f56ebad0cc2c6575af4c183a6dcecfdcd4002c2adfd8d34f6` | CREATED_AND_VALIDATED |
| `kaggle_uploads/00_code/certvic_execution_tools_bundle.zip` | 175976 | `2665d24427bd60472d153fa1f9701870ff2341eadfb920f43fb984aa41971ee3` | CREATED_AND_VALIDATED |
| `kaggle_uploads/00_code/certvic_synthetic_validation_bundle.zip` | 38104 | `9b4f0c67af7f552ef4eff0198d7d9f0c0e5be1d7b5b3351d12e99bb2f42bb92c` | CREATED_AND_VALIDATED |

## External-byte builders

| Output | Status | Exact builder | Expected size |
| --- | --- | --- | --- |
| `kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip` | PROVISIONED_CLEAN_LINUX_CP310_VALIDATED | `python3 -m certvic.cvpr.wheelhouse_builder --mode LOCAL_VERIFY_ONLY --requirements-root requirements --wheel-root local_inputs/wheelhouse/linux_cp310 --output kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip` |  |
| `kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse_cp312.zip` | CP312_WHEELHOUSE_BUILDER_READY | `python3 scripts/build_kaggle_wheelhouse.py --mode KAGGLE_PROVISIONING_BUILD --profile kaggle_cp312_2026_07 --deterministic-provision --wheel-root /kaggle/working/wheels` |  |
| `kaggle_uploads/02_snapshots/qwen2_5_vl_7b_snapshot.zip` | BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES | `python3 scripts/build_model_snapshot_bundle.py --provider qwen2_5_vl_7b --snapshot-root <SNAPSHOT_ROOT> --model-commit <40_HEX> --processor-commit <40_HEX>` | 15-18 GB |
| `kaggle_uploads/02_snapshots/internvl2_8b_snapshot.zip` | BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES | `python3 scripts/build_model_snapshot_bundle.py --provider internvl_8b --snapshot-root <SNAPSHOT_ROOT> --model-commit <40_HEX> --processor-commit <40_HEX>` | 16-20 GB |
| `kaggle_uploads/02_snapshots/llava_onevision_7b_snapshot.zip` | BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES | `python3 scripts/build_model_snapshot_bundle.py --provider llava_onevision_7b --snapshot-root <SNAPSHOT_ROOT> --model-commit <40_HEX> --processor-commit <40_HEX>` | 15-18 GB |
| `kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip` | BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES | `python3 -m certvic.cvpr.smoke_input_builder --task-manifest local_inputs/smoke/real_smoke_tasks.jsonl --output kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip` | 1-50 MB |
| `kaggle_uploads/04_permissions/certvic_pre_smoke_permissions.zip` | BLOCKED_BY_UPSTREAM_GATE | `python3 -m certvic.cvpr.pre_smoke_packager --config <INPUTS_JSON>` | under 1 MB |
| `kaggle_uploads/05_confirmatory/certvic_confirmatory_generation_input.zip` | BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES | `python3 -m certvic.cvpr.confirmatory_input_builder --config <INPUT_CONFIG_JSON>` | 1-20 GB |
| `kaggle_uploads/06_confirmatory_runs/certvic_confirmatory_qwen_input.zip` | BLOCKED_BY_UPSTREAM_GATE | `python3 -m certvic.cvpr.scientific_input_builder --study confirmatory --provider qwen --config <ROLE_CONFIG_JSON> --run-tag <RUN_TAG>` | 1 MB-25 GB depending on redistributable task-bundle bytes |
| `kaggle_uploads/06_confirmatory_runs/certvic_confirmatory_internvl_input.zip` | BLOCKED_BY_UPSTREAM_GATE | `python3 -m certvic.cvpr.scientific_input_builder --study confirmatory --provider internvl --config <ROLE_CONFIG_JSON> --run-tag <RUN_TAG>` | 1 MB-25 GB depending on redistributable task-bundle bytes |
| `kaggle_uploads/06_confirmatory_runs/certvic_confirmatory_llava_input.zip` | BLOCKED_BY_UPSTREAM_GATE | `python3 -m certvic.cvpr.scientific_input_builder --study confirmatory --provider llava --config <ROLE_CONFIG_JSON> --run-tag <RUN_TAG>` | 1 MB-25 GB depending on redistributable task-bundle bytes |
| `kaggle_uploads/08_main_runs/certvic_main_qwen_input.zip` | CONDITIONAL_ON_CONFIRMATORY | `python3 -m certvic.cvpr.scientific_input_builder --study main --provider qwen --config <ROLE_CONFIG_JSON> --run-tag <RUN_TAG>` | 1 MB-25 GB depending on redistributable task-bundle bytes |
| `kaggle_uploads/08_main_runs/certvic_main_internvl_input.zip` | CONDITIONAL_ON_CONFIRMATORY | `python3 -m certvic.cvpr.scientific_input_builder --study main --provider internvl --config <ROLE_CONFIG_JSON> --run-tag <RUN_TAG>` | 1 MB-25 GB depending on redistributable task-bundle bytes |
| `kaggle_uploads/08_main_runs/certvic_main_llava_input.zip` | CONDITIONAL_ON_CONFIRMATORY | `python3 -m certvic.cvpr.scientific_input_builder --study main --provider llava --config <ROLE_CONFIG_JSON> --run-tag <RUN_TAG>` | 1 MB-25 GB depending on redistributable task-bundle bytes |
| `kaggle_uploads/10_coco_runs/certvic_coco_qwen_input.zip` | BLOCKED_BY_UPSTREAM_GATE | `python3 -m certvic.cvpr.scientific_input_builder --study coco --provider qwen --config <ROLE_CONFIG_JSON> --run-tag <RUN_TAG>` | 1 MB-25 GB depending on redistributable task-bundle bytes |
| `kaggle_uploads/10_coco_runs/certvic_coco_internvl_input.zip` | BLOCKED_BY_UPSTREAM_GATE | `python3 -m certvic.cvpr.scientific_input_builder --study coco --provider internvl --config <ROLE_CONFIG_JSON> --run-tag <RUN_TAG>` | 1 MB-25 GB depending on redistributable task-bundle bytes |
| `kaggle_uploads/10_coco_runs/certvic_coco_llava_input.zip` | BLOCKED_BY_UPSTREAM_GATE | `python3 -m certvic.cvpr.scientific_input_builder --study coco --provider llava --config <ROLE_CONFIG_JSON> --run-tag <RUN_TAG>` | 1 MB-25 GB depending on redistributable task-bundle bytes |
| `kaggle_uploads/07_main/certvic_main_generation_input.zip` | CONDITIONAL_ON_CONFIRMATORY | `python3 -m certvic.cvpr.build_all_kaggle_inputs --with-external-roots <EXTERNAL_ROOTS_YAML>` | 1-60 GB depending on the frozen licensed source universe |
| `kaggle_uploads/09_coco/certvic_coco_generation_input.zip` | BLOCKED_BY_UPSTREAM_GATE | `python3 -m certvic.cvpr.build_all_kaggle_inputs --with-external-roots <EXTERNAL_ROOTS_YAML>` | 1-60 GB depending on the frozen licensed source universe |

Frozen V1/V2 evidence, prospective gates, `paper_evidence=false`, and genuine human-review count zero remain unchanged.
