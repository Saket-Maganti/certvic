# V11 Command and Exit-Code Log

**Status:** final local-safe validation complete; scientific execution/review blockers remain; `paper_evidence=false`

All commands ran from `<PROJECT_ROOT>` unless the command explicitly changes directory. An exit code
of 1 or 2 is marked expected only where the check is designed to expose a real blocker.

| Check | Exact command | Exit code | Result |
|---|---|---:|---|
| Focused repaired surfaces | `python3 -m pytest -q tests/test_v9_spurious_v2_ingest_decision.py tests/test_v9_spurious_v2_builder.py tests/test_v9_spurious_v2_runbooks.py tests/test_remaining_kaggle_runbooks.py tests/test_claim_validation.py tests/test_claim_language_guard_cli.py tests/test_v2_certification_power.py tests/test_v7_spurious_control_integration.py tests/test_v7_prompt_ablations.py tests/test_v7_mechanism_probes.py tests/test_v3_edit_detectability.py tests/test_parse.py tests/test_v1_1_reporting_outputs.py tests/test_v8_upgrade.py tests/test_v11_human_review_packet.py tests/test_v11_supported_analysis.py tests/test_v11_full_ceiling_audit.py tests/test_anytime_cs_validity.py tests/test_kaggle_bundle.py tests/test_open_vlm_import_safety.py` | 0 | 170 passed in 18.70 s. |
| Full suite | `python3 -m pytest -q` | 0 | 747 passed in 31.81 s. |
| Ruff | `python3 -m ruff check --no-cache certvic scripts tests` | 0 | All checks passed. |
| V11 report contract | `python3 -m pytest -q tests/test_v11_full_ceiling_audit.py` | 0 | 10 passed. |
| T4x2 notebook contract | `python3 scripts/validate_t4x2_notebooks.py --out reports/v11_full_ceiling_audit/notebook_static_validation.json` | 0 | 6/6 notebooks passed CPU-static validation; no notebook was executed. |
| Import safety | `python3 -m pytest -q tests/test_v9_spurious_v2_ingest_decision.py tests/test_open_vlm_import_safety.py` | 0 | 28 passed in 3.31 s. |
| Claim guard | `python3 -m certvic.validation.claim_language_guard --root README.md docs paper reports/v11_full_ceiling_audit --out reports/v11_full_ceiling_audit/claim_guard_v11.md` | 0 | Passed with 0 findings. |
| Privacy audit | `python3 -m certvic.security.release_privacy_audit --root . --out reports/v11_full_ceiling_audit/privacy_audit_v11.md --json-out reports/v11_full_ceiling_audit/privacy_audit_v11.json` | 0 | Passed with 0 text-tree findings. The deprecated session2 ZIP remains separately classified non-release because its member contains 182 private-path occurrences. |
| Evidence ledger | `python3 -m pytest -q tests/test_v11_full_ceiling_audit.py -k evidence` | 0 | 3 passed, 7 deselected; 23 entries, 0 paper-eligible and 0 human-reviewed. |
| Package integrity | `python3 -m pytest -q tests/test_kaggle_bundle.py tests/test_v9_spurious_v2_builder.py tests/test_v9_spurious_v2_runbooks.py tests/test_v11_human_review_packet.py` | 0 | 22 passed in 2.76 s. |
| Main bundle security | `python3 -m certvic.security.audit_kaggle_bundle --bundle dist/certvic_kaggle_main200_bundle.zip --out reports/v11_full_ceiling_audit/main_bundle_security_v11.md --json-out reports/v11_full_ceiling_audit/main_bundle_security_v11.json --strict` | 0 | Passed with 0 findings. |
| Paper compile pass 1 | `cd paper && pdflatex -interaction=nonstopmode -halt-on-error main_v11.tex` | 0 | Compiled. |
| Paper compile pass 2 | `cd paper && pdflatex -interaction=nonstopmode -halt-on-error main_v11.tex` | 0 | Compiled to 3 pages, 196,068 bytes; no LaTeX warning, undefined-reference, overfull, or underfull finding. |
| Paper visual QA | `pdftoppm -png -r 150 paper/main_v11.pdf /tmp/certvic_v11_page` | 0 | All 3 rendered pages inspected; no clipping, overlap, or unreadable content. |
| Bibliography presence | `test -f paper/main_v11.bib` | 1 (expected blocker) | No bibliography exists; submission readiness remains blocked. |
| Citation command presence | `rg -n "\\\\cite|\\\\bibliography|\\\\addbibresource" paper/main_v11.tex` | 1 (expected blocker) | No citation/bibliography command exists. |
| Anonymized text scan | `rg -ni "saket|maganti|/U[s]ers/|Projects/certVIC|saketmaganti" paper/main_v11.tex /tmp/certvic_main_v11.txt` | 1 (expected no-match) | No identity or private-path finding. |
| PDF metadata | `pdfinfo paper/main_v11.pdf` | 0 | Author, title, subject, and keywords are blank; pages=3. |
| Human packet template QA | `python3 scripts/validate_v11_human_review.py --packet-dir reports/v11_full_ceiling_audit/human_review_packet --allow-blank` | 0 | Structurally valid, blank, `HUMAN_REVIEW_PENDING`; no agreement computed. |
| Human completion gate | `python3 scripts/validate_v11_human_review.py --packet-dir reports/v11_full_ceiling_audit/human_review_packet` | 2 (expected blocker) | Fails closed because both rater sheets are blank. |
| Release audit | `python3 scripts/audit_release_candidate.py --no-fail` | 0 | Audit executed: `release_ready=false`, 2 blockers, 1,566 cannot-release paths, 30 release-safe paths. |

## Deterministic artifact locks

- Retrospective V2 private ZIP: `61102740bb1ad76d0315b65839c3a73ad502fd204b77b1634a5003913e29d277`; two consecutive rebuilds matched.
- V2 task JSONL: `58694872601c34bfc787c62f09cfe539949bc2caf9cc0f244ba87e59804c7f64`.
- Main code ZIP: `3e311fcb3f16ab6fdad839e2e340965bf5d65dca96938ef5a206b77d727b8447`; two consecutive rebuilds matched.
- Main code manifest: `4c930e2abff1a40ab6557e087088386d74f122c49e507d043e57216fef600ad7`.
- Blinded reviewer ZIP: `d6e777d035fa806d0b4ffb42cd6c140e08c1187a571770ba87b70c629c3f044f`.
- V11 paper/delivered PDF: `d9a01c930c892059268d119f0d296b8ff1a5d924b42c2799631866e9213fa76b`; both copies match.

Expected blocker exits above are evidence, not test failures. No GPU/provider job, paid API, model
download, human judgment, or Main-500 execution occurred.
