# CertVIC CVPR Final Validation

Final local-safe validation date: 2026-07-13. Verdict: `CVPR_PRE_EXECUTION_READY` with real
inputs, review, immutable revisions, and execution still blocked. `paper_evidence=false`.

## Passing lanes

| Lane | Exact command | Exit | Result |
| --- | --- | ---: | --- |
| Full suite | `python3 -m pytest -q` | 0 | 764 passed in 32.99 s on the final post-edit rerun |
| Concentrated CVPR/V11/package/import | `python3 -m pytest -q tests/test_cvpr_pre_execution.py tests/test_v11_full_ceiling_audit.py tests/test_v11_human_review_packet.py tests/test_kaggle_bundle.py tests/test_v9_spurious_v2_ingest_decision.py tests/test_open_vlm_import_safety.py` | 0 | 66 passed in 4.50 s |
| New parser/CVPR focused | `python3 -m pytest -q tests/test_cvpr_pre_execution.py tests/test_parse.py` | 0 | 41 passed |
| Ruff | `python3 -m ruff check --no-cache certvic scripts tests` | 0 | all checks passed |
| Compile | `python3 -m compileall -q certvic scripts` | 0 | passed |
| Historical T4x2 static | `python3 scripts/validate_t4x2_notebooks.py --out <TEMP>` | 0 | 6/6 passed; not executed |
| New notebook static/mock runtime | `python3 -m pytest -q tests/test_cvpr_pre_execution.py -k 'notebook or worker or builder'` | 0 | 3 passed; 13 notebooks validated; deterministic two-shard mock package |
| Claim guard | `python3 -m certvic.validation.claim_language_guard --root README.md docs paper paper_cvpr reports/cvpr_pre_execution --out <TEMP>` | 0 | 0 findings |
| Privacy | `python3 -m certvic.security.release_privacy_audit --root . --out <TEMP> --json-out <TEMP>` | 0 | 0 findings |
| Human template QA | `python3 scripts/validate_v11_human_review.py --packet-dir reports/v11_full_ceiling_audit/human_review_packet --allow-blank` | 0 | structurally valid; 4 tracks blank; no agreement computed |
| Paper | two `pdflatex -interaction=nonstopmode -halt-on-error main.tex` passes in `paper_cvpr` | 0 | 1 page; no warning/overfull/underfull/undefined finding on final pass |
| Paper anonymity | `pdfinfo`, `pdftotext`, identity/private-path scan | 0 | blank Author/Title/Subject/Keywords; no identity/path text finding |
| Evidence boundary | machine assertions over CVPR reports/configs/notebooks/paper | 0 | 0 `paper_evidence=true`; 0 `human_reviewed=true`; Main execution false; V2-30 retrospective; no fabricated outputs/labels |
| Release audit | `python3 scripts/audit_release_candidate.py --no-fail` | 0 | audit ran; privacy passed; release_ready=false; 2 declared blockers; 30 safe and 1,566 cannot-release paths |

No standalone type checker is configured in `pyproject.toml`; compileall, Pydantic/runtime schema
checks, Ruff, and tests are the configured local-safe substitutes. Git is absent at the repository
root, so `git diff --check` is not applicable. Bibliography files and the citation verification
matrix exist; bibliography activation remains blocked until citations are source-verified.

## Expected fail-closed exits

| Gate | Command | Exit | Expected state |
| --- | --- | ---: | --- |
| Post-run import | `python3 -m certvic.cvpr.after_runs --input-dir tmp/cvpr_empty_returns --study specificity_confirmatory_cvpr --strict --status-out <TEMP>` | 2 | `BLOCKED_PRECONDITIONS`; immutable revisions/execution approval absent; no canonical output fabricated |
| Human completion | `python3 scripts/validate_v11_human_review.py --packet-dir reports/v11_full_ceiling_audit/human_review_packet` | 2 | `HUMAN_REVIEW_PENDING`; blank sheets rejected |
| Model revision lock | execution-mode registry validation | expected blocked | exactly six 40-character model/processor commit fields required |

## Final locks

- Master plan SHA-256: `1dd1222e06f90f08ef7e38bccf2f644600039f4c7086b6c550827bb60ae521dd`.
- Handoff SHA-256: `14f17fcde2240593d33ff235e88b2d0458d0ffc1ffc0dca85c5e651bc1389118`.
- New notebook manifest SHA-256: `0bc6e294ee90a04bc8f764eb30d63f0db4f7e55ced462e2b7b4ab604f744ed54`.
- Prospective exclusion inventory SHA-256: `9ec1c63a43053f02e0b06b23fda1b3a22ea7c8520d4170ab50837f3b714b33ca`.
- Paper scaffold PDF SHA-256: `9443966ed0615933a28654f4c314c7def53a1e368bc291c717108680d86fa68a`.

The release audit's blocked status is not a software-test failure. It preserves the license/path
boundary and prevents publication of restricted historical pixels or unrelativized sheets.
