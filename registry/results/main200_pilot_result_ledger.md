# CertVIC main_real_200 — Pilot Result Ledger

**PILOT_ONLY** (`evidence_status=HUMAN_REVIEWED_NON_EVIDENCE`, `paper_evidence=False`). Every metric traces to a sha256-locked artifact. Non-canonical reports are excluded by construction; see non_canonical_excluded.

Every number below is recomputed from a sha256-locked artifact by `certvic.v7.result_ledger_audit`; nothing is hand-entered.

| result_id | task_set | metrics | scoring artifact | sha256 (12) |
|---|---|---|---|---|
| `qwen2_5_vl_7b__presence` | presence | a=0.9231 p=0.1758 Δ=0.7473 CS_LB=0.364 cert=True | `data/results/main_real_200/pilot_report/pilot_result.json` | `b8f103f3ac34` |
| `qwen2_5_vl_7b__absent_control` | absent_control | absent=60/60 present=50/60 | `data/results/main_real_200/pilot_report/absent_object_control.json` | `2c4d088ab4b2` |
| `internvl_8b__presence` | presence | a=0.9231 p=0.0989 Δ=0.8242 CS_LB=0.4409 cert=True | `data/results/main_real_200/pilot_report__internvl_8b/pilot_result.json` | `5686cc592f13` |
| `internvl_8b__absent_control` | absent_control | absent=58/60 present=58/60 | `data/results/main_real_200/pilot_report__internvl_8b/absent_object_control.json` | `faffbd5d32f3` |
| `llava_onevision_7b__presence` | presence | a=0.8901 p=0.1758 Δ=0.7143 CS_LB=0.331 cert=True | `data/results/main_real_200/pilot_report__llava_onevision_7b/pilot_result.json` | `9539b9f84ca6` |
| `llava_onevision_7b__absent_control` | absent_control | absent=60/60 present=58/60 | `data/results/main_real_200/pilot_report__llava_onevision_7b/absent_object_control.json` | `3a1d17e1be50` |

## Excluded (non-canonical)

- `data/results/main_real_200/final_report` — smoke-template markdown (MOCK_ONLY narrative); not canonical
- `data/results/main_real_200/final_report_v2` — smoke-template markdown; not canonical
- `affordance_intervention arm` — original accuracy ~chance; confounded; not certified

Verify integrity:

```bash
python3 -m certvic.v7.result_ledger_audit --ledger registry/results/main200_pilot_result_ledger.json
```
