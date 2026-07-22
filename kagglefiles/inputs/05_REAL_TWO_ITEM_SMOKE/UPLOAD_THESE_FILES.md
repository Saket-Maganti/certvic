# Upload files for 05_REAL_TWO_ITEM_SMOKE

Readiness: `WAITING_FOR_EXTERNAL_BYTES`.

Always attach `inputs/00_COMMON/` to execution notebooks. Attach only authenticated ZIPs; Kaggle dataset titles, owners, filenames, extensions, mounts, and nesting may vary because runbooks discover by content.

Expected files:

- `certvic_real_two_item_smoke_bundle.zip` (not present)

Builder or provisioning action: `python3 -m certvic.cvpr.smoke_input_builder --task-manifest local_inputs/smoke/real_smoke_tasks.jsonl --output kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip`.

Keep `paper_evidence=false`. Never substitute a similarly named or unauthenticated archive.
