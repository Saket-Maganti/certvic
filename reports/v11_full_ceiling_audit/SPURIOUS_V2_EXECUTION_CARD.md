# Spurious V2 Execution Card

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

This card prevents a diagnostic run from being mistaken for confirmatory evidence.

## Before execution

This is an optional retrospective diagnostic run, not the mandatory independent confirmatory set.
Before uploading, complete or explicitly waive diagnostic-only review without exposing V1 outcomes,
fill each notebook's `MODEL_REVISION` with an exact 40-character commit, and rerun the local locks.

```bash
python3 scripts/build_kaggle_main200_bundle.py
python3 scripts/build_spurious_v2_control.py
python3 scripts/validate_t4x2_notebooks.py \
  --out reports/v11_full_ceiling_audit/notebook_static_validation.json
python3 -m pytest -q tests/test_v9_spurious_v2_ingest_decision.py \
  tests/test_v9_spurious_v2_builder.py tests/test_v9_spurious_v2_runbooks.py
```

## Exact Kaggle inputs and settings

Upload both inputs to each private notebook session:

1. `dist/certvic_kaggle_main200_bundle.zip`
2. `dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip`

Use Accelerator `GPU T4 x2`, Internet `ON` for a fresh public-model download, no paid API,
and no credential except an optional Hugging Face read token when the repository requires it.
The notebooks verify task, 60 image-member, code-bundle, control-bundle, and model-revision locks.

Run in this exact operational order:

1. `notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb`
2. `notebooks/kaggle/vlm_internvl_8b_spurious_v2_T4x2.ipynb`
3. `notebooks/kaggle/vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb`

Each notebook must produce exactly 60 merged rows and one schema-v3 runtime manifest. Expected
archives are `qwen2_5_vl_7b_spurious_v2_preds.zip`,
`internvl_8b_spurious_v2_preds.zip`, and `llava_onevision_7b_spurious_v2_preds.zip`.
Runbook-only T4x2 estimates, not measured V11 runtimes, are 12--25, 10--20, and 15--30 minutes;
single-GPU fallback estimates are 25--45, 20--40, and 30--60 minutes respectively.

## During and after execution

Download all three archives into `kaggleoutputs/v9_spurious_v2/`, then run:

```bash
python3 scripts/import_v9_spurious_v2_outputs.py \
  --input-dir kaggleoutputs/v9_spurious_v2 \
  --out-dir data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest
python3 -m pytest -q tests/test_v9_spurious_v2_ingest_decision.py
```

The importer requires all three providers at once, exact source/prediction hashes, 60 rows each,
strict parses, exact item/variant keys, provider/run IDs, pinned revisions, and conflict-free atomic
writes. Missing or unparseable pairs fail closed. The result remains `DIAGNOSTIC_ONLY` and
`paper_evidence=false` regardless of its numerical rate; it cannot unlock Main-500.
The final diagnostic gate artifact is
`data/results/main_real_200/v9_mega_upgrade/spurious_v2_specificity_results.json`
(or the explicit `--report-dir`);
do not route this retrospective set through the Main-500 readiness gate.

For recovery, rerun the same notebook with unchanged inputs/revision. Complete shard files are
reused only when their exact denominators validate; incomplete shards resume, merge is deterministic,
and any canonical hash conflict stops without overwrite.

## Stop condition

If hashes, provider/run IDs, item/variant keys, strict parsing, or row counts disagree, stop and
preserve inputs. Do not partially write canonical outputs.
