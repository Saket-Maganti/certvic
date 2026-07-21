# CertVIC Kaggle Ready to Upload Handoff

Five repository-byte ZIPs are ready. Every unavailable wheel, model, licensed source, human-review, and upstream authorization byte has a deterministic builder and precise status; none was fabricated.

## Built now

| Path | Bytes | SHA-256 | Status |
| --- | ---: | --- | --- |
| `kaggle_uploads/00_code/certvic_code_bundle.zip` | 1184393 | `0873a95e99550faa939706783d38b1c4c2cadc0026931df6ccd6c4b82a58df30` | CREATED_AND_VALIDATED |
| `kaggle_uploads/00_code/certvic_notebooks_bundle.zip` | 196297 | `b268cd84be7b8976b30b36b98b7bf58c5e8985fc4b5139d1ab1d0945f4b27ae2` | CREATED_AND_VALIDATED |
| `kaggle_uploads/00_code/certvic_configs_bundle.zip` | 45814 | `4095c4b947a4d1fbfe67cca32ea3861b4782dde19da62184d38c0baf869dcd40` | CREATED_AND_VALIDATED |
| `kaggle_uploads/00_code/certvic_execution_tools_bundle.zip` | 132032 | `b676b4829088cbf8ce2166de0fd2f335d5cfc5e9de2523d81dbf59de817c9a19` | CREATED_AND_VALIDATED |
| `kaggle_uploads/00_code/certvic_synthetic_validation_bundle.zip` | 37962 | `1816c27b2de6155b6add2f993277cf2c0050eec8c676e09e9590f0532a7b6075` | CREATED_AND_VALIDATED |

## External and gated items

| Output | Status | Builder | Expected size |
| --- | --- | --- | --- |
| `kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip` | PROVISIONED_CLEAN_LINUX_CP310_VALIDATED | `python3 -m certvic.cvpr.wheelhouse_builder --mode LOCAL_VERIFY_ONLY --requirements-root requirements --wheel-root local_inputs/wheelhouse/linux_cp310 --output kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip` |  |
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

Use `kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md`. The exact Phase B command is:

```bash
python3 scripts/run_phase_b_cpu_workflows.py --out reports/kaggle_execution_pack/phase_b_cpu_validation
```
