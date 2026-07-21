# CertVIC Codex V2 — Single Master Prompt

Use this only if you want Codex to attempt a very large V2 build in one session. Prefer the numbered V2 prompts for cleaner work.

You are working inside:

`/Users/saketmaganti/Projects/certVIC`

Do not initialize git. Do not create commits/tags. Do not use paid APIs. Do not use paid cloud. Do not download large datasets automatically. Do not run VLM inference in tests. Do not fabricate evidence claims. Keep paper result sections as RESULT REQUIRED until real eligible outputs exist.

The project has passed V1 through V1.5, with 110 tests passing. Upgrade to V2.

Build:

1. V2 baseline audit.
2. Human/visual review workflow.
3. ADE20K label policy and task-family eligibility.
4. Modular edit engine and stronger quality gates.
5. Open-local VLM inference readiness/preflight.
6. Baselines and ablations.
7. Certification, power planning, and optional-stopping diagnostics.
8. V2 results reporting, tables, and figures.
9. Failure taxonomy and local gallery.
10. Recipe-first artifact release.
11. Major paper scaffold upgrade.
12. End-to-end tiny real pilot orchestrator.
13. Tiny eval + scoring path.
14. Main 200-item pilot runbook and gates.
15. Full V2 system audit.

For every subsystem:
- add tests
- add docs
- add CLI commands
- keep heavy imports optional
- preserve zero-cost policy
- preserve non-evidence statuses
- update claim gates
- run `python3 -m pytest -q`

Create final docs:
- `docs/V2_FULL_SYSTEM_AUDIT_REPORT.md`
- `docs/V2_COMMAND_INDEX.md`
- `docs/V2_NEXT_ACTIONS.md`

At the end, report files changed, tests run, commands added, audit status, and blockers before evidence claims.
