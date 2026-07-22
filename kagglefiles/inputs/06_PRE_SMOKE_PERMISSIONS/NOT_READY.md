# NOT READY: PRE_SMOKE_PERMISSIONS

- Missing role: `PRE_SMOKE_PERMISSIONS`
- Why missing: Permissions are derived from genuine upstream identities and cannot be precomputed.
- Prerequisite stage: `Verified 00A, all three 00B returns, and real smoke bundle`
- Exact builder/notebook/command: `python3 -m certvic.cvpr.pre_smoke_packager --config local_inputs/pre_smoke_inputs.json`
- Expected filename: `certvic_pre_smoke_permissions.zip`
- Expected size: under 1 MB
- Completed-file destination: `kagglefiles/inputs/06_PRE_SMOKE_PERMISSIONS/`
- Evidence boundary: `paper_evidence=false`; do not fabricate the missing bytes.
