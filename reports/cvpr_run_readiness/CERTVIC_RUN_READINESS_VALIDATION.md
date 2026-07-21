# CertVIC Run-Readiness Validation

Machine-captured validation:

- `pytest -q`: exit 1; first failure after 474 passes; privacy audit isolated 2 private-path findings in one newly added prompt artifact
- `pytest -q tests/test_cvpr_run_readiness.py tests/test_cvpr_absolute_final.py tests/test_cvpr_execution_closure.py tests/test_cvpr_runtime_hardening.py tests/test_cvpr_final_integration.py tests/test_cvpr_pre_execution.py`: exit 0; 67 passed in 19.91s
- `pytest -q`: exit 0; 814 passed in 50.96s
- `python3 -m ruff check --no-cache certvic scripts tests`: exit 0; All checks passed
- `python3 -m compileall -q certvic scripts tests`: exit 0; no syntax errors
- `python3 -m certvic.validation.claim_language_guard --root README.md docs paper paper_cvpr reports/cvpr_run_readiness --out reports/cvpr_run_readiness/claim_guard.md`: exit 0; passed; 0 findings
- `python3 -m certvic.security.release_privacy_audit --root . --out reports/cvpr_run_readiness/privacy_audit.md --json-out reports/cvpr_run_readiness/privacy_audit.json`: exit 0; passed; 0 findings
- `cd paper_cvpr && pdflatex -interaction=nonstopmode -halt-on-error main.tex twice`: exit 0; 3 pages; 124026 bytes
- `python3 scripts/build_cvpr_run_readiness.py --with-release`: exit 0; byte-identical rebuild and clean-extraction synthetic closure passed; exact final hash in release/cvpr_execution_closure/ARCHIVE_SHA256.txt
- `python3 scripts/audit_cvpr_execution_closure_release.py`: exit 0; passed; no corrupt members or manifest errors

Required boundary checks remain explicit: zero genuine `human_reviewed=true` artifacts; no real GPU
evidence; no fabricated labels; portable hashes survive rebasing; provider slots reject replay; the
synthetic routes use the actual package/smoke/import contracts; and all synthetic outputs retain
`paper_evidence=false`.
