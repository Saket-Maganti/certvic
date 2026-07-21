# CertVIC first Kaggle integrity wave handoff

00A and 00B are CPU integrity stages; neither loads a model nor performs inference. 00C2 is the first
genuine GPU model-load/inference stage and is not authorized by this handoff. Publish every ZIP as a
private Kaggle dataset, preserve its filename and SHA-256, use a fresh session, and disable Internet.
The seven smoke-stage notebooks require no manual configuration edits; attach the exact datasets and
click Run All. See `reports/non_human_closure/CERTVIC_KAGGLE_ZERO_EDIT_SMOKE_HANDOFF.md` for the
complete per-notebook cards.

| Common upload | Bytes | SHA-256 | Dataset | Mount |
| --- | ---: | --- | --- | --- |
| `kaggle_uploads/00_code/certvic_code_bundle.zip` | 1167565 | `e670d70146f79471d0163fbf6024b49aa1a068befb769b2d6ac345e730ffb46e` | `certvic/certvic-code` | `/kaggle/input/certvic-code` |
| `kaggle_uploads/00_code/certvic_configs_bundle.zip` | 45697 | `0a10cf9b570dd7769d2c24c84d406be1d7c64cc0fabd774c4354572a7bda1db8` | `certvic/certvic-configs` | `/kaggle/input/certvic-configs` |
| `kaggle_uploads/00_code/certvic_execution_tools_bundle.zip` | 121856 | `d06e1d6a25ae6689dfc5a5d3b8e37170f46c567ea25ffb2b669acc0ca8f3c1b8` | `certvic/certvic-execution-tools` | `/kaggle/input/certvic-execution-tools` |
| `kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip` | 3188416530 | `d62fe562ee7d012062c03fad3537f0a4da71e0e860b04b9dc7b6f942f4d15bda` | `certvic/certvic-offline-wheelhouse` | `/kaggle/input/certvic-offline-wheelhouse` |

| Provider | Snapshot ZIP | SHA-256 | Dataset |
| --- | --- | --- | --- |
| `qwen2_5_vl_7b` | `kaggle_uploads/02_snapshots/qwen2_5_vl_7b_snapshot.zip` | `ABSENT` | `certvic/qwen2-5-vl-7b-snapshot` |
| `internvl_8b` | `kaggle_uploads/02_snapshots/internvl2_8b_snapshot.zip` | `ABSENT` | `certvic/internvl2-8b-snapshot` |
| `llava_onevision_7b` | `kaggle_uploads/02_snapshots/llava_onevision_7b_snapshot.zip` | `ABSENT` | `certvic/llava-onevision-7b-snapshot` |

## Exact runs

| Run | Notebook / parameters | Accelerator | Return ZIP | Unchanged local destination |
| --- | --- | --- | --- | --- |
| 00A | `00A_certvic_code_and_environment_smoke.ipynb` | off | `00A_environment_bundle.zip` | `data/runtime/00A_environment_bundle.zip` |
| 00B Qwen | `00B_qwen2_5_vl_7b_snapshot_smoke.ipynb` | off | `00B_qwen2_5_vl_7b_snapshot_bundle.zip` | `data/runtime/00B_qwen2_5_vl_7b_snapshot_bundle.zip` |
| 00B InternVL | `00B_internvl_8b_snapshot_smoke.ipynb` | off | `00B_internvl_8b_snapshot_bundle.zip` | `data/runtime/00B_internvl_8b_snapshot_bundle.zip` |
| 00B LLaVA | `00B_llava_onevision_7b_snapshot_smoke.ipynb` | off | `00B_llava_onevision_7b_snapshot_bundle.zip` | `data/runtime/00B_llava_onevision_7b_snapshot_bundle.zip` |

Run 00A first. After its unchanged return validates locally, run the three isolated 00B sessions in
parallel or sequence. Attach exactly one provider snapshot to each 00B session. Do not set a mutable
revision, do not enable model loading, and do not rename a return. After each download run:

```bash
python3 scripts/run_all_cpu_workflows.py --resume
```

The resume verifies ZIP security, schemas, byte identities, the immutable model/processor contract,
and `paper_evidence=false`; it refuses partial matrices. Follow
`reports/non_human_closure/CERTVIC_REAL_SMOKE_EXTERNAL_EXECUTION_HANDOFF.md` only after the complete
00A/00B matrix and the licensed two-item smoke bundle exist. No prompt, path, model identity,
commit, architecture, hash, permission ID, or output filename is entered by the operator.
