# V5 Stop Infrastructure — Begin Empirical Runs

V5 completes the result-free CVPR-readiness layer. Stop adding general
infrastructure unless a real run exposes a concrete missing gate.

## Audit status (2026-06-22)

A full destructive audit ran against V1–V5 (`docs/V5_DESTRUCTIVE_AUDIT_REPORT.md`).
Result: **conditional pass; empirical runs may begin.** Four safety-gate bugs were
found and fixed (see `docs/V5_AUDIT_FIXES_REPORT.md`): a certification-policy
global-allowlist leak, a paper-number-guard em-dash/placeholder bypass, a missing
edit-detectability block in the item certificate, and a release-privacy text-scan
blind spot. Tests: **471 passed** (was 459; +12 regressions). No gate was weakened.

The stop condition is **reaffirmed**: the remaining blockers are empirical, not
structural. Do not keep building general infrastructure.

## Exact Next Commands — run STAGED and GATED (do not run the bundle wholesale)

```bash
# 1. Confirm readiness (CPU-only, no GPU/VLM):
python3 -m certvic.v5.cvpr_ready_except_results_audit --out docs/V5_CVPR_READY_EXCEPT_RESULTS_AUDIT.md --json-out data/results/v5_cvpr_ready_except_results_audit.json

# 2. Generate the tiny-pilot bundle (writes files; executes nothing).
#    Pass your real local ADE20K root so the dry-run can inspect it:
python3 -m certvic.commands.generate_real_run_commands \
  --stage tiny_pilot --out-dir commands/tiny_pilot \
  --ade20k-root <YOUR_LOCAL_ADE20K_ROOT>
```

**Do NOT run `bash commands/tiny_pilot/commands.sh` as one shot.** That script
chains dry-run → execute → GPU edit generation → VLM inference. Run it
command-by-command, inspecting outputs between each:

1. `[v3_gate]` — CPU audit, must be green.
2. `[study_plan]` — plan only.
3. `[tiny_pilot_dry_run]` — `--dry-run`; confirm it passes and the ADE20K root reads correctly.
4. **STOP.** Do not proceed to `[tiny_pilot_execute]`, `[gpu_edit_generation]`, or
   any `--evidence-run` VLM command until: the dry-run is clean, generated edits
   pass quality gates, the **edit-detectability probe is acceptable**, and items
   are **human-reviewed** (reviewed status + passing item validity certificates).

Per-command guards remain in force regardless: `run_eval --evidence-run` hard-blocks
non-open-local providers and unreviewed tasks; `--dry-run` writes nothing; paid and
mock providers are rejected; `max_items` is required.

## Remaining empirical blockers

Local ADE20K root, free GPU sessions, photorealistic edits that survive the
detectability probe, human review with acceptable IAA, answerability validation,
item validity certificates, open-local VLM predictions, scoring, an eligible
anytime-valid certified lower bound, clean cluster diagnostics, result lock, and
final paper injection — plus citations, a formal theory/proof section, and
qualitative figures (see paper weaknesses in the audit report).
