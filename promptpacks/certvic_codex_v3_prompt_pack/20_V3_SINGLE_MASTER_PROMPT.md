# CertVIC Codex V3 — Single Master Prompt

Use this only if you want one very large session to attempt all V3 infrastructure in one go.

You are working in `/Users/saketmaganti/Projects/certVIC`. V1–V2.7 are complete, tests are around 246 passing, pre-run master audit is cleared, and no real empirical evidence exists yet.

## Global constraints

- Work in `/Users/saketmaganti/Projects/certVIC`.
- Do not initialize git, commit, or tag.
- Do not use paid APIs, paid cloud, paid datasets, paid annotation, paid credits, or paid tracking.
- Do not download large datasets or model weights.
- Do not run GPU jobs or VLM inference in tests.
- Do not fabricate results or insert fake paper numbers.
- Keep heavy dependencies optional and import-safe.
- Normal tests must run locally without GPU.
- Simulated/pre-run artifacts must be marked non-evidence and blocked from claims.
- Preserve backward compatibility and run `python3 -m pytest -q`.

## Build all V3 systems

1. Run ledger and provenance graph.
2. Dataset root and storage planner.
3. Kaggle/Colab free-compute packager.
4. Diffusion job queue and resume planner.
5. Edit detectability probe.
6. Cluster-aware certification diagnostics.
7. Human review operations.
8. Model run orchestration matrix.
9. Model output quality and parse triage.
10. Scale planner and free-compute budget simulator.
11. Static local run dashboard.
12. Paper result injection and traceability.
13. Related work and citation scaffold.
14. Rebuttal/reviewer simulation kit.
15. Dockerless reproduction scripts.
16. Security/privacy/path audit.
17. Failure mode playbooks.
18. Main study orchestrator dry run.
19. Final pre-real-run audit.

For each subsystem: inspect existing modules first, preserve compatibility, add tests, docs, and CLI commands, keep heavy imports optional, mark artifacts non-evidence, and run `python3 -m pytest -q`.

Final deliverables:
- `docs/V3_FINAL_PRE_REAL_RUN_AUDIT_REPORT.md`
- `docs/V3_COMMAND_INDEX.md`
- `docs/V3_STOP_BUILDING_START_RUNNING.md`

Final report must include files changed, tests run, commands added, audit status, exact next real ADE20K command, runtime implications, and stop condition.
