# Scientific Validity Audit

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

The scientific question is whether intended responsiveness is separable from specificity under irrelevant edits.

## Intervention pilot

| Model | n | a | raw answer-change p | gap | CS LB | full certified |
|---|---|---|---|---|---|---|
| Qwen2.5-VL-7B | 91 | 0.9231 | 0.1758 | 0.7473 | 0.363958 | false |
| InternVL2-8B | 91 | 0.9231 | 0.0989 | 0.8242 | 0.440881 | false |
| LLaVA-OneVision-7B | 91 | 0.8901 | 0.1758 | 0.7143 | 0.330991 | false |

The historical quantity `p` is raw response change, not necessarily correct semantic updating.
Qwen and InternVL changes end on edited gold for 16/91 and 9/91 items. LLaVA changes on 16/91,
but only 13 reach edited gold. The full policy fails because n=91 < 150, family counts are
54/31/6, validity review is incomplete, and specificity is not uniformly cleared.

## Specificity pilot

| Model | V1 flips | rate | frozen V1 status |
|---|---|---|---|
| Qwen2.5-VL-7B | 12/94 | 0.127660 | FAIL |
| InternVL2-8B | 1/94 | 0.010638 | PASS observed rule only |
| LLaVA-OneVision-7B | 3/94 | 0.031915 | PASS observed rule only |

The current evidence supports a model-dependent pilot observation. It does not support a broad
robustness, causal-understanding, architecture, or population-generalization claim. All outputs
come from one ADE20K-derived household/object setting, and exact historical revisions are missing.

## Validity threats

- Inclusion decisions are machine-assisted preliminary, despite stale embedded labels.
- Conservative image-difference boxes intersect target boxes on 20/94 V1 controls; target-mask overlap is zero.
- Corrected grouped detectability is moderate, not proof that artifacts are absent.
- Current V2 is post-outcome and reuses V1; selection can change failure composition.
- The natural perception control shows unedited object recognition but cannot validate edited images.
