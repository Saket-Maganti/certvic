# CertVIC Codex V2 Prompt 10 — Recipe-First Artifact Release

Do not rehost non-redistributable pixels. Do not package private dataset pixels. Do not use paid services.

## Goal

Make the artifact release story CVPR-grade: recipe-first, license-aware, reproducible, and hashed.

## Tasks

1. Add package:
   - `certvic/release/__init__.py`
   - `certvic/release/build_artifact.py`
   - `certvic/release/data_card.py`

2. Add command:

   `python3 -m certvic.release.build_artifact --config configs/release_recipe.yaml --out-dir release/certvic_recipe_artifact`

3. Package:
   - source pointers/hashes
   - masks metadata
   - edit plans
   - task manifests
   - prediction schemas
   - metrics/report scripts
   - docs
   - no forbidden pixels by default

4. Add config:
   - `configs/release_recipe.yaml`

   Fields:
   - include_cc0_pixels
   - include_pointer_only_sources
   - include_generated_edits
   - require_license_verified
   - exclude_private_paths
   - anonymize_local_paths
   - hash_manifests
   - write_checksums

5. Add release audit:
   - no absolute private paths unless allowed
   - no non-rehostable pixels
   - license summary
   - checksum manifest
   - reproducibility command list
   - zero-cost statement

6. Add data-card generator:

   `python3 -m certvic.release.data_card --manifests data/manifests --out release/DATA_CARD_GENERATED.md`

7. Add tests:
   - `tests/test_v2_release_recipe.py`

8. Update docs:
   - `docs/DATA_CARD.md`
   - `docs/REPRO.md`
   - `docs/ZERO_COST_POLICY.md`

9. Create:
   - `docs/V2_RECIPE_FIRST_ARTIFACT_REPORT.md`

10. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, commands added, whether artifact release passed, and next prompt: `11_V2_PAPER_SCAFFOLD_MAJOR_UPGRADE.md`.
