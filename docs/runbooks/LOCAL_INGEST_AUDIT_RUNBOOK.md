# V8 Local Ingest and Audit Runbook

All V8 outputs are pilot or diagnostic only. Do not mark paper_evidence=true. Do not run paid APIs or paid cloud.

```bash
python3 scripts/build_v8_upgrade.py
python3 -m pytest -q tests/test_v8_upgrade.py
python3 -m pytest -q
python3 -m certvic.validation.claim_language_guard --root docs --out data/results/main_real_200/v8_upgrade/claim_guard_final.md
python3 -m certvic.security.release_privacy_audit --root . --out data/results/main_real_200/v8_upgrade/privacy_audit_final.md --json-out data/results/main_real_200/v8_upgrade/privacy_audit_final.json
```
