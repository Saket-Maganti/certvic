# V5 Command Index

All V5 commands are CPU/local planning, auditing, or scaffold commands. They do
not download data or weights, run GPU jobs, run VLM inference, or create
evidence claims.

| Prompt | Area | Command |
| --- | --- | --- |
| 01 | Item certificates | `python3 -m certvic.validity.item_certificate --tasks <tasks.jsonl> --edits <generated_edits.jsonl> --review <visual_review_summary.json> --out data/validity/item_certificates.jsonl --report-dir data/results/item_validity` |
| 02 | Analysis plan lock | `python3 -m certvic.analysis.analysis_plan_lock --config configs/certification_policy.yaml --out docs/ANALYSIS_PLAN_LOCK.md --json-out data/results/analysis_plan_lock.json` |
| 03 | Theory audit | `python3 -m certvic.paper.theory_audit --paper-dir paper --out docs/THEORY_AUDIT.md` |
| 04 | Result-free paper audit | `python3 -m certvic.paper.result_free_completeness_audit --paper-dir paper --out docs/RESULT_FREE_COMPLETENESS_AUDIT.md` |
| 05 | Rater training | `python3 -m certvic.validation.rater_training --out-dir docs/rater_training` |
| 05 | Rater calibration | `python3 -m certvic.validation.rater_calibration --ratings <ratings.csv> --gold <gold.csv> --out-dir data/results/rater_calibration` |
| 06 | Edit realism scorecard | `python3 -m certvic.reporting.edit_realism_scorecard --ratings <visual_review_ratings.csv> --out-dir data/results/edit_realism_scorecard` |
| 07 | Answerability sheet | `python3 -m certvic.validation.answerability --tasks <tasks.jsonl> --out data/annotations/answerability_sheet.csv` |
| 07 | Apply answerability | `python3 -m certvic.data.apply_answerability_review --tasks <tasks.jsonl> --ratings <answerability_ratings.csv> --out <reviewed_tasks.jsonl>` |
| 08 | Model card | `python3 -m certvic.cards.model_card --provider <provider> --out cards/model_<provider>.md` |
| 08 | Eval card | `python3 -m certvic.cards.eval_card --run-dir <run_dir> --out cards/eval_<run_id>.md` |
| 09 | Registry validate | `python3 -m certvic.experiments.registry validate --config configs/experiments.yaml` |
| 09 | Registry render | `python3 -m certvic.experiments.registry render --config configs/experiments.yaml --out docs/EXPERIMENT_REGISTRY.md` |
| 10 | Result contracts | `python3 -m certvic.contracts.result_contracts validate --contracts configs/result_contracts.yaml --root data/results` |
| 11 | Claim guard | `python3 -m certvic.validation.claim_language_guard --root paper docs --out docs/CLAIM_LANGUAGE_GUARD_REPORT.md` |
| 12 | Score simulator | `python3 -m certvic.review.score_simulator --paper-dir paper --reports-root data/results --out-dir docs/cvpr_score_simulation` |
| 13 | Figure audit | `python3 -m certvic.paper.figure_manifest_audit --manifest paper/figure_manifest.yaml --paper-dir paper --out docs/FIGURE_MANIFEST_AUDIT.md` |
| 14 | Table audit | `python3 -m certvic.paper.table_manifest_audit --manifest paper/table_manifest.yaml --out docs/TABLE_MANIFEST_AUDIT.md` |
| 15 | Response bank | `python3 -m certvic.review.response_bank --out docs/response_bank/index.md` |
| 16 | Ablation interpreter | `python3 -m certvic.reporting.ablation_interpreter --ablation-report data/results/ablation_report --out docs/ABLATION_INTERPRETATION_DRAFT.md` |
| 17 | Certification interpreter | `python3 -m certvic.reporting.certification_interpreter --cert-report data/results/certification.json --claim-ledger data/results/claim_ledger.json --out docs/CERTIFICATION_CLAIM_DRAFT.md` |
| 18 | Ethics audit | `python3 -m certvic.paper.ethics_audit --paper-dir paper --out docs/ETHICS_AUDIT.md` |
| 19 | Package plan | `python3 -m certvic.submission.package_plan --paper-dir paper --out-dir docs/submission_package_plan` |
| 20 | Critical path | `python3 -m certvic.planning.deadline_plan --target-date 2026-11-15 --out docs/CVPR_2027_CRITICAL_PATH.md` |
| 21 | CVPR-ready audit | `python3 -m certvic.v5.cvpr_ready_except_results_audit --out docs/V5_CVPR_READY_EXCEPT_RESULTS_AUDIT.md --json-out data/results/v5_cvpr_ready_except_results_audit.json` |
| 23 | All commands smoke | `python3 -m certvic.v5.all_commands_smoke --out data/results/v5_all_commands_smoke.json` |

