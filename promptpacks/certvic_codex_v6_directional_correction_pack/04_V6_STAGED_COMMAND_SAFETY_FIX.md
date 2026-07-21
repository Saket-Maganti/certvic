# CertVIC V6 Prompt — Staged Command Safety Fix

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

Fix command bundle behavior so `commands.sh` cannot encourage dry-run→execute→GPU→VLM in one blind run.

Inspect:
- `certvic/commands/command_manifest.py`
- generated command bundles
- docs stop/runbook files

Add:
- stage-specific scripts:
  - `commands/tiny_pilot/01_cpu_readiness.sh`
  - `commands/tiny_pilot/02_dry_run_only.sh`
  - `commands/tiny_pilot/03_generate_edits_only.sh`
  - `commands/tiny_pilot/04_detectability_gate_only.sh`
  - `commands/tiny_pilot/05_vlm_eval_only_AFTER_GATES.sh`
- or generator support to create these scripts.

Modify generated `commands.sh`:
- it should print instructions and exit, or require `CERTVIC_RUN_ALL_DANGEROUS_STAGES=1`
- it must not run GPU/VLM stages by default
- it must warn not to run wholesale

Add CLI option:
`--staged-only`

Tests:
- generated commands.sh does not run unsafe stages by default
- staged scripts exist
- unsafe scripts contain explicit gate comments
- no tests execute GPU/VLM

Docs:
- update `docs/V6_STAGED_COMMAND_SAFETY_REPORT.md`
- update stop-doc and command index

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
