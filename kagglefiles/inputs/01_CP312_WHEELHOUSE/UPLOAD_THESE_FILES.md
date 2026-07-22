# Upload files for 01_CP312_WHEELHOUSE

Readiness: `WAITING_FOR_EXTERNAL_BYTES`.

Always attach `inputs/00_COMMON/` to execution notebooks. Attach only authenticated ZIPs; Kaggle dataset titles, owners, filenames, extensions, mounts, and nesting may vary because runbooks discover by content.

Expected files:

- `certvic_offline_wheelhouse_cp312.zip` (not present)

Builder or provisioning action: `Run runbooks/00_PROVISIONING/00_build_certvic_cp312_wheelhouse.ipynb`.

Keep `paper_evidence=false`. Never substitute a similarly named or unauthenticated archive.
