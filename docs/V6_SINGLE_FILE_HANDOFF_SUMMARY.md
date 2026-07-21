# V6 Single-File Handoff Summary

Project identity: CertVIC is certified, confound-controlled measurement of
visual decision updates in VLMs.

V1-V5 status: infrastructure, result-free paper scaffolding, command planning,
claim guards, item certificates, and destructive-audit fixes exist. The project
still has no real ADE20K/diffusion/VLM evidence.

V6 correction: the paper is not a benchmark, not a dataset paper, and not a
generic robustness claim. The load-bearing object is the item-validity
certificate, and the existential pilot number is edit detectability AUC.

What remains unproven:
- real edited images are photorealistic enough
- edit detectability is low enough
- humans agree on answerability and single-factor validity
- open VLMs produce certificate-eligible outputs
- the validity-gated gap is meaningful and certifiable

Next commands:
1. `python3 -m pytest -q`
2. `python3 -m certvic.v6.final_directional_audit --out docs/V6_FINAL_DIRECTIONAL_AUDIT.md --json-out data/results/v6_final_directional_audit.json`
3. `ADE20K_ROOT=<ADE20K_ROOT> commands/tiny_pilot/02_dry_run_only.sh`

Current verification:
- `python3 -m pytest -q`: 480 passed
- V6 final directional audit: passed
- V6 stop-condition audit: passed

Go/no-go thresholds:
- AUC <= 0.60: GO if quality and certificates pass
- 0.60 < AUC <= 0.70: CONDITIONAL
- AUC > 0.70: NO-GO for VLM inference
- AUC >= 0.80: artifact-confounded

What kills the paper:
- high edit detectability
- low photorealism or ambiguous answer keys
- certificate filtering removes most items
- no validity-gated gap after real open-model runs
- no proof/citation bridge before submission

What makes it CVPR-strong:
- low edit detectability
- high human agreement and certificate pass rate
- validity-gated gap differs from naive gap in an interpretable way
- certified lower bound survives controls, parsing checks, and open-model scope

No evidence claims are made. Results remain `[RESULT REQUIRED]`.
