# CertVIC Kaggle Pack Validation

Phase A CPU validation passed without launching a real Kaggle/GPU scientific run.

| Check | Observed result | Exit |
| --- | --- | ---: |
| Pre-edit regression baseline | 857 passed, 1 skipped | 0 |
| Final full pytest suite | 885 passed, 1 skipped | 0 |
| Focused Kaggle execution-pack and bundle tests | 15 passed | 0 |
| Ruff | All checks passed | 0 |
| Python compileall | Passed | 0 |
| Canonical notebook static validation | 20/20 output-free runbooks passed | 0 |
| Synthetic notebook execution proof | 21/21 routes passed; all 20 notebooks covered | 0 |
| Deterministic local ZIP rebuild | 5/5 byte-identical | 0 |
| Claim guard | Passed; zero human-reviewed rows; no prohibited external bytes | 0 |
| Privacy scan | Passed; zero findings | 0 |
| Paper compile | Passed; 3-page PDF | 0 |
| Maximum-ceiling clean release extraction | Passed | 0 |

The synthetic notebook proof used the in-process Python fallback because the repository environment does not include `nbclient`; this is an explicit restricted-environment fallback, not a scientific result. Phase B must repeat the complete CPU workflow from the sealed offline wheelhouse before any real GPU launch. Frozen V1/V2 evidence boundaries remain unchanged, and every generated synthetic artifact retains `paper_evidence=false`.
