# CertVIC V6 Prompt — Intervention That Moves the Gap

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

Prepare analysis for one intervention that may reduce or increase the decision-update gap.

Create:
- `certvic/mechanisms/intervention_analysis.py`

Possible interventions:
- localize-then-answer prompt
- changed-region description prompt
- crop-only diagnostic
- multiple-choice response format
- stricter instruction to ignore original answer inertia

CLI:
`python3 -m certvic.mechanisms.intervention_analysis --baseline <baseline_scores.jsonl> --intervention <intervention_scores.jsonl> --out-dir data/results/intervention_analysis`

Outputs:
- gap_delta
- parse_delta
- consistency_delta
- caution flags
- exploratory-only language unless preregistered

Tests:
- reduced gap detected
- increased parse failures warn
- non-evidence inputs marked exploratory
- no certified claims from unregistered intervention

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
