# V4 Command Index

V4 commands are run-later infrastructure. Generating these artifacts does not
download datasets or model weights, run GPU jobs, run VLM inference, or create
paper evidence.

| Prompt | Area | Command |
| --- | --- | --- |
| 01 | Real-run command bundle | `python3 -m certvic.commands.generate_real_run_commands --stage tiny_pilot --out-dir commands/tiny_pilot` |
| 01 | Real-run command bundle | `python3 -m certvic.commands.generate_real_run_commands --stage main_200 --out-dir commands/main_200` |
| 01 | Real-run command bundle | `python3 -m certvic.commands.generate_real_run_commands --stage full_2000 --out-dir commands/full_2000` |
| 02 | Kaggle notebook | `python3 -m certvic.notebooks.kaggle_notebook_builder --job diffusion_tiny --out notebooks/generated/kaggle_diffusion_tiny.ipynb` |
| 02 | Kaggle notebook | `python3 -m certvic.notebooks.kaggle_notebook_builder --job vlm_200 --out notebooks/generated/kaggle_vlm_200.ipynb` |
| 03 | Colab notebook | `python3 -m certvic.notebooks.colab_notebook_builder --job diffusion_tiny --out notebooks/generated/colab_diffusion_tiny.ipynb` |
| 03 | Colab notebook | `python3 -m certvic.notebooks.colab_notebook_builder --job vlm_tiny --out notebooks/generated/colab_vlm_tiny.ipynb` |
| 04 | Model cache manifest | `python3 -m certvic.models.cache_manifest --provider qwen2_5_vl_7b --cache-root /path/to/cache --out data/model_cache/qwen_manifest.json` |
| 04 | Model cache check | `python3 -m certvic.models.cache_check --manifest data/model_cache/qwen_manifest.json --out data/model_cache/qwen_check.json` |
| 05 | Dataset fallback options | `python3 -m certvic.data.fallback_sources --out docs/FALLBACK_DATASET_OPTIONS.md` |
| 06 | CC0 showcase split | `python3 -m certvic.data.showcase_split --sources data/manifests/cc0_sources.jsonl --out data/manifests/showcase_split.jsonl` |
| 06 | Showcase package | `python3 -m certvic.release.showcase_package --split data/manifests/showcase_split.jsonl --out-dir release/showcase` |
| 07 | Edit sweep planner | `python3 -m certvic.edit.parameter_sweep --edit-plan data/manifests/pilot_edit_plan.jsonl --out data/manifests/edit_sweep_plan.jsonl --max-combinations 20` |
| 08 | Static review app | `python3 -m certvic.review_app.build_static_app --review-sheet data/annotations/visual_review_sheet.csv --out-dir data/review_app` |
| 09 | Run inspection | `python3 -m certvic.recovery.inspect_run --run-dir data/results/tiny_real_pilot --out data/results/recovery_report.json` |
| 09 | Manifest repair dry-run | `python3 -m certvic.recovery.repair_manifests --input broken.jsonl --out repaired.jsonl --dry-run` |
| 10 | Prediction merge | `python3 -m certvic.eval.merge_predictions --pred-dirs data/predictions/shards --out data/predictions/merged.jsonl --report data/results/merge_report.json` |
| 11 | Model comparison | `python3 -m certvic.reporting.model_comparison --score-dirs data/results/model_scores --out-dir data/results/model_comparison` |
| 12 | Statistical sensitivity | `python3 -m certvic.metrics.sensitivity_suite --scores data/results/pair_scores.jsonl --out-dir data/results/stat_sensitivity` |
| 13 | Qualitative figures | `python3 -m certvic.paper.qualitative_figures --gallery data/results/failure_gallery_v2/failure_gallery.jsonl --out-dir paper/figures/qualitative --dry-run` |
| 14 | LaTeX audit | `python3 -m certvic.paper.latex_audit --paper-dir paper --out docs/LATEX_AUDIT.md` |
| 15 | Supplement generator | `python3 -m certvic.paper.supplement_generator --reports-root data/results --out paper/supp/generated_supplement.tex --dry-run` |
| 16 | Capsule validator | `python3 -m certvic.release.capsule_validator --release-dir release/certvic_recipe_artifact --out docs/CAPSULE_VALIDATION.md` |
| 17 | Freeze results | `python3 -m certvic.results.freeze_results --results-root data/results/main_study --out results_lock.json` |
| 17 | Compare lockfile | `python3 -m certvic.results.compare_lockfile --lockfile results_lock.json --out docs/RESULT_LOCK_DIFF.md` |
| 18 | Submission checklist | `python3 -m certvic.submission.checklist --out docs/CVPR_SUBMISSION_CHECKLIST.md` |
| 18 | Deadline plan | `python3 -m certvic.submission.deadline_plan --deadline 2026-11-15 --out docs/CVPR_DEADLINE_PLAN.md` |
| 19 | Troubleshooting | `python3 -m certvic.troubleshoot.diagnose_logs --log run.log --out docs/TROUBLESHOOTING_DIAGNOSIS.md` |
| 20 | Dataset license expansion | `python3 -m certvic.data.license_expansion --out docs/DATASET_LICENSE_EXPANSION.md` |
| 21 | Reviewer quality | `python3 -m certvic.validation.reviewer_quality --ratings data/annotations/visual_review_ratings.csv --out-dir data/annotations/reviewer_quality` |
| 22 | Ablation plan | `python3 -m certvic.planning.ablation_plan --scale 2000 --models qwen2_5_vl_7b internvl_8b llava_onevision_7b --out docs/ABLATION_PLAN.md` |
| 23 | Internal review packet | `python3 -m certvic.submission.internal_review_packet --paper-dir paper --reports-root data/results --out-dir review_packet` |
| 24 | Final V4 audit | `python3 -m certvic.v4.final_all_system_audit --out docs/V4_FINAL_ALL_SYSTEM_AUDIT_REPORT.md --json-out data/results/v4_final_all_system_audit.json` |

## Safety Contract

- Generated command bundles are `RUN_COMMANDS_PLANNED_ONLY`.
- Absolute local roots are replaced by `<ADE20K_ROOT>` and `<MODEL_CACHE_ROOT>`
  unless `--no-anonymize` is explicitly used.
- Paid and non-core reference providers are rejected.
- The scripts include dry-run, max-item, resume, leakage, and evidence-run
  flags where the underlying command supports them.

Future V4 prompt implementations should append their commands here.
