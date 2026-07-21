# Failure Diagnosis

Generated: 2026-06-22

Report dir: `data/results/smoke_report`
Symptoms matched: 1  |  report present: True

Read-only diagnosis; maps observed symptoms to operational playbooks. No claims.

## Matched symptoms

| Symptom | Detail | Playbook |
| --- | --- | --- |
| No certified intervention-consistency gap | no certified claim found in report | `docs/playbooks/NO_CERTIFIED_GAP.md` |

## All playbooks

- `docs/playbooks/EDIT_REALISM_FAILURE.md` — Edit quality pass rate is low
- `docs/playbooks/EDIT_REALISM_FAILURE.md` — Edits are low-level detectable (artifact confound)
- `docs/playbooks/HIGH_PARSE_FAILURE.md` — High parse-failure rate
- `docs/playbooks/HIGH_CONTROL_FLIP.md` — High control-edit spurious-flip rate
- `docs/playbooks/NO_CERTIFIED_GAP.md` — No certified intervention-consistency gap
- `docs/playbooks/LOW_ORIGINAL_ACCURACY.md` — Low original-image accuracy
- `docs/playbooks/LOW_HUMAN_AGREEMENT.md` — Low inter-annotator agreement
- `docs/playbooks/TOO_FEW_CANDIDATES.md` — Too few candidate edits
- `docs/playbooks/GPU_PREFLIGHT_FAILURE.md` — GPU / preflight failure
- `docs/playbooks/LABEL_POLICY_FAILURE.md` — Label-policy rejections dominate
- `docs/playbooks/CLAIM_GATE_FAILURE.md` — Claim gate blocked the claim
- `docs/playbooks/KAGGLE_SESSION_FAILURE.md` — Kaggle/Colab session died mid-run
