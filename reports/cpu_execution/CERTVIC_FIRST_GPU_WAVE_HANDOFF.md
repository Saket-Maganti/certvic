# CertVIC first Kaggle integrity wave handoff

00A and 00B are CPU integrity stages; neither loads a model nor performs inference. 00C2 is the
first genuine GPU model-load/inference stage and is not authorized by this handoff.

Upload the authenticated bundle bytes to any of the four Kaggle accounts. Dataset owners, titles,
slugs, archive names, extensions, mounts, nesting, and notebook filenames are irrelevant to
scientific identity. The same bundle bytes can be reused across accounts without rebuilding
authorizations. Canonical names are optional recommended labels; canonical return ZIP names remain
fixed.

## First wave

| Run | Required authenticated roles | Accelerator | Canonical return |
| --- | --- | --- | --- |
| 00A | `CODE`, `CONFIGS`, `EXECUTION_TOOLS`, `OFFLINE_LINUX_WHEELHOUSE` | Off | `00A_environment_bundle.zip` |
| 00B Qwen | 00A roles + Qwen `MODEL_SNAPSHOT` | Off | `00B_qwen2_5_vl_7b_snapshot_bundle.zip` |
| 00B InternVL | 00A roles + InternVL `MODEL_SNAPSHOT` | Off | `00B_internvl_8b_snapshot_bundle.zip` |
| 00B LLaVA | 00A roles + LLaVA `MODEL_SNAPSHOT` | Off | `00B_llava_onevision_7b_snapshot_bundle.zip` |

Run 00A first. After its unchanged return validates locally, run the three isolated 00B sessions in
parallel or sequence. Attach exactly one provider snapshot identity to each 00B session. Do not set
a mutable revision or enable model loading. After every download run:

```bash
python3 scripts/run_all_cpu_workflows.py --resume
```

The resume verifies archive security, schemas, content identities, immutable model/processor
commits, and `paper_evidence=false`; it refuses partial matrices. The runbooks require no manual
prompt, path, owner, slug, model identity, commit, architecture, hash, permission, or provider edit.

See `reports/non_human_closure/CERTVIC_KAGGLE_ZERO_EDIT_SMOKE_HANDOFF.md` and
`reports/non_human_closure/CERTVIC_MULTI_ACCOUNT_KAGGLE_HANDOFF.md` for the failure codes and
cross-account workflow.
