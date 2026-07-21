# CertVIC V6 Prompt — Post-V6 Audit Prompt

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

Create a compact prompt for Claude to audit V6 before runs.

Create:
- `docs/audit_prompts/V6_POST_DIRECTIONAL_AUDIT_PROMPT.md`

It must ask Claude to check:
- did V6 truly pivot away from benchmark framing?
- is item-validity load-bearing now?
- does detectability gate block VLM runs?
- are commands staged safely?
- is mechanism infrastructure enough?
- are paper claims still blocked?
- is the next action definitely runs?

Tests:
- prompt exists
- includes no fake numbers
- includes exact expected outputs

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
