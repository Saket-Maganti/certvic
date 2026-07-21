# CertVIC V6 Prompt — Main Figure and Table Redesign

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

Redesign the paper's core visual story.

Create:
- `paper/figure_manifest_v6.yaml`
- `paper/table_manifest_v6.yaml`
- `certvic/paper/v6_visual_story_audit.py`
- `docs/V6_MAIN_FIGURE_TABLE_PLAN.md`

Required main figure:
Detectability-vs-certified-gap figure:
- x-axis: edit detectability AUC
- y-axis: certified decision-update gap lower bound or descriptive gap if uncertified
- chance line at 0.5
- danger region for AUC >= 0.8
- point per model/family/task family
- paired qualitative triptychs nearby

Required main table:
Per model/family:
- n valid
- naive gap
- validity-gated gap
- certified lower bound
- detectability AUC
- control spurious-flip rate
- parse failure rate
- human IAA
- certificate pass rate

Tests:
- manifests contain required figure/table slots
- every slot maps to source artifact
- no fake numbers
- placeholders are result-required only

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
