# V2 Full System Audit Report

Generated: 2026-06-22

Overall status: **PASS** (13/13 checks passed)

Verifies V1-V1.5 + V2 handoffs, configs, runbooks, command imports, zero-cost,
claim discipline, and no fake paper results. No inference, no downloads.

| Check | Status | Detail |
| --- | --- | --- |
| `v1_handoffs_exist` | pass | expected=6 |
| `v2_handoffs_exist` | pass | expected=14 |
| `v2_configs_exist` | pass | expected=5 |
| `runbooks_exist` | pass | expected=4 |
| `v2_commands_import` | pass | checked=26 |
| `no_paid_provider_enabled` | pass | ok |
| `zero_cost_policy_exists` | pass | ok |
| `claim_policy_exists` | pass | ok |
| `release_audit_available` | pass | ok |
| `gate_checks_available` | pass | ok |
| `no_forbidden_claims` | pass | ok |
| `no_fake_paper_results` | pass | results_placeholder=True |
| `baseline_audit_passes` | pass | n_passed=9; n_checks=9 |

See docs/V2_COMMAND_INDEX.md and docs/V2_NEXT_ACTIONS.md.
