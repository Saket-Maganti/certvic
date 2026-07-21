# CertVIC V5 Prompt — Edit Realism Rubric and Scorecard

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Build a formal edit realism rubric.

Create:
- `certvic/validation/edit_realism_rubric.py`
- `certvic/reporting/edit_realism_scorecard.py`
- `docs/EDIT_REALISM_RUBRIC.md`

Rubric:
- photorealism
- lighting consistency
- boundary artifacts
- shadow consistency
- geometry/plausibility
- single-factor preservation
- target clarity
- required-change clarity

CLI:
`python3 -m certvic.reporting.edit_realism_scorecard --ratings <visual_review_ratings.csv> --out-dir data/results/edit_realism_scorecard`

Tests:
- rubric fields present
- scorecard computes pass/fail
- major artifact blocks item
- uncertain-heavy items flagged

Docs:
- `docs/V5_EDIT_REALISM_SCORECARD_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
