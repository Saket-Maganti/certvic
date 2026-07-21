# CertVIC V6 Prompt — Open-Only Defense Package

Read `00_V6_MASTER_CONTEXT.md` first.

You are correcting project direction, not building generic infrastructure.

Hard constraints:
- Do not initialize git.
- Do not commit or tag.
- Do not use paid APIs.
- Do not use paid cloud.
- Do not download data or weights.
- Do not run GPU jobs.
- Do not run VLM inference.
- Do not fabricate results.
- Do not fabricate citations.
- Do not insert fake paper numbers.
- Do not make evidence claims from mock/smoke/simulated/planned/unreviewed/simple-edit-only artifacts.
- Keep tests local and CPU-only.
- Heavy dependencies must be optional/import-safe.

Build paper/docs support for the no-paid-frontier-model policy.

Create:
- `docs/OPEN_ONLY_EVALUATION_RATIONALE.md`
- `paper/sections/open_only_scope.tex`
- `certvic/paper/open_only_audit.py`

Required defense:
- core pipeline is zero-cost and reproducible
- claims are scoped to open VLMs actually run
- no frontier/closed model generalization
- protocol is model-agnostic
- frontier comparison is optional/non-core only if user later chooses it
- absence of frontier models is a limitation, not hidden

CLI:
`python3 -m certvic.paper.open_only_audit --paper-dir paper --out docs/V6_OPEN_ONLY_AUDIT.md`

Tests:
- no GPT/Gemini/Claude claims unless marked optional future/non-core
- open-only limitation present
- model-agnostic protocol statement present

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
