# CertVIC V5 Prompt — Human Rater Training and Calibration

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Build human rater training/calibration infrastructure.

Create:
- `certvic/validation/rater_training.py`
- `certvic/validation/rater_calibration.py`
- `docs/rater_training/`

CLI:
`python3 -m certvic.validation.rater_training --out-dir docs/rater_training`
`python3 -m certvic.validation.rater_calibration --ratings <ratings.csv> --gold <gold.csv> --out-dir data/results/rater_calibration`

Outputs:
- rater guide
- calibration quiz template
- gold-label rubric template
- calibration report
- rater approval status

Tests:
- guide generated
- calibration computes accuracy/agreement
- low-calibration rater flagged
- no paid annotation

Docs:
- `docs/V5_RATER_TRAINING_CALIBRATION_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
