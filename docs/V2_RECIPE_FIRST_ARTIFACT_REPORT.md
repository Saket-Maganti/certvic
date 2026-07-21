# V2 Recipe-First Artifact Report

Date: 2026-06-22
Prompt: `10_V2_ARTIFACT_RELEASE_RECIPE_FIRST.md`

## What was added

- `certvic/release/__init__.py`, `certvic/release/build_artifact.py`,
  `certvic/release/data_card.py`.
- `configs/release_recipe.yaml`.

## Behavior

Packages manifests (pointers, hashes, masks metadata, edit plans, task manifests)
and reproducibility scripts. No non-redistributable pixels by default. Anonymizes
private absolute paths, writes checksums.json and release_audit.json (no private
paths, no forbidden pixels, license summary, reproducibility commands, zero-cost
statement). data_card generator emits a recipe-first data card.

## Tests

- `tests/test_v2_release_recipe.py` — 4 tests (recipe-first defaults, anonymize +
  audit pass, no pixels packaged, data card). Full suite: **193 passed** (was 189).

## Status: PASS. Next: `11_V2_PAPER_SCAFFOLD_MAJOR_UPGRADE.md`.
