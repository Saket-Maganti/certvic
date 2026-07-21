# Kaggle rerun steps after the free-form diagnostic parser crash

1. Stop the failed cell.
2. Upload/use the `*_DIAGNOSTIC_FREEFORM_FIXED.ipynb` notebook for the provider.
3. Set the same `RUN_TAG`, usually `mechanism`.
4. Keep the same attached inputs: CertVIC code bundle + mechanism bundle.
5. Before launching, delete old incomplete mechanism files in `/kaggle/working`:

```python
from pathlib import Path
for pat in ["*mechanism*shard*.jsonl", "*mechanism*.zip", "*mechanism*summary*.json", "*mechanism*manifest*.json", "log_*mechanism*shard*.txt"]:
    for p in Path("/kaggle/working").glob(pat):
        print("Removing", p)
        p.unlink()
```

6. Run all cells.
7. Expected merged output for mechanism: `pred_<provider>_mechanism.jsonl` with 364 rows.

No need to rerun spurious/perception_scaled/polarity if they already completed.
