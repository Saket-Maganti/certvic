# Upload files for 06_PRE_SMOKE_PERMISSIONS

Readiness: `WAITING_FOR_PRIOR_RETURN`.

Always attach `inputs/00_COMMON/` to execution notebooks. Attach only authenticated ZIPs; Kaggle dataset titles, owners, filenames, extensions, mounts, and nesting may vary because runbooks discover by content.

Expected files:

- `certvic_pre_smoke_permissions.zip` (not present)

Builder or provisioning action: `python3 -m certvic.cvpr.pre_smoke_packager --config local_inputs/pre_smoke_inputs.json`.

Keep `paper_evidence=false`. Never substitute a similarly named or unauthenticated archive.
