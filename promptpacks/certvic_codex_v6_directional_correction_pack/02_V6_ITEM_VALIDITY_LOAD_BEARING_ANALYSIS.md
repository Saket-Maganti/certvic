# CertVIC V6 Prompt — Item Validity Must Be Load-Bearing

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

Build analysis showing whether item-validity certification changes conclusions.

Create:
- `certvic/validity/load_bearing.py`
- `certvic/reporting/validity_shift_report.py`

CLI:
`python3 -m certvic.reporting.validity_shift_report --scores <pair_scores.jsonl> --certificates <item_certificates.jsonl> --out-dir data/results/validity_shift`

The report must compare:
- naive all-item gap
- gap after quality gates
- gap after detectability gate
- gap after human realism/single-factor gate
- gap after answerability gate
- final certificate-eligible gap

Outputs:
- `validity_shift_summary.json`
- `validity_shift_table.csv`
- `validity_shift_report.md`
- optional plot spec JSON, no plotting heavy deps required

Rules:
- if inputs are mock/smoke/simulated, mark NON_EVIDENCE_ANALYSIS_ONLY
- no certified claims unless claim gates pass
- if validity gating changes the measured gap materially, flag "certificate_is_load_bearing"
- if validity gating changes nothing, flag "certificate_not_yet_load_bearing"

Tests:
- rejected items alter naive gap in fixture
- non-evidence inputs cannot produce paper claims
- missing certificate blocks final eligible gap
- deterministic outputs

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
