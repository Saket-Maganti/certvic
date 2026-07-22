# Upload files for 07_CONFIRMATORY_GENERATION

Readiness: `WAITING_FOR_EXTERNAL_BYTES`.

Always attach `inputs/00_COMMON/` to execution notebooks. Attach only authenticated ZIPs; Kaggle dataset titles, owners, filenames, extensions, mounts, and nesting may vary because runbooks discover by content.

Expected files:

- `certvic_confirmatory_generation_input.zip` (not present)

Builder or provisioning action: `python3 -m certvic.cvpr.confirmatory_input_builder --config local_inputs/confirmatory_generation_inputs.json`.

Keep `paper_evidence=false`. Never substitute a similarly named or unauthenticated archive.
