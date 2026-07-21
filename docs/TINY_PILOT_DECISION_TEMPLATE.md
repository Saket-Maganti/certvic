# Tiny Pilot Decision Template

This is the report shape for `python3 -m certvic.dashboard.tiny_pilot_decision`.

Required fields:
- dry-run status
- edit generation status
- quality pass rate
- detectability AUC
- visual review count
- answerability review count
- item certificate pass rate
- whether VLM eval may begin
- top blockers

Decision rules:
- AUC <= 0.60 and quality pass: GO if review/certificates also pass
- 0.60 < AUC <= 0.70: CONDITIONAL, improve edits before VLM
- AUC > 0.70: NO-GO for VLM inference
- AUC >= 0.80: artifact-confounded, must not become evidence
- missing detectability: NO-GO

VLM inference should not begin until detectability and visual quality pass.
