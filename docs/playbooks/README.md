# Failure Mode Playbooks

Operational playbooks for when a real run fails. Diagnose automatically with:

```bash
python3 -m certvic.playbooks.diagnose_failure --report-dir data/results/tiny_real_pilot --out docs/playbooks/DIAGNOSIS.md
```

| Playbook | Covers |
| --- | --- |
| [Edit Realism Failure](EDIT_REALISM_FAILURE.md) | Edit Realism Failure |
| [No Certified Gap](NO_CERTIFIED_GAP.md) | No Certified Gap |
| [High Parse Failure](HIGH_PARSE_FAILURE.md) | High Parse Failure |
| [High Control Spurious-Flip](HIGH_CONTROL_FLIP.md) | High Control Spurious-Flip |
| [Low Human Agreement](LOW_HUMAN_AGREEMENT.md) | Low Human Agreement |
| [Kaggle / Colab Session Failure](KAGGLE_SESSION_FAILURE.md) | Kaggle / Colab Session Failure |
| [Label Policy Failure](LABEL_POLICY_FAILURE.md) | Label Policy Failure |
| [Claim Gate Failure](CLAIM_GATE_FAILURE.md) | Claim Gate Failure |
| [Low Original Accuracy](LOW_ORIGINAL_ACCURACY.md) | Low Original Accuracy |
| [Too Few Candidates](TOO_FEW_CANDIDATES.md) | Too Few Candidates |
| [GPU / Preflight Failure](GPU_PREFLIGHT_FAILURE.md) | GPU / Preflight Failure |

Each playbook is a checklist, not a way to manufacture results: when the honest
answer is a null result or ineligible claim, report it.
