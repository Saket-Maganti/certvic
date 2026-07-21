# Importer Negative Test

Safe failure: `true`

## Command

```bash
python3 scripts/import_v9_spurious_v2_outputs.py --input-dir /tmp/certvic_empty_spurious_v2_import --out-dir data/results/main_real_200/v10_2_final_pre_run_sanity/importer_empty_out --canonical-dir data/results/main_real_200/v10_2_final_pre_run_sanity/importer_empty_canonical --report-dir data/results/main_real_200/v10_2_final_pre_run_sanity || true
```

## Result

- Status: `BLOCKED_MISSING_PREDICTIONS`
- Missing providers: `qwen2_5_vl_7b, internvl_8b, llava_onevision_7b`
- Canonical results changed: `false`
- `paper_evidence`: `false`
- Canonical files created: `0`

The importer failed closed on missing real outputs. No predictions were fabricated and no canonical evidence was promoted.
