# Upload files for 09_CONFIRMATORY_INTERNVL

Readiness: `WAITING_FOR_HUMAN_REVIEW`.

Always attach `inputs/00_COMMON/` to execution notebooks. Attach only authenticated ZIPs; Kaggle dataset titles, owners, filenames, extensions, mounts, and nesting may vary because runbooks discover by content.

Expected files:

- `certvic_confirmatory_internvl_input.zip` (not present)

Builder or provisioning action: `python3 -m certvic.cvpr.scientific_input_builder --study confirmatory --provider internvl --config local_inputs/09_confirmatory_internvl.json --run-tag specificity_confirmatory_v1`.

Keep `paper_evidence=false`. Never substitute a similarly named or unauthenticated archive.
