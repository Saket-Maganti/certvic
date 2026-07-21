# Confirmatory generation external handoff

Prerequisites: strict all-provider 00C2 GO, verified private ADE20K validation source/license manifest,
licensed edit assets, the frozen authority/analysis locks, exclusion inventory, and the offline
wheelhouse. Create `local_inputs/confirmatory_generation_input_roles.json` with `control_files` keys
exactly `source_manifest`, `exclusion_inventory`, `generation_config`, `licenses`, `engine_policy`,
`seed_plan`, `shard_plan`, and `resume_ledger`, each pointing to its real frozen file. Then run:

```bash
python3 -m certvic.cvpr.confirmatory_input_builder --config local_inputs/confirmatory_generation_input_roles.json --output kaggle_uploads/05_confirmatory/certvic_confirmatory_generation_input.zip
python3 -m certvic.cvpr.kaggle_bundle verify kaggle_uploads/05_confirmatory/certvic_confirmatory_generation_input.zip
```

Publish it privately as `certvic/certvic-confirmatory-generation-input`, attach at
`/kaggle/input/certvic-confirmatory-generation-input`, and run
`notebooks/kaggle/cvpr/01_specificity_confirmatory_generation_T4x2.ipynb` with T4x2, Internet off.
Download `confirmatory_generation_return.zip` unchanged to
`local_inputs/generation_returns/specificity_confirmatory_cvpr/`, then run
`python3 scripts/run_all_cpu_workflows.py --resume`.
