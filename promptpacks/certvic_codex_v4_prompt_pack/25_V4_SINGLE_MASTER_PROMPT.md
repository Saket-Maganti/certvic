# CertVIC Codex V4 — Single Master Prompt

Use this only if you want Claude/Codex to attempt all V4 infrastructure in one long session.

You are working in:

`/Users/saketmaganti/Projects/certVIC`

Do not initialize git. Do not create commits/tags. Do not use paid APIs/cloud/datasets/annotation. Do not download real datasets or model weights. Do not run GPU jobs. Do not run VLM inference in tests. Do not fabricate results. Do not make evidence claims from synthetic/simulated/pre-run artifacts.

Current state:
- V1–V3 complete
- around 434 tests passing
- V3 final pre-real-run audit passes
- no real empirical evidence yet

Goal:
Build final run-later infrastructure before coding/assistant limits expire. After V4, the user should mostly execute real runs.

Build all V4 systems:
1. Real-run command generator.
2. Kaggle notebook autogenerator.
3. Colab notebook autogenerator.
4. Offline model cache manifests.
5. Dataset fallback adapters.
6. CC0 showcase split tooling.
7. Edit engine parameter sweep planner.
8. Static visual QA review app.
9. Real-run recovery and repair.
10. Prediction merge and deduplication.
11. Multi-model comparison suite.
12. Statistical sensitivity suite.
13. Qualitative figure builder.
14. LaTeX camera-ready infrastructure.
15. Supplement autogenerator.
16. Reproducibility capsule validator.
17. Result freeze and lockfile.
18. Submission checklist and deadline manager.
19. Runbook troubleshooting assistant.
20. Dataset license expansion.
21. Human review QC plus.
22. Realistic paper ablation planner.
23. Final CVPR internal review packet.
24. Final all-system audit.

For every subsystem:
- inspect existing modules first
- preserve backward compatibility
- add tests
- add docs
- add CLI commands
- keep heavy imports lazy
- mark planned/simulated artifacts non-evidence
- do not fake paper claims
- run `python3 -m pytest -q`

Final deliverables:
- `docs/V4_COMMAND_INDEX.md`
- `docs/V4_FINAL_ALL_SYSTEM_AUDIT_REPORT.md`
- `docs/V4_STOP_BUILDING_EXECUTE_RUNS.md`
- final JSON audit under `data/results/`

Final response must include:
- strategic summary
- files changed
- tests run
- commands added
- docs added
- final audit status
- exact next real-run commands
- strict stop condition
