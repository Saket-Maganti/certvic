# CertVIC Phase A to Phase B Handoff

## Built

Phase A created and verified all five repository-only upload ZIPs, regenerated all 20 canonical output-free runbooks, implemented the v1 secure bundle schema, offline wheelhouse/snapshot/smoke/permission/generation/scientific builders, T4x2 parallel and single-T4 fallback contracts, deterministic seed hierarchy, common notebook bootstrap, canonical return ZIP naming, upload map, runtime estimates, and failure playbooks.

| Path | Bytes | SHA-256 | Status |
| --- | ---: | --- | --- |
| `kaggle_uploads/00_code/certvic_code_bundle.zip` | 1233565 | `f3d27703ed0e1d9a4792ba92ae1594bb6b22af562fe816efa5900e742fe444d8` | CREATED_AND_VALIDATED |
| `kaggle_uploads/00_code/certvic_notebooks_bundle.zip` | 207365 | `d2304331a346cc29484b38062e459da8f3dd098c5a0961776a16fd1338ce82e9` | CREATED_AND_VALIDATED |
| `kaggle_uploads/00_code/certvic_configs_bundle.zip` | 46527 | `64df5cb66455f72f56ebad0cc2c6575af4c183a6dcecfdcd4002c2adfd8d34f6` | CREATED_AND_VALIDATED |
| `kaggle_uploads/00_code/certvic_execution_tools_bundle.zip` | 176318 | `731fd5b7d31e19b06fee1482e164d2ea4c9e9ca22acf3ef3653f4dfde2377397` | CREATED_AND_VALIDATED |
| `kaggle_uploads/00_code/certvic_synthetic_validation_bundle.zip` | 38104 | `9b4f0c67af7f552ef4eff0198d7d9f0c0e5be1d7b5b3351d12e99bb2f42bb92c` | CREATED_AND_VALIDATED |

## External bytes still absent

Only Linux CPython 3.10 wheels, three immutable model snapshots and commits, two real licensed smoke items, licensed ADE20K/COCO/source/insertion bytes, genuine reviewer outputs, and gate-derived permissions/task freezes remain external. Their exact builders and statuses are below; no fake bytes were created.

| Output | Status | Builder | Expected size |
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

## Phase B CPU workflows

Phase B must execute the full pytest suite, focused Kaggle builder/security/sharding/seed/bootstrap tests, Ruff, compileall, 20-runbook static validation, 21-route synthetic notebook execution proof, bundle verification and deterministic rebuild, doctor, next-action, run graph, artifact registry, claim/privacy guards, paper compile, and clean maximum-release rebuild. It must not launch a real model or scientific GPU run.

Begin Phase B exactly with:

```bash
python3 scripts/run_phase_b_cpu_workflows.py --out reports/kaggle_execution_pack/phase_b_cpu_validation
```

PHASE_A_KAGGLE_PACKAGING_COMPLETE  
ALL_BUILDABLE_UPLOAD_ZIPS_CREATED  
ALL_EXTERNAL_BUNDLE_BUILDERS_READY  
ALL_16_RUNBOOKS_VALIDATED  
READY_FOR_PHASE_B_CPU_EXECUTION
