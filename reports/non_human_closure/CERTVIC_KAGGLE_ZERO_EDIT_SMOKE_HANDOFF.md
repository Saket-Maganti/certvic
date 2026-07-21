# CertVIC zero-edit Kaggle smoke handoff

These are non-evidence integrity and smoke runs. All inputs are selected by authenticated content,
never by Kaggle account, owner, dataset title, slug, mount folder, archive filename, extension,
nesting, or notebook filename. Identical bytes may be uploaded to any of the four Kaggle accounts
under any labels. ZIP-compatible files and authenticated extracted bundle directories are accepted.
Canonical labels in the dataset map are recommendations only.

Do not edit bundle contents, manifests, notebook cells, provider identities, hashes, permissions, or
canonical return ZIP names. Keep Internet off and use a fresh session. A required role may appear
anywhere below `/kaggle/input`, `/kaggle/working`, or `CERTVIC_INPUT_ROOTS`.

## Stable discovery behavior

- No valid candidate: `CERTVIC_DISCOVERY_01_REQUIRED_ROLE_NOT_FOUND`.
- Distinct valid identities for one role: `CERTVIC_DISCOVERY_02_AMBIGUOUS_DISTINCT_CONTENT`.
- Tampering, unsafe members, wrong metadata, or an override mismatch:
  `CERTVIC_DISCOVERY_03_CONTENT_AUTHENTICATION_FAILED`.
- Byte-identical copies are mirrors. The normalized path is selected deterministically and every
  mirror is printed as operational provenance.

## Run cards

| Run | Authenticated roles | Accelerator | Canonical return ZIP |
| --- | --- | --- | --- |
| 00A | `CODE`, `CONFIGS`, `EXECUTION_TOOLS`, `OFFLINE_LINUX_WHEELHOUSE` | Off; zero GPUs enforced | `00A_environment_bundle.zip` |
| 00B Qwen | 00A roles + Qwen `MODEL_SNAPSHOT` | Off; zero GPUs enforced | `00B_qwen2_5_vl_7b_snapshot_bundle.zip` |
| 00B InternVL | 00A roles + InternVL `MODEL_SNAPSHOT` | Off; zero GPUs enforced | `00B_internvl_8b_snapshot_bundle.zip` |
| 00B LLaVA | 00A roles + LLaVA `MODEL_SNAPSHOT` | Off; zero GPUs enforced | `00B_llava_onevision_7b_snapshot_bundle.zip` |
| 00C2 Qwen | 00A roles + Qwen snapshot + `REAL_TWO_ITEM_SMOKE` + `PRE_SMOKE_PERMISSIONS` | T4×2; deterministic one-T4 fallback | `00C2_qwen2_5_vl_7b_real_model_smoke.zip` |
| 00C2 InternVL | 00A roles + InternVL snapshot + smoke + permissions | T4×2; deterministic one-T4 fallback | `00C2_internvl_8b_real_model_smoke.zip` |
| 00C2 LLaVA | 00A roles + LLaVA snapshot + smoke + permissions | T4×2; deterministic one-T4 fallback | `00C2_llava_onevision_7b_real_model_smoke.zip` |

00C2 authenticates its provider permission before hardware detection, snapshot/model access, or
inference. It remains blocked until real licensed smoke bytes and current permissions exist. Main
and COCO remain unauthorized. `paper_evidence=false`; genuine `human_reviewed=true` count remains
zero.

After downloading each unchanged return, run:

```bash
python3 scripts/run_all_cpu_workflows.py --resume
```

For 00A: upload the four required role bundles under any names to any Kaggle account, attach them,
keep accelerator off, keep Internet off, and click Run All.
