# CertVIC V6 Prompt — Run-After-This Checklist

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

Create the exact post-V6 execution checklist.

Create:
- `docs/RUN_AFTER_V6_CHECKLIST.md`

Must include:
1. verify tests/audits
2. generate staged tiny-pilot commands
3. run CPU readiness
4. run ADE20K dry-run
5. inspect manifest/masks/tasks
6. generate max 20 diffusion edits
7. inspect images by eye
8. run detectability
9. run tiny-pilot go/no-go
10. if GO, run human review
11. generate item certificates
12. only then run first VLM eval
13. score and inspect
14. decide scale/no-scale

Include exact commands with placeholders.

No command may run full pipeline wholesale.

Tests:
- checklist exists
- contains detectability before VLM
- warns against commands.sh wholesale

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
