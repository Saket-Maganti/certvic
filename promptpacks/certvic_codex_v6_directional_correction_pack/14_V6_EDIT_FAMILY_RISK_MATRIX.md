# CertVIC V6 Prompt — Edit Family Risk Matrix

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

Build risk matrix for edit families before scaling.

Create:
- `certvic/edit/family_risk.py`
- `docs/EDIT_FAMILY_RISK_MATRIX.md`

Risk dimensions:
- detectability
- photorealism
- answerability
- single-factor validity
- ADE20K label ambiguity
- expected VLM sensitivity
- free-GPU feasibility

CLI:
`python3 -m certvic.edit.family_risk --edit-manifest <generated_edits.jsonl> --detectability <detectability.json> --review <review_summary.json> --out docs/EDIT_FAMILY_RISK_MATRIX.md`

Tests:
- high detectability family flagged
- low review pass family flagged
- missing data is unknown not pass
- risk matrix deterministic

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
