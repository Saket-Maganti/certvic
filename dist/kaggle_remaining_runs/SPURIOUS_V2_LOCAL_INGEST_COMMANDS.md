# Retrospective Spurious V2 Diagnostic Local Ingest Commands

```bash
mkdir -p kaggleoutputs/v9_spurious_v2
# place qwen2_5_vl_7b_spurious_v2_preds.zip, internvl_8b_spurious_v2_preds.zip, and llava_onevision_7b_spurious_v2_preds.zip there
python3 scripts/import_v9_spurious_v2_outputs.py --input-dir kaggleoutputs/v9_spurious_v2 --out-dir data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest
python3 -m pytest -q tests/test_v9_spurious_v2_ingest_decision.py
```

The importer must keep `paper_evidence=false` even when all files are valid: this 30-item set is a retrospective post-outcome V1 subset and can only support diagnostic sensitivity analysis.
