
# CertVIC Runtime Validation

Final local validation date: 2026-07-14. Verdict: `PARTIALLY_READY_WITH_BLOCKERS`;
`paper_evidence=false`.

| Gate | Command or assertion | Result |
| --- | --- | --- |
| Reproduced baseline | `python3 -m pytest -q` before privacy repair | 758 passed, 6 failed; all six were the new prompt pack's private host path |
| Legacy focused baseline | `python3 -m pytest -q tests/test_cvpr_pre_execution.py` | 17 passed; confirmed it did not exercise named runtime behaviors |
| Repaired focused paths | runtime-hardening plus legacy CVPR tests | 27 passed |
| Full suite | `python3 -m pytest -q` | 774 passed in 36.86 s |
| Lint | `python3 -m ruff check --no-cache certvic scripts tests` | pass, all checks |
| Byte compilation | `python3 -m compileall -q certvic scripts` | pass |
| Notebook static | JSON parse, clean cells, notebook contract tests | 16/16 pass |
| Synthetic runtime | generation, selection, snapshot, code extraction, batch/OOM, resume quarantine, review, atomic import, analysis | pass |
| Claim guard | README/docs/paper/reports scan | pass, 0 findings |
| Privacy guard | repository release privacy audit | pass, 0 findings |
| Paper | `pdflatex -interaction=nonstopmode -halt-on-error main.tex` | pass, 3-page PDF |
| Release determinism | two runtime-candidate builds | identical SHA-256 (recorded in candidate archive checksum) |
| Existing release audit | `python3 scripts/audit_release_candidate.py --no-fail` | privacy pass; release-ready false with two declared historical/license blockers |
| Builder ownership | rerun legacy pre-execution builder | runtime-owned surfaces preserved |

Evidence assertions: zero structured `human_reviewed=true` records; all runtime artifacts retain
`paper_evidence=false`; Main execution remains false; V2-30 remains retrospective sensitivity only;
no GPU/provider result or human label was created; required generation no longer selects a disabled
engine; worker flags affect tested behavior; stale shards are quarantined before regeneration.

Level 3 (Kaggle environment plus real two-item adapter smoke) and Level 4 (scientific execution) are
`NOT_RUN_EXTERNAL`. They cannot be converted into local passes.
