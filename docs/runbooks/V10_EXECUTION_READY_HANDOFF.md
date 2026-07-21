# CertVIC V10 Execution Ready Handoff

First recommended execution: Spurious V2 provider notebooks on Kaggle T4x2.

Notebook: `notebooks/kaggle/v10_execution_ready_handoff_t4x2.ipynb`

Import command after download:

```bash
python3 scripts/import_v9_spurious_v2_outputs.py --input-dir kaggleoutputs/v10_spurious_v2
```

Stop conditions:

- Do not run Main-500 while Spurious V2 is unresolved.
- Do not use stress outputs as evidence.
- Do not bypass human review.
- Do not lower thresholds to pass gates.
- Stop on row mismatch, provider mismatch, code bundle mismatch, claim guard failure, or privacy failure.
