# CertVIC V5 Prompt — Preregistration and Analysis Plan Lock

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Harden preregistration so reviewers can see primary endpoints were not chosen after results.

Create:
- `certvic/analysis/preregistration.py`
- `certvic/analysis/analysis_plan_lock.py`

CLI:
`python3 -m certvic.analysis.analysis_plan_lock --config configs/certification_policy.yaml --out docs/ANALYSIS_PLAN_LOCK.md --json-out data/results/analysis_plan_lock.json`

Must include:
- primary estimand Delta
- primary population
- primary model set
- primary item inclusion rules
- primary stopping rule
- alpha
- gap threshold
- parse failure threshold
- control spurious flip threshold
- allowed exploratory analyses
- multiplicity statement
- cluster dependence statement
- frozen-before-results flag

Tests:
- missing primary endpoint fails
- exploratory-only analyses cannot become primary
- fake post-result modification is flagged
- lockfile hash stable

Docs:
- `docs/V5_ANALYSIS_PLAN_LOCK_REPORT.md`
- update `docs/PRE_REGISTRATION.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
