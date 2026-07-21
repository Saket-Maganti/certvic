# Reproducibility and Release Audit

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

The code path is substantially stronger than the evidence-release path; they must be evaluated separately.

## Current package locks

- Main code/config bundle: `3e311fcb3f16ab6fdad839e2e340965bf5d65dca96938ef5a206b77d727b8447`;
  426 manifest entries and content digest
  `cda7d7fcf1208f3e387f1c638864e9568942487b46cda75a8e441f1c4a557450`.
- Retrospective private V2 bundle: `61102740bb1ad76d0315b65839c3a73ad502fd204b77b1634a5003913e29d277`; 30 tasks and
  60 hash-locked image members.
- Private blinded reviewer bundle: `d6e777d035fa806d0b4ffb42cd6c140e08c1187a571770ba87b70c629c3f044f`; blank human fields and no coordinator keys.
- `dist/certvic_main200_session2_data.zip`: quarantined historical/non-release archive.

## Reproducible surfaces

- Canonical raw prediction files are hash-bound in the evidence ledger.
- V1 item membership and frozen decision rule are preserved.
- V2 package construction and importer now have deterministic/transactional contracts.
- Pairwise statistics use explicit fixed bootstrap seeds.
- Synthetic results remain labeled test fixtures.

## Minimal reproducible path

1. Run `python3 -m pytest -q` and `python3 -m ruff check --no-cache certvic scripts tests`.
2. Inspect `CERTVIC_EVIDENCE_LEDGER.json`, then run
   `python3 scripts/rebuild_v11_supported_analysis.py` to reproduce supported numbers.
3. Inspect private pending packages with `scripts/build_spurious_v2_control.py`,
   `scripts/validate_t4x2_notebooks.py`, and the human-review packet validator.
4. Before any provider run, fill exact model commits and preserve the printed code/control hashes.
5. Import returned archives only through `scripts/import_v9_spurious_v2_outputs.py`.
6. Read `CERTVIC_GATE_LEDGER.csv`; do not infer a gate from a point estimate.
7. Build the paper twice with `pdflatex -interaction=nonstopmode -halt-on-error main_v11.tex`
   and visually inspect the rendered pages.
8. Read `CERTVIC_BLOCKER_REGISTER.csv` and the master handoff before selecting any next experiment.

## Release blockers

- Historical model/processor revisions are missing.
- Independent human review and exclusion provenance are incomplete.
- V2 imagery has `redistribution_allowed=false` in source metadata.
- `dist/certvic_main200_session2_data.zip` contains 182
  private-root occurrences and is explicitly non-release material.
- Repository-root LICENSE/COPYING present: false; paper
  bibliography present: false.
- Older archives and generated results contain scoped or stale manifests; release integrity must use
  current hashes rather than V10.2 hash claims.
- The initial broad path scan found 195 files containing a private-root prefix, while older privacy
  checks excluded several generated/data trees. This V11 packet itself uses `<PROJECT_ROOT>` only.

## Safe release boundary

Until licensing is resolved, release code, schemas, task IDs, hashes, derived aggregate tables, and
pointer manifests; keep source-derived image bundles private. Run claim, privacy, package, anonymity,
and manifest checks on the exact candidate archive, not only on selected source trees.
