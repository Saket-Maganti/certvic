# V3 Command Index

Every V3 tool, by prompt. All are planning/diagnostic/audit tools — none run paid
services, downloads, GPU jobs, or VLM inference, and none make evidence claims.

| # | Area | Command |
| --- | --- | --- |
| 01 | Run ledger | `python3 -m certvic.provenance.run_ledger init --out data/provenance/run_ledger.jsonl` |
| 01 | Artifact graph | `python3 -m certvic.provenance.artifact_graph --ledger data/provenance/run_ledger.jsonl --out-dir data/provenance/artifact_graph` |
| 01 | Claim trace | `python3 -m certvic.provenance.trace_claim --claim-ledger data/results/claim_ledger.json --run-ledger data/provenance/run_ledger.jsonl --out data/provenance/claim_trace_report.md` |
| 02 | Storage plan | `python3 -m certvic.storage.plan_storage --config configs/real_pilot_ade20k.yaml --scale 2000 --out data/results/storage_plan_2000.json` |
| 02 | Dataset root policy | `python3 -m certvic.storage.dataset_roots --out data/results/dataset_root_policy.md` |
| 03 | Kaggle bundle | `python3 -m certvic.compute.kaggle_packager --job vlm_tiny --config configs/tiny_reviewed_eval.yaml --out-dir compute_bundles/kaggle_vlm_tiny` |
| 03 | Colab bundle | `python3 -m certvic.compute.colab_packager --job reports_only --config configs/smoke.yaml --out-dir compute_bundles/colab_reports_only` |
| 04 | Diffusion queue | `python3 -m certvic.edit.job_queue build --edit-plan data/manifests/pilot_edit_plan.jsonl --out data/manifests/diffusion_job_queue.jsonl --shards 4` |
| 04 | Diffusion resume | `python3 -m certvic.edit.diffusion_resume --queue data/manifests/diffusion_job_queue.jsonl --generated data/manifests/pilot_generated_edits.jsonl --out data/manifests/diffusion_resume.jsonl` |
| 05 | Edit detectability | `python3 -m certvic.validation.edit_detectability --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/results/edit_detectability` |
| 06 | Cluster diagnostics | `python3 -m certvic.metrics.cluster_diagnostics --scores data/results/pair_scores.jsonl --tasks data/manifests/tasks.jsonl --out-dir data/results/cluster_diagnostics` |
| 07 | Review batches | `python3 -m certvic.validation.review_batches --tasks data/manifests/pilot_eval_tasks_tiny.jsonl --out-dir data/annotations/review_batches --reviewers reviewer_a reviewer_b --overlap-rate 0.2` |
| 07 | Review progress | `python3 -m certvic.validation.review_progress --ratings-dir data/annotations/review_batches --out data/annotations/review_progress.json` |
| 07 | Adjudicate | `python3 -m certvic.validation.adjudicate_review --ratings data/annotations/visual_review_ratings.csv --out data/annotations/visual_review_adjudicated.csv` |
| 08 | Model run matrix | `python3 -m certvic.eval.run_matrix_planner --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --providers qwen2_5_vl_7b internvl_8b llava_onevision_7b --out-dir data/results/model_run_matrix --max-items 200 --num-shards 4` |
| 08 | Run status | `python3 -m certvic.eval.run_status --matrix data/results/model_run_matrix/run_matrix.json --pred-root data/predictions --out data/results/model_run_matrix/status.json` |
| 09 | Output triage | `python3 -m certvic.eval.output_triage --preds data/predictions/run.jsonl --tasks data/manifests/tasks.jsonl --out-dir data/results/output_triage` |
| 10 | Scale planner | `python3 -m certvic.planning.scale_planner --scale 2000 --out data/results/scale_plan_2000.md` |
| 11 | Dashboard | `python3 -m certvic.dashboard.build_dashboard --results-root data/results --out-dir data/dashboard` |
| 12 | Result manifest | `python3 -m certvic.paper.result_manifest --report-dir data/results/v2_report --claim-ledger data/results/claim_ledger.json --out paper/result_manifest.json` |
| 12 | Inject results | `python3 -m certvic.paper.inject_results --manifest paper/result_manifest.json --paper-dir paper --dry-run` |
| 12 | Paper trace | `python3 -m certvic.paper.paper_trace_report --paper-dir paper --manifest paper/result_manifest.json --out docs/PAPER_TRACE_REPORT.md` |
| 13 | Related work audit | `python3 -m certvic.paper.related_work_audit --matrix paper/related_work_matrix.yaml --paper paper/sections/02_related.tex --out docs/RELATED_WORK_AUDIT.md` |
| 14 | Reviewer simulation | `python3 -m certvic.review.simulate_reviews --paper-dir paper --reports-root data/results --out-dir docs/reviewer_simulation` |
| 14 | Rebuttal pack | `python3 -m certvic.review.rebuttal_pack --reviews docs/reviewer_simulation/reviews.json --out docs/rebuttal_pack.md` |
| 15 | Reproduction audit | `python3 -m certvic.release.reproduction_audit --scripts scripts --out docs/REPRODUCTION_AUDIT.md` |
| 16 | Security/privacy audit | `python3 -m certvic.security.release_privacy_audit --root . --out docs/SECURITY_PRIVACY_AUDIT.md` |
| 17 | Failure diagnosis | `python3 -m certvic.playbooks.diagnose_failure --report-dir data/results/tiny_real_pilot --out docs/playbooks/DIAGNOSIS.md` |
| 18 | Main study dry run | `python3 -m certvic.pipeline.main_study_dry_run --scale 200 --out-dir data/results/main_study_dry_run_200` |
| 19 | Final audit | `python3 -m certvic.v3.final_pre_real_run_audit --out docs/V3_FINAL_PRE_REAL_RUN_AUDIT_REPORT.md --json-out data/results/v3_final_pre_real_run_audit.json` |

## Reproduction scripts (dockerless)

```bash
bash scripts/reproduce_smoke.sh
bash scripts/reproduce_simulation.sh
bash scripts/reproduce_reports.sh
export ADE20K_ROOT=/path/to/ADEChallengeData2016 && bash scripts/reproduce_tiny_pilot_dry_run.sh
```

After the final audit passes, see `docs/V3_STOP_BUILDING_START_RUNNING.md`.
