# CertVIC V5 Prompt — Human Answerability Validation

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Add explicit human answerability validation.

Create:
- `certvic/validation/answerability.py`
- `certvic/data/apply_answerability_review.py`

CLI:
`python3 -m certvic.validation.answerability --tasks <tasks.jsonl> --out data/annotations/answerability_sheet.csv`
`python3 -m certvic.data.apply_answerability_review --tasks <tasks.jsonl> --ratings <answerability_ratings.csv> --out <reviewed_tasks.jsonl>`

Fields:
- original_answerable
- edited_answerable
- expected_change_unambiguous
- human_expected_original
- human_expected_edited
- agreement_with_manifest
- notes

Tests:
- answerability sheet hides model outputs
- disagreement blocks evidence candidate
- reviewed tasks preserve non-evidence until model run

Docs:
- `docs/V5_HUMAN_ANSWERABILITY_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
