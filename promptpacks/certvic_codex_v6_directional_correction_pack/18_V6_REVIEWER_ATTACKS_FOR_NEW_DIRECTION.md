# CertVIC V6 Prompt — Reviewer Attacks for New Direction

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

Update reviewer attack harness around the new direction.

Create/update:
- `certvic/review/v6_attack_harness.py`
- `docs/V6_REVIEWER_ATTACKS_NEW_DIRECTION.md`

Attacks:
- this is just another benchmark
- edits are artifacts
- item certificate is over-engineered
- confidence sequences are unnecessary
- open-only models are weak
- no mechanism
- small scale
- human validation too subjective
- detectability probe too weak
- answer keys ambiguous

CLI:
`python3 -m certvic.review.v6_attack_harness --out docs/V6_REVIEWER_ATTACKS_NEW_DIRECTION.md --json-out data/results/v6_reviewer_attacks.json`

Tests:
- attack list complete
- each attack has required empirical defense
- missing defense flags blocker

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
