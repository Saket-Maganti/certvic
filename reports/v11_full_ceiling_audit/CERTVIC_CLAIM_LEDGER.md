# CertVIC Claim Ledger

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

Every substantive claim is scoped to the exact artifact that can support it.

| Claim | Classification | Exact evidence | Required qualification |
|---|---|---|---|
| Three open-model prediction files exist for the 91-pair intervention pilot. | currently supported | canonical presence JSONL files in the evidence ledger | Real outputs; item validity remains pending human review. |
| Numerical intervention-gap CS lower bounds exceed 0.05 for all three models. | supported with qualification | three `pilot_result.json` artifacts and raw pairs | Numeric crossing is not full certification. |
| Qwen flips on 12/94 V1 irrelevant-edit pairs. | currently supported | canonical Qwen V1 JSONL | Frozen observed-rate gate fails; mechanism is unknown. |
| InternVL and LLaVA flip on 1/94 and 3/94 V1 pairs. | supported with qualification | canonical V1 JSONL files | Validity review is incomplete and revisions are unpinned. |
| Specificity differs by model in this pilot. | supported with qualification | paired same-item comparison | Retrospective, exploratory, one domain. |
| The 12 Qwen flips are parser or row-integrity failures. | contradicted by current evidence | pair-integrity forensic audit | All pairs parse and match; this does not establish a causal mechanism. |
| The current V2 package independently confirms specificity. | prohibited | V1/V2 item-ID intersection | All 30 items reuse V1 and no V2 outputs exist. |
| The current V2 package is a stricter retrospective sensitivity set. | diagnostic only | V2 task and quality manifests | Four known Qwen failures retained, eight filtered out. |
| The pilot tasks completed independent human review. | contradicted by current evidence | reviewer identity and blank second-rater sheet | Machine assistance is preliminary, not human-reviewed evidence. |
| Main-500 results exist or execution is currently allowed. | prohibited | V11 protocol | `execution_allowed_now=false`. |
| CertVIC is submission-ready. | prohibited | blocker and gate ledgers | Human, independent-control, reproducibility, and literature blockers remain. |

No ledger entry is paper-claim eligible in the current V11 state. This conservative setting
does not erase real observations; it prevents incomplete validity evidence from being promoted.
