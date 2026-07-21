# Real-model smoke external handoff

The real two-item input cannot be built until two licensed, portable, zero-overlap task pairs exist.
Create the exact JSONL manifest with source/original/edited image paths, any required masks/assets,
expected original/edited answers, license IDs, provenance, and explicit V1/V2-30 zero-overlap proofs;
then run:

```bash
python3 -m certvic.cvpr.smoke_input_builder --task-manifest local_inputs/smoke/real_smoke_tasks.jsonl --output kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip
python3 -m certvic.cvpr.kaggle_bundle verify kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip
python3 scripts/run_all_cpu_workflows.py --resume
```

After valid 00A and all three 00B returns, the resume builds the byte-bound pre-smoke permission. Run
the three provider-specific `00C2_<provider>_real_model_two_item_smoke.ipynb` notebooks, T4 x2
(single-T4 fallback permitted), Internet off. No cell edits are required. Download the unchanged
returns to `data/runtime/00C2_<provider>_real_model_smoke.zip`, then run the same resume command. No
genuine smoke result is claimed before all three ZIPs pass strict local import.
