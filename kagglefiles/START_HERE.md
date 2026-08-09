OPEN ONLY THIS FOLDER FOR KAGGLE EXECUTION.
DO NOT NAVIGATE THE REST OF THE REPOSITORY.

# CertVIC CVPR 2027 next action

Active runtime profile: `kaggle_cp312_2026_07`. The historical provisioning action `BUILD_CP312_WHEELHOUSE` is complete; do not repeat it unless the authenticated doctor state explicitly regresses.

Current authenticated state: 00A is valid; all three 00B snapshot smokes are valid; the 00B matrix is complete. The 00C2 real-model smoke remains `NOT_AUTHORIZED` because two genuine license-eligible paired items are absent. `paper_evidence=false`; genuine human-reviewed count is zero; Main and the second domain are not authorized.

## Do this now

Provide exactly two real, non-synthetic original/edited image pairs with `license_eligible=true`, a concrete auditable `license_id`, zero overlap with historical items, and the frozen prompt/parser/run-contract metadata. Do not open a GPU session yet.

After local validation creates three provider permissions, run the 00C2 rows in `CVPR2027_NEXT_RUNS.csv`. Suggested accounts are conveniences only: lancerdevsm for Qwen, saket9500 for InternVL, and examhelps for LLaVA. Each run uses T4x2, Internet OFF, and has a 20–60 minute planning estimate.

After every download:

```bash
python3 kagglefiles/import_kaggle_return.py /path/to/downloaded_return.zip
bash kagglefiles/run_local_resume.sh
```

Never rename archive contents, edit executable runbook configuration, reuse a consumed permission, bypass a gate, or treat a planning estimate as measured runtime.
