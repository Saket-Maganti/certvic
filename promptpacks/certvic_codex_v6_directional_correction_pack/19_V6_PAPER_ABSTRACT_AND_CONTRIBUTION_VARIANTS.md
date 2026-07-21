# CertVIC V6 Prompt — Paper Abstract and Contribution Variants

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

Generate safe, result-free paper wording variants for the new identity.

Create:
- `docs/paper_variants/V6_ABSTRACT_VARIANTS.md`
- `docs/paper_variants/V6_CONTRIBUTIONS.md`
- `docs/paper_variants/V6_TITLE_OPTIONS.md`

Rules:
- no fake numbers
- no fake citations
- every empirical sentence must use [RESULT REQUIRED]
- include at least 3 variants:
  1. method/protocol-heavy
  2. construct-validity-heavy
  3. empirical-finding-heavy placeholder

Tests:
- variants contain no unsupported numbers
- forbidden claims absent
- title options avoid benchmark-first framing

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
