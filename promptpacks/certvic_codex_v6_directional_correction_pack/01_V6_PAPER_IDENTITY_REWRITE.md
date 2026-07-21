# CertVIC V6 Prompt — Paper Identity Rewrite

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

Rewrite the paper identity around the new direction.

Inspect current `paper/` and `docs/` first.

Create or update:
- `paper/sections/00_title_and_thesis.tex` or equivalent
- `paper/sections/01_introduction.tex`
- `paper/sections/02_method_overview.tex`
- `docs/V6_PAPER_IDENTITY_REWRITE_REPORT.md`

New required identity:
- not a benchmark
- not a dataset paper
- not generic robustness
- certified, confound-controlled decision-update evaluation

Required language:
- "visual decision update"
- "intervention-consistency gap"
- "item-validity certificate"
- "confound-controlled"
- "edit detectability"
- "anytime-valid certification"

Must add forbidden-claim comments:
- no causal-understanding claims
- no all-VLM claims
- no frontier-model claims unless actually run
- no deployment-safety claims
- no fake results

Add an audit:
- `certvic/paper/identity_audit.py`

CLI:
`python3 -m certvic.paper.identity_audit --paper-dir paper --out docs/V6_PAPER_IDENTITY_AUDIT.md`

Tests:
- paper identity contains new framing
- "benchmark" is not the lead identity
- forbidden claims absent
- result placeholders still intact

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
