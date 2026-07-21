# Post-Result Reviewer-Attack Audit

`evidence_status=REVIEWER_ATTACK_AUDIT_NON_EVIDENCE` · attacks: 12 · unresolved: 7 · {'answered': 5, 'partially_answered': 3, 'blocked': 1, 'unanswered': 3}

| # | attack | status | severity | remaining action |
| --- | --- | --- | --- | --- |
| 1 | Models simply do not perceive the object. | **answered** | low | None: original-image accuracy is 0.89-0.92 and absent-object present-accuracy is high, so the object is perceived; the gap is a post-edit update failure. |
| 2 | The question presupposes the object (answers without looking). | **answered** | low | None: on naturally absent objects the models answer 'no' at 58-60/60. |
| 3 | The edited images have residual artifacts the VLM exploits. | **partially_answered** | medium | Complete the human residual-cue review (scripts/apply_residual_cue_review.py); detectability AUC=0.349 already argues against trivial artifacts. |
| 4 | Models are sticky under any perturbation (no specificity). | **blocked** | high | Run spurious-flip / control_irrelevant VLM predictions for all 3 models, then integrate (V7 prompt 14). BLOCKER until predictions exist. |
| 5 | Only one dataset (ADE20K). | **unanswered** | medium | Execute the recommended COCO second-domain arm; readiness is assessed but not run. |
| 6 | Only one reviewer (no IAA). | **unanswered** | medium | Collect a second rater and compute Cohen's kappa (scripts/compute_review_iaa.py); tooling ready, two-rater IAA not yet computed. |
| 7 | n=91 is too small. | **unanswered** | medium | Execute a scaled run (main_500+) after the specificity control passes; plan ready. |
| 8 | Prompt polarity caused the effect. | **partially_answered** | medium | Run the polarity-validated ablation tasks (positive/negative/pixel-only/short). The canonical effect already holds across mixed phrasing. |
| 9 | The result is not reproduced across models. | **answered** | low | None: 3/3 open VLMs are certified under the pilot protocol (Qwen, InternVL, LLaVA). |
| 10 | The statistics are optional-stopping hacked. | **answered** | low | None: anytime-valid CS controls Type-I error under continuous peeking (statistical_sensitivity simulation). |
| 11 | Old reports are mock-labeled / non-canonical. | **answered** | low | None: the result ledger excludes final_report*/ by construction; canonical = pilot_report*/ only, documented in the project-state memo. |
| 12 | The benchmark is just another edited-image dataset. | **partially_answered** | medium | The natural-absence-vs-edited-absence dissociation, certification, and controls differentiate it; full differentiation needs the specificity control + scale. |

## Top unresolved

- **[high] blocked** — Models are sticky under any perturbation (no specificity). → Run spurious-flip / control_irrelevant VLM predictions for all 3 models, then integrate (V7 prompt 14). BLOCKER until predictions exist.
- **[medium] unanswered** — Only one dataset (ADE20K). → Execute the recommended COCO second-domain arm; readiness is assessed but not run.
- **[medium] unanswered** — Only one reviewer (no IAA). → Collect a second rater and compute Cohen's kappa (scripts/compute_review_iaa.py); tooling ready, two-rater IAA not yet computed.
- **[medium] unanswered** — n=91 is too small. → Execute a scaled run (main_500+) after the specificity control passes; plan ready.
- **[medium] partially_answered** — The edited images have residual artifacts the VLM exploits. → Complete the human residual-cue review (scripts/apply_residual_cue_review.py); detectability AUC=0.349 already argues against trivial artifacts.
