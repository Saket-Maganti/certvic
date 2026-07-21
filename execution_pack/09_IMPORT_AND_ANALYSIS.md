# Provider reconciliation, transactional import, and analysis

Reconcile each unchanged provider return against the parent matrix:

```bash
python3 -m certvic.cvpr.reconcile_provider_permissions reconcile \
  --matrix MATRIX.json --provider-zip PROVIDER.zip --out RECONCILIATION.json
```

When the full matrix passes, run the two-phase importer:

```bash
python3 -m certvic.cvpr.import_transaction run \
  --matrix MATRIX.json --provider-zip PROVIDER_ZIPS.json \
  --destination data/studies/specificity_confirmatory_cvpr/canonical_import \
  --nonce-ledger data/studies/specificity_confirmatory_cvpr/consumed_nonces.json \
  --evidence-ledger data/studies/specificity_confirmatory_cvpr/evidence_updates.json \
  --gate-ledger data/studies/specificity_confirmatory_cvpr/gate_updates.json \
  --study-import-config PRIVATE_STRICT_IMPORT_CONFIG.json
```

Then run `python3 -m certvic.cvpr.after_runs --input-dir ... --study
specificity_confirmatory_cvpr --project-root . --status-out ... --strict`. Hardware is local CPU;
allow 15–60 minutes. Outputs include immutable raw returns, transaction journal, raw and filtered
statistics, confidence sequence, missingness/completion audits, decision trace, Main decision, and
guarded paper manifest.

Validate exact hashes, complete paired rows, missing-as-failure primary analysis, Bonferroni bounds,
McNemar/Holm exploratory matrix, claim eligibility, guards, and paper branch. Recover interrupted
imports with `import_transaction recover --journal ...`; never delete the journal or nonce ledger.

