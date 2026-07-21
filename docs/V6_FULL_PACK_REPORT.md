# V6 Full Pack Report

V6 exists because V1-V5 made the project runnable, but the paper still risked
looking like another edited-image VLM benchmark. V6 redirects CertVIC toward
certified, confound-controlled measurement of visual decision updates.

Strategic changes:
- paper identity rewritten around visual decision updates
- item-validity certification made load-bearing
- detectability-first tiny-pilot gate added
- validity-gated scoring and naive-vs-gated reports added
- mechanism and intervention diagnostics added as exploratory support
- open-only scope made explicit
- command execution staged so wholesale dry-run to GPU to VLM is blocked
- final stop condition says after V6, run; do not build V7

Modules added:
- `certvic.validity.load_bearing`
- `certvic.validity.filter_scores`
- `certvic.reporting.validity_shift_report`
- `certvic.reporting.naive_vs_validity_gated`
- `certvic.validation.detectability_gate`
- `certvic.pipeline.tiny_pilot_go_no_go`
- `certvic.dashboard.tiny_pilot_decision`
- `certvic.mechanisms.diagnostics`
- `certvic.mechanisms.intervention_analysis`
- `certvic.edit.family_risk`
- `certvic.review.cvpr_bar_checker`
- `certvic.validation.directional_language_guard`
- `certvic.review.v6_attack_harness`
- `certvic.v6.final_directional_audit`
- `certvic.v6.stop_condition_audit`

Tests added:
- `tests/test_v6_directional_pack.py`

Verification run:
- `python3 -m pytest -q`: 480 passed
- `python3 -m certvic.v6.final_directional_audit --out docs/V6_FINAL_DIRECTIONAL_AUDIT.md --json-out data/results/v6_final_directional_audit.json`: passed
- `python3 -m certvic.validation.directional_language_guard --root paper docs/V6_FULL_PACK_REPORT.md --out docs/V6_DIRECTIONAL_LANGUAGE_GUARD_REPORT.md`: passed

Final status:
No evidence claims. Empirical results remain `[RESULT REQUIRED]`.

Exact next command:
`ADE20K_ROOT=<ADE20K_ROOT> commands/tiny_pilot/02_dry_run_only.sh`

After V6, run; do not build V7.
