
# CertVIC Absolute-Final Validation

All captured validations are artifact-derived and fail closed.

- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q`: exit 0; 797 passed in 39.85s
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests/test_cvpr_absolute_final.py`: exit 0; 10 passed in 2.71s
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests/test_cvpr_absolute_final.py tests/test_cvpr_execution_closure.py tests/test_cvpr_final_integration.py tests/test_cvpr_runtime_hardening.py tests/test_cvpr_pre_execution.py`: exit 0; 60 passed in 4.88s
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q`: exit 0; 807 passed in 36.90s
- `python3 -m ruff check --no-cache certvic scripts tests`: exit 0; All checks passed
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q certvic scripts tests`: exit 0; passed
- `python3 -m certvic.cvpr.notebook_validation --root notebooks/kaggle/cvpr`: exit 0; 16 observed; 16 passed
- `python3 scripts/validate_t4x2_notebooks.py`: exit 0; 6 observed; 6 passed
- `python3 -m certvic.validation.claim_language_guard --root README.md docs paper paper_cvpr reports/cvpr_pre_execution reports/cvpr_final_integration reports/cvpr_absolute_final --out reports/cvpr_absolute_final/claim_guard.md`: exit 0; 0 findings
- `python3 -m certvic.security.release_privacy_audit --root . --out reports/cvpr_absolute_final/privacy_audit.md --json-out reports/cvpr_absolute_final/privacy_audit.json`: exit 0; 0 findings
- `pdflatex -interaction=nonstopmode -halt-on-error main.tex twice`: exit 0; 3-page PDF; both passes exit 0
- `python3 scripts/build_cvpr_absolute_final.py --rebuild-release`: exit 0; clean extraction and internal deterministic rebuild passed
- `python3 scripts/audit_cvpr_execution_closure_release.py --archive release/certvic_cvpr_execution_closure.zip --out reports/cvpr_absolute_final/release_audit.json`: exit 0; manifest membership and every member hash passed
- `python3 scripts/audit_release_candidate.py --no-fail`: exit 0; privacy passed; historical main_200 release_ready=false with 2 declared blockers

Explicit checks cover canonical/mixed schema rejection, all Main builder families through generation,
canonical Main analysis joins, strict generation packages, review-bound selection, protected-scene
negatives, prospective engines, exact/tampered smoke ZIPs, signed permissions including expiry and
Main GO prerequisite, Main final output names, attribute safety, 100/300/600/1,000-row solver stress,
all-route synthetic closure, post-run permission checks, 16 output-free notebooks, claim/privacy
guards, paper compile, clean extraction, release audit, and deterministic rebuild.

Boundary assertions: `paper_evidence=false`; genuine `human_reviewed=true` count 0; Main and COCO
`execution_allowed=false`; no real GPU evidence or labels; V2-30 retrospective; no mixed schema; no
manual success report authorizes execution.
