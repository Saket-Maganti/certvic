# Security / Privacy / Path Audit

Generated: 2026-07-09

Root: `.`
Status: **FAIL** (140 finding(s))

Static text inspection only; no network, no evidence claims.

## Summary

| Check | Findings | OK |
| --- | --- | --- |
| Private absolute paths / dataset roots | 140 | False |
| Secrets / credentials | 0 | True |
| Committed .env files | 0 | True |
| Paid endpoints | 0 | True |
| Release pixels | 0 | True |
| Release-dir private paths (text) | 0 | True |
| Release-dir secrets (text) | 0 | True |

## Private paths

| File | Line | Kind | Match |
| --- | --- | --- | --- |
| `AUTORUN_LEDGER_V2.jsonl` | 1 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 1 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 2 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 2 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 3 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 3 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 4 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 4 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 5 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 5 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 6 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 6 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 7 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 7 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 8 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 8 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 9 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 9 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 10 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 10 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 11 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 11 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 12 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 12 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 13 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 13 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 14 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 14 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 15 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 15 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 16 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 16 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 17 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 17 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 18 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 18 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 19 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 19 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 20 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 20 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 21 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 21 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 22 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 22 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 23 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 23 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 24 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 24 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 25 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 25 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 26 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 26 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 27 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 27 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 28 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 28 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 29 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 29 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 30 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 30 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 31 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 31 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_LEDGER_V2.jsonl` | 32 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `AUTORUN_LEDGER_V2.jsonl` | 32 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_STATUS.md` | 3 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC/certvic_v9_mega_issue_resolution_prompt_pack`` |
| `AUTORUN_STATUS.md` | 3 | home_dir_path | `/Users/saketmaganti` |
| `AUTORUN_STATUS_V2.md` | 5 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC/certvic_v10_pre_execution_god_tier_prompt_pack`` |
| `AUTORUN_STATUS_V2.md` | 5 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report.md` | 5 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC/certvic_v9_mega_issue_resolution_prompt_pack`.` |
| `certVIC_report.md` | 5 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report.md` | 9 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC/certvic_v9_mega_issue_resolution_prompt_pack`` |
| `certVIC_report.md` | 9 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report.md` | 10 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report.md` | 10 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 5 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 5 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 11 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC/certvic_v10_pre_execution_god_tier_prompt_pack`` |
| `certVIC_report_v2.md` | 11 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 12 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 12 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 59 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 59 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 74 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 74 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 89 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 89 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 104 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 104 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 119 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 119 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 134 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 134 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 149 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 149 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 164 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 164 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 179 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 179 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 194 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 194 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 209 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 209 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 224 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 224 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 239 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 239 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 254 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 254 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 269 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 269 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 284 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 284 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 299 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 299 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 314 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 314 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 329 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 329 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 344 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 344 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 359 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 359 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 374 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 374 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 389 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 389 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 404 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 404 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 419 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 419 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 434 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 434 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 449 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 449 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 464 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 464 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 479 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 479 | home_dir_path | `/Users/saketmaganti` |
| `certVIC_report_v2.md` | 494 | private_absolute_path | `/Users/saketmaganti/Projects/certVIC`` |
| `certVIC_report_v2.md` | 494 | home_dir_path | `/Users/saketmaganti` |
