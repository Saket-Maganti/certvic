# Upload files for 00_COMMON

Readiness: `READY_NOW`.

Always attach `inputs/00_COMMON/` to execution notebooks. Attach only authenticated ZIPs; Kaggle dataset titles, owners, filenames, extensions, mounts, and nesting may vary because runbooks discover by content.

Expected files:

- `certvic_code_bundle.zip` (present and verified)
- `certvic_configs_bundle.zip` (present and verified)
- `certvic_execution_tools_bundle.zip` (present and verified)

Builder or provisioning action: `python3 -m certvic.cvpr.build_all_kaggle_inputs --local-only`.

Keep `paper_evidence=false`. Never substitute a similarly named or unauthenticated archive.
