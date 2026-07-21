# V7 Post-3-Model Final Audit & Stop Conditions

`evidence_status=FINAL_AUDIT_NON_EVIDENCE` · **paper_grade_ready: False** · unresolved reviewer attacks: 7

## Category status

| category | status | note |
| --- | --- | --- |
| canonical_result_artifacts | **pass** | ledger audit passed=True (6 rows hash-locked) |
| multi_model_replication | **pass** | 3/3 open VLMs certified under the pilot protocol |
| control_status | **blocked** | spurious-flip predictions missing -> specificity BLOCKED |
| human_review_iaa | **partial** | single-rater only; two-rater IAA status=second_rater_pending |
| scale_readiness | **ready_plan** | gated scale plan exists (projections); not executed |
| second_domain_readiness | **ready_plan** | COCO recommended; not executed |
| mechanism_probes | **ready_plan** | probe tasks generated; predictions pending |
| statistical_validity | **pass** | anytime-valid CS; optional-stopping Type-I controlled |
| paper_report_language | **pass** | claim-language guard clean on V7 paper/report deliverables; pilot-only scaffold written |
| release_privacy_security | **pass** | privacy audit passed=True; release_ready=False (path relativization pending) |

## Stop / build policy

| proposed task | verdict | why |
| --- | --- | --- |
| More generic V7+ infrastructure | **DO_NOT_DO** | Elevation infra is complete; further generic building does not add evidence. |
| Spurious-flip / control_irrelevant predictions + integration | **RUN_NOW** | Lone high-severity blocker; integration code is ready and gated. |
| Scale to main_500/800+ | **BUILD_ONLY_IF_BLOCKED** | Run after the specificity control passes; plan + gates already exist. |
| Second-rater IAA collection | **RUN_NOW** | Blinded export + kappa tooling ready; needs one human rater. |
| Residual-cue human review | **RUN_NOW** | Blank sheet + summarizer ready; needs human labels. |
| Mechanism / prompt-ablation predictions | **RUN_NOW** | Task manifests generated; cheap free-tier inference. |
| Second domain (COCO) execution | **BUILD_ONLY_IF_BLOCKED** | Only if a reviewer demands cross-domain before scale; readiness assessed. |
| More models beyond 3 | **BUILD_ONLY_IF_BLOCKED** | Only on explicit reviewer need; 3-model replication already holds. |
| Paper pilot result + limitations section | **WRITE_NOW** | Fresh, guard-clean, pilot-only scaffold already written; keep it current. |

## Paper-grade gate (harsh)

- control_pass: False
- scale_executed: False
- two_rater_iaa: False
- **paper_grade_ready: False**

## One next highest-leverage action

Run the spurious-flip / control_irrelevant VLM predictions for all 3 models on free Kaggle, then integrate (python3 -m certvic.v7.spurious_control_integration). It is the lone high-severity blocker and gates both the specificity claim and scaling.
