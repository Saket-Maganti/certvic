# CertVIC V5 Prompt — Conference Submission Package Planner

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Plan the final CVPR submission package.

Create:
- `certvic/submission/package_plan.py`
- `docs/CVPR_SUBMISSION_PACKAGE_PLAN.md`

CLI:
`python3 -m certvic.submission.package_plan --paper-dir paper --out-dir docs/submission_package_plan`

Include:
- main paper
- supplement
- figures
- tables
- checklist
- artifact README
- data card
- model/eval cards
- claim ledger
- reproduction docs
- release package
- anonymization checklist

Tests:
- required package components listed
- missing result placeholders flagged
- anonymization reminders present

Docs:
- `docs/V5_SUBMISSION_PACKAGE_PLANNER_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
