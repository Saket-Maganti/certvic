# CertVIC V6 Prompt — Detectability-First Pilot Gate

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

Build a first-class tiny-pilot gate around edit detectability.

Create:
- `certvic/validation/detectability_gate.py`
- `certvic/pipeline/tiny_pilot_go_no_go.py`

CLI:
`python3 -m certvic.pipeline.tiny_pilot_go_no_go --detectability data/results/tiny_real_pilot/edit_detectability --quality data/results/tiny_real_pilot/quality_report.json --out docs/TINY_PILOT_GO_NO_GO.md --json-out data/results/tiny_pilot_go_no_go.json`

Gate logic:
- AUC <= 0.60: GO, if quality also passes
- 0.60 < AUC <= 0.70: CONDITIONAL / improve edits before VLM
- AUC > 0.70: NO-GO for VLM inference
- AUC >= 0.80: artifact-confounded, must not become evidence
- missing detectability: NO-GO
- insufficient n: CONDITIONAL, not evidence

Docs must say:
"VLM inference should not begin until detectability and visual quality pass."

Tests:
- AUC 0.55 -> GO
- AUC 0.65 -> CONDITIONAL
- AUC 0.90 -> NO-GO
- missing file -> NO-GO
- quality fail overrides GO

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
