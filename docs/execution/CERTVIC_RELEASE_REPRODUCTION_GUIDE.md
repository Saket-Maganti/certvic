
# CertVIC Release Reproduction Guide

Build twice with `python3 scripts/build_cvpr_execution_closure.py`; the two archive SHA-256 values must
match. The archive contains all local Python modules (not a hand-picked partial dependency set),
configs, schemas, notebooks, fixtures, guides, paper source, cards, license matrix, closure reports,
and byte manifests. It excludes datasets, weights, genuine human sheets, credentials, and historical
quarantines.

Extract into an empty directory and set only that extraction root on `PYTHONPATH`. Run the recorded
imports, CLI help commands, and `certvic.cvpr.synthetic_study`. The fixture exercises generation,
mock review/adjudication, three mock providers, atomic import, human-aware analysis, tables, a guarded
paper fragment, and a synthetic release update. Every fixture artifact says
`SYNTHETIC_END_TO_END_FIXTURE` and `paper_evidence=false`.
