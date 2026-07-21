# CertVIC V6 Prompt — Single-File Handoff Summary

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

Create a one-file human handoff summary.

Create:
- `docs/V6_SINGLE_FILE_HANDOFF_SUMMARY.md`

It should be readable in 5 minutes and include:
- project identity
- V1–V5 status
- destructive audit result
- V6 direction correction
- what remains unproven
- next commands
- go/no-go thresholds
- what kills the paper
- what makes it CVPR-strong

No fake results.
No citations unless real citations exist.

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
