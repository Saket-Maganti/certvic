
# CertVIC Execution Closure Validation

Final machine-captured commands and exact totals are recorded in
`reports/cvpr_execution_closure/validation_results.json` and the commands CSV. The sealed gate requires
focused/full pytest, Ruff, compileall, notebook static checks, synthetic end-to-end execution, claim
and privacy guards, paper compile, release audit, clean extraction, and byte-identical archive rebuild.

Explicit boundary checks: `paper_evidence=false`; structured `human_reviewed=true` count is zero;
Main and second-domain `execution_allowed=false`; no real GPU evidence or human labels were created;
V2-30 remains retrospective; required closure paths contain no `NotImplementedError`; generation
uses concurrent `Popen` workers after one global slice; stale resume binds the full run-contract hash;
raw and canonical hashes are separate; and the release imports/runs from a clean extraction.


Final capture:

- `python3 -m pytest -q (pre-closure baseline)`: exit 0; 774 passed in 36.12s
- `python3 -m pytest -q tests/test_cvpr_execution_closure.py tests/test_cvpr_runtime_hardening.py tests/test_cvpr_pre_execution.py tests/test_v7_second_domain.py`: exit 0; 43 passed in 2.97s
- `python3 -m pytest -q`: exit 0; 786 passed in 35.01s
- `python3 -m ruff check --no-cache certvic scripts tests`: exit 0; All checks passed
- `python3 -m compileall -q certvic scripts`: exit 0; clean
- `python3 -m certvic.cvpr.notebook_validation --root notebooks/kaggle/cvpr`: exit 0; 16 expected, 16 observed, 16 passed
- `python3 -m certvic.cvpr.synthetic_study --out-dir <EMPTY_DIR>`: exit 0; SYNTHETIC_END_TO_END_FIXTURE_COMPLETE
- `python3 -m certvic.validation.claim_language_guard --root README.md docs paper paper_cvpr reports/cvpr_pre_execution reports/cvpr_runtime_hardening reports/cvpr_execution_closure`: exit 0; 0 findings; passed
- `python3 -m certvic.security.release_privacy_audit --root .`: exit 0; 0 findings; passed
- `cd paper_cvpr && pdflatex -interaction=nonstopmode -halt-on-error main.tex`: exit 0; 3-page PDF built
- `python3 scripts/build_cvpr_execution_closure.py`: exit 0; byte-identical double rebuild and clean-extraction fixture passed
- `python3 scripts/audit_cvpr_execution_closure_release.py`: exit 0; membership, byte hashes, weight exclusion, and synthetic-pixel policy passed
- `git diff --check`: exit NOT_APPLICABLE; checkout root is not a Git worktree
