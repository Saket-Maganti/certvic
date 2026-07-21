
# CertVIC Kaggle Runtime Smoke Guide

All smoke output is non-evidence. Run 00A for code/environment, 00B once per exact model snapshot,
00C1 only for `SYNTHETIC_MOCK_RUNTIME`, and 00C2 once per provider for
`NON_EVIDENCE_REAL_MODEL_SMOKE`. 00C1 always passes `--mock-runtime`; 00C2 refuses until
`USE_REAL_MODEL=True` and never contains a mock fallback. A real smoke must preserve its ZIP, runtime,
environment, run-contract, peak-VRAM, validation, failure, and hash manifests. Resume only validated
rows; mismatches move to structured quarantine. No smoke may write scientific evidence paths.
