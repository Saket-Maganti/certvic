# Upload files for 03_INTERNVL_SNAPSHOT

Readiness: `WAITING_FOR_EXTERNAL_BYTES`.

Always attach `inputs/00_COMMON/` to execution notebooks. Attach only authenticated ZIPs; Kaggle dataset titles, owners, filenames, extensions, mounts, and nesting may vary because runbooks discover by content.

Expected files:

- `internvl2_8b_snapshot.zip` (not present)

Builder or provisioning action: `Run runbooks/00_PROVISIONING/02_build_internvl_8b_snapshot.ipynb`.

Keep `paper_evidence=false`. Never substitute a similarly named or unauthenticated archive.
