# Wheelhouse validation handoff

The Linux x86-64/CPython 3.10 wheel set is locally provisioned. Canonical output:
`kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip`. Its clean Docker validation installs all
five provider/generation/analysis locks with `--no-index --find-links` and imports every runtime module;
the exact result is `reports/non_human_closure/wheelhouse_clean_linux_validation.json`. 00A must repeat
that check in a fresh Kaggle CPU session, accelerator off and Internet off, because 00A also binds the
Kaggle environment identity. The provisioning notebook remains a recovery route only.
