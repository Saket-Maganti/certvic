# Upload files for 15_SECOND_DOMAIN_GENERATION

Readiness: `CONDITIONAL_NOT_AUTHORIZED`.

Always attach `inputs/00_COMMON/` to execution notebooks. Attach only authenticated ZIPs; Kaggle dataset titles, owners, filenames, extensions, mounts, and nesting may vary because runbooks discover by content.

Expected files:

- `certvic_coco_generation_input.zip` (not present)

Builder or provisioning action: `python3 -m certvic.cvpr.build_all_kaggle_inputs --with-external-roots local_inputs/second_domain_external_roots.yaml`.

Keep `paper_evidence=false`. Never substitute a similarly named or unauthenticated archive.
