# V6 Final Go/No-Go

Current status before empirical execution: GO to run the ADE20K dry-run after
tests and V6 final audit pass.

Verification:
- `python3 -m pytest -q`: 480 passed
- V6 final directional audit: passed
- V6 stop-condition audit: passed

No evidence claims are made. All empirical findings remain `[RESULT REQUIRED]`.

The number that decides whether the paper is real is tiny-pilot edit
detectability AUC:
- AUC <= 0.60: GO if quality and certificates pass
- 0.60 < AUC <= 0.70: CONDITIONAL
- AUC > 0.70: NO-GO for VLM inference
- AUC >= 0.80: artifact-confounded

Next exact command after verification:
`ADE20K_ROOT=<ADE20K_ROOT> commands/tiny_pilot/02_dry_run_only.sh`
