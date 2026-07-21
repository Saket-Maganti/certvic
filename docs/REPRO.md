# Reproducibility

## Smoke Workflow

```bash
python -m certvic.data.build_tasks --smoke --out data/manifests/smoke_tasks.jsonl
python -m certvic.data.manifest_checks --tasks data/manifests/smoke_tasks.jsonl --strict
python -m certvic.eval.run_eval --config configs/smoke.yaml --tasks data/manifests/smoke_tasks.jsonl --out data/predictions/smoke_mock_inconsistent.jsonl --provider mock_inconsistent --run-id smoke_mock_inconsistent_v1 --max-items 10
python -m certvic.metrics.score_predictions --tasks data/manifests/smoke_tasks.jsonl --preds data/predictions/smoke_mock_inconsistent.jsonl --out-scores data/results/smoke_pair_scores.jsonl --out-summary data/results/smoke_summary.json
python -m certvic.reporting.build_report --tasks data/manifests/smoke_tasks.jsonl --scores data/results/smoke_pair_scores.jsonl --preds data/predictions/smoke_mock_inconsistent.jsonl --out-dir data/results/smoke_report --alpha 0.05 --gap-threshold 0.05
python -m certvic.audit --config configs/smoke.yaml --tasks data/manifests/smoke_tasks.jsonl --preds data/predictions/smoke_mock_inconsistent.jsonl --scores data/results/smoke_pair_scores.jsonl --paper paper/main.tex --strict
```

## Pilot Workflow

Pilot runs require local user-provided data. CertVIC does not download ADE20K or
any other large dataset automatically.

### ADE20K Readiness Dry Run

Before any manifest generation, inspect the local root:

```bash
python3 -m certvic.data.pilot_readiness \
  --config configs/real_pilot_ade20k.yaml \
  --ade20k-root /path/to/ADE20K \
  --out-dir data/results/pilot_readiness_ade20k \
  --dry-run
```

Outputs:

- `data/results/pilot_readiness_ade20k/dataset_inspection.json`
- `data/results/pilot_readiness_ade20k/candidate_summary.json`
- `data/results/pilot_readiness_ade20k/license_summary.json`
- `data/results/pilot_readiness_ade20k/readiness_report.md`

This dry run does not copy pixels, generate edits, run VLM inference, require
GPU, or create evidence claims.

### ADE20K Manifest Generation

After the dry-run report shows a supported semantic PNG layout:

```bash
python3 -m certvic.data.ade20k_adapter \
  --ade20k-root /path/to/ADE20K \
  --out-sources data/manifests/ade20k_sources.jsonl \
  --out-masks data/manifests/ade20k_masks.jsonl \
  --inspection-out data/results/pilot_readiness_ade20k/dataset_inspection.json \
  --max-items 500
```

The adapter pairs image files with annotation PNGs by split and stem, identifies
non-background label IDs, computes bbox and mask-area fractions, and writes a
manifest-only mask JSONL. It does not generate edited images.

Binary mask PNG export is disabled by default:

```bash
python3 -m certvic.data.ade20k_adapter \
  --ade20k-root /path/to/ADE20K \
  --out-sources data/manifests/ade20k_sources.jsonl \
  --out-masks data/manifests/ade20k_masks.jsonl \
  --export-binary-masks \
  --mask-out-dir data/masks/ade20k_pilot \
  --max-items 500
```

Use export only for explicit local inspection. Do not treat exported masks as
paper evidence or redistributable assets until license/release checks pass.

### ADE20K Pilot Candidate Selection

After source and mask manifests exist, select review candidates:

```bash
python3 -m certvic.data.select_pilot_items \
  --sources data/manifests/ade20k_sources.jsonl \
  --masks data/manifests/ade20k_masks.jsonl \
  --out data/manifests/pilot_selection.jsonl \
  --summary-out data/manifests/pilot_selection_summary.json \
  --target 200 \
  --seed 0 \
  --max-masks-per-source 1 \
  --domains household \
  --splits train val \
  --allowed-task-families support_stability occlusion_safety affordance_reachability control_irrelevant \
  --min-mask-area-fraction 0.01 \
  --max-mask-area-fraction 0.40
```

These rows are `CANDIDATE_ONLY`. The summary reports shortfall warnings if the
target cannot be met.

### ADE20K Edit Plan And Task Preview

Plan edits without generating images:

```bash
python3 -m certvic.edit.plan_edits \
  --selection data/manifests/pilot_selection.jsonl \
  --out data/manifests/pilot_edit_plan.jsonl \
  --summary-out data/manifests/pilot_edit_plan_summary.json \
  --seed 0
```

Rejected candidates, if any, are written to
`data/manifests/pilot_edit_plan_rejected.jsonl`.

Preview non-runnable tasks:

```bash
python3 -m certvic.data.preview_tasks \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --out data/manifests/pilot_task_preview.jsonl \
  --summary-out data/manifests/pilot_task_preview_summary.json
```

Build the review report:

```bash
python3 -m certvic.reporting.pilot_plan_report \
  --selection data/manifests/pilot_selection.jsonl \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --task-preview data/manifests/pilot_task_preview.jsonl \
  --out-dir data/results/pilot_plan_review
```

Manual inspection before V1.5 generation:

- review selected source/mask/label rows
- review rejected candidates and feasibility reasons
- confirm release mode and license posture
- confirm leakage summary is clean
- confirm task-family and edit-type mappings are plausible

These artifacts are still not evidence. They contain no edited images, no model
outputs, no human validity checks, and no certified claims.

### Tiny Edit Generation And Quality Report

After `pilot_edit_plan.jsonl` exists and has been reviewed, generate a tiny
local batch only:

```bash
python3 -m certvic.edit.generate_edits \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --out-dir data/edits/ade20k_tiny_pilot \
  --out-manifest data/manifests/pilot_generated_edits.jsonl \
  --rejected-out data/manifests/pilot_generated_edits_rejected.jsonl \
  --summary-out data/results/tiny_edit_generation_summary.json \
  --max-items 20 \
  --mode simple \
  --seed 0
```

`--mode simple` is deterministic, local, CPU-friendly, and zero-cost. It is
pipeline validation only. It does not use diffusers, download model weights, run
VLM inference, or create paper evidence.

Build the quality report:

```bash
python3 -m certvic.edit.quality_report \
  --generated-manifest data/manifests/pilot_generated_edits.jsonl \
  --rejected data/manifests/pilot_generated_edits_rejected.jsonl \
  --out-dir data/results/tiny_edit_quality_report
```

Materialize tiny non-evidence task rows only from generated edits that passed
quality gates:

```bash
python3 -m certvic.data.materialize_tasks \
  --task-preview data/manifests/pilot_task_preview.jsonl \
  --generated-edits data/manifests/pilot_generated_edits.jsonl \
  --out data/manifests/pilot_eval_tasks_tiny.jsonl \
  --summary-out data/manifests/pilot_eval_tasks_tiny_summary.json
```

Quality gates check structural edit validity: mask area, bbox validity,
inside/outside-mask changes, edit-specific allowed regions, image-size match,
edited file/hash presence, nonempty changed region, and simple artifact
warnings. Passing gates does not mean semantic validity, human validity, or VLM
evidence.

Manual inspection before any VLM inference:

- inspect generated original/edited pairs
- inspect `pilot_generated_edits_rejected.jsonl`
- inspect `data/results/tiny_edit_quality_report/generated_edit_review.md`
- confirm simple-mode edits are semantically valid
- confirm task prompts and filenames are leakage-clean
- prepare human validity checks

Generated rows remain `GENERATED_EDIT_ONLY`. Materialized rows remain
`EDIT_READY_NON_EVIDENCE`.

Before pilot:

- verify licenses and release modes
- build source and mask manifests
- review pilot candidate and edit-plan manifests
- inspect tiny generated edits and quality report
- run leakage checks
- run edit quality gates
- export human validation sheets
- keep optional free-tier references disabled unless genuinely free
- keep ADE20K pixels pointer-only unless redistribution is explicitly verified

## V2 label policy (ADE20K task-family eligibility)

Build label-policy diagnostics over a mask manifest (descriptive only, no claims):

```bash
python3 -m certvic.data.label_policy_report \
  --masks data/manifests/ade20k_masks.jsonl \
  --policy configs/ade20k_label_policy.yaml \
  --out-dir data/results/label_policy_report
```

Inspect a single label decision:

```bash
python3 -m certvic.data.label_policy --policy configs/ade20k_label_policy.yaml \
  --label-id 16 --task-family support_stability --edit-type displace
```

Selection and edit planning accept `--label-policy configs/ade20k_label_policy.yaml`.
With a policy: blocked labels (background "stuff") are rejected, family/edit
combinations incompatible with a label are rejected, and unresolved labels fall
back to control-only eligibility. The selector records the policy version/hash
and an unresolved-label count; `--per-family-target-json '{"support_stability":50}'`
emits a warning when a family target cannot be met.

`configs/ade20k_label_policy.yaml` is an UNVERIFIED template. Confirm the
label_id -> name map against your ADE20K release before any evidence run.

## V2 modular edit engine

Batch generate edits with a replayable engine (simple engines run on CPU; the
diffusers engine is disabled unless local/cached weights + GPU are present):

```bash
python3 -m certvic.edit.engines \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --out-dir data/edits/pilot --out-manifest data/manifests/pilot_generated_edits.jsonl \
  --rejected-out data/manifests/pilot_generated_rejected.jsonl \
  --summary-out data/results/pilot_generation_summary.json \
  --engine simple_fill --max-items 20 --seed 0 --resume
```

Engines: simple_fill, simple_occlude, simple_displace, simple_control,
composite_occluder, diffusers_inpaint_optional (disabled by default), no_op_debug.
Each generated row carries replay metadata (engine version, seed,
source_image_sha256, mask_spec_hash, edit_plan_hash, generation_config_hash,
actual params). Batch safety: `--max-items` required unless `--allow-full-run`,
resume by edit_id, no overwrite by default, duplicate-edited-image detection.
Stricter degenerate-edit gates live in `configs/edit_quality.yaml` (opt-in).

## V2 visual review workflow

```bash
python3 -m certvic.validation.export_visual_review --tasks data/manifests/pilot_eval_tasks_tiny.jsonl \
  --generated-edits data/manifests/pilot_generated_edits.jsonl --out data/annotations/visual_review_sheet.csv --max-items 50 --seed 0
python3 -m certvic.validation.build_review_gallery --review-sheet data/annotations/visual_review_sheet.csv --out-dir data/annotations/visual_review_gallery
# (reviewers fill yes/no/uncertain into visual_review_ratings.csv) then:
python3 -m certvic.validation.aggregate_visual_review --ratings data/annotations/visual_review_ratings.csv \
  --out data/annotations/visual_review_summary.json --keep-list data/annotations/visual_keep_items.txt --drop-list data/annotations/visual_drop_items.txt
python3 -m certvic.data.apply_visual_review --tasks data/manifests/pilot_eval_tasks_tiny.jsonl \
  --keep-list data/annotations/visual_keep_items.txt --out data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --summary-out data/manifests/pilot_eval_tasks_tiny_reviewed_summary.json
python3 -m certvic.reporting.visual_review_report --summary data/annotations/visual_review_summary.json \
  --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/results/visual_review_report
```

Drop rule: an item is dropped if ANY of photorealistic, single_factor,
target_object_clear, required_change_unambiguous, prompt_answerable, keep_for_eval
is majority-no or uncertain-heavy. IAA: Cohen's kappa (2 raters) / majority
agreement (3+) per field, with a single-rater warning. Approved tasks become
`HUMAN_REVIEWED_NON_EVIDENCE` — human review validates quality only, never model
evidence. The review sheet contains no model outputs.

## V2 baselines and ablations

```bash
python3 -m certvic.eval.run_ablations --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/predictions/ablations --max-items 50 --seed 0
python3 -m certvic.reporting.ablations --pred-dir data/predictions/ablations --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/results/ablation_report
```

Baselines (construct-validity, not evidence): random_seeded, majority_by_family,
text_only_heuristic, caption_only_stub, original_only, edited_only, answer_prior,
prompt_shuffle_control. Outputs: baseline_table.csv, parser_sensitivity.csv
(strict vs lenient, ambiguous/recovered/fail buckets), prompt_sensitivity.csv
(6 prompt variants incl. leakage stress), construct_validity_flags.json
(flags the task as gameable if a non-visual baseline exceeds the consistency
threshold), ablation_summary.md.

## V2 power planning and certification policy

```bash
python3 -m certvic.metrics.power_plan --config configs/real_pilot_ade20k.yaml --out-dir data/results/power_plan --optional-stopping
```

Outputs power_plan.json, n_vs_gap.csv, optional_stopping_sim.csv (when
--optional-stopping and confseq available), power_plan.md. The certification
policy (`configs/certification_policy.yaml`) gates claims on min_n_overall,
min_n_by_family, parse_failure_max, control_spurious_flip_max,
evidence_status_required, provider_type_disallowed, AND an available anytime-valid
CS lower bound above gap_threshold. A bootstrap CI is never certification; CS
unavailable means not certified.

## V2 tiny real-pilot orchestrator

```bash
python3 -m certvic.pipeline.run_tiny_pilot --config configs/real_pilot_ade20k.yaml \
  --ade20k-root /absolute/path/to/ADE20K --out-dir data/results/tiny_real_pilot --max-items 20 --dry-run
```

Chains readiness -> manifests -> label policy -> selection -> edit plan ->
preview -> plan report -> tiny edit generation -> quality report ->
materialization -> visual review sheet. No VLM inference. `--dry-run` stops after
the label-policy report and prints the remaining commands. Resumes by stage
(stage_status.json); writes command_log.txt and zero_cost_audit.json. See
docs/TINY_REAL_PILOT_RUNBOOK.md.

## V2 tiny eval + scoring path

```bash
python3 -m certvic.pipeline.run_tiny_eval --config configs/tiny_reviewed_eval.yaml \
  --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --provider qwen2_5_vl_7b --out-dir data/results/tiny_eval_qwen --max-items 20
```

Evidence path requires reviewed tasks + a non-mock open-local provider. See
docs/TINY_EVAL_RUNBOOK.md.

## V2 open-local VLM preflight

```bash
python3 -m certvic.eval.vlm_preflight --provider qwen2_5_vl_7b --config configs/kaggle_open_vlm.yaml \
  --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/results/vlm_preflight_qwen.json
```

Checks manifest/images exist, provider importability + metadata, optional deps,
optional GPU (`--check-gpu`), memory estimate, output writable, zero-cost policy.
Runs no inference. The runner writes `<out>.provider_metadata.json` and
`<out>.environment.json` sidecars; `--evidence-run` blocks mock providers and
unreviewed tasks.

## V2 paper-ready report (tables + figures)

```bash
python3 -m certvic.reporting.build_v2_report --scores data/results/pair_scores.jsonl \
  --preds data/predictions/run.jsonl --tasks data/manifests/tasks.jsonl --out-dir data/results/v2_report
```

Tables (csv/tex): main_results, by_family, by_domain, by_edit_type, control_edit,
parser_sensitivity, certification. Figures (matplotlib/Agg): consistency_gap_bar,
cs_trajectory, by_family_heatmap, parse_failure, control_spurious_flip,
sample_count, with figure_manifest.json (figure_id, source, command, claim_status,
paper_ready). Unavailable cells render as `--`; descriptive vs certified is kept
separate; claim_ledger.json records eligibility.

## V2 failure taxonomy + gallery

```bash
python3 -m certvic.reporting.failure_gallery_v2 --tasks data/manifests/tasks.jsonl \
  --preds data/predictions/run.jsonl --scores data/results/pair_scores.jsonl --out-dir data/results/failure_gallery_v2
```

Deterministic taxonomy (10 types incl. missed_required_change, answer_inertia,
spurious_flip_on_control). Outputs failure_gallery.jsonl, failure_taxonomy_summary.csv,
failure_gallery.md, local_gallery.html, paper_candidate_failures.jsonl. No pixel
copy by default; local links; safe non-deployment captions; supports a manual
override jsonl.

## V2 recipe-first artifact release

```bash
python3 -m certvic.release.build_artifact --config configs/release_recipe.yaml --out-dir release/certvic_recipe_artifact
python3 -m certvic.release.data_card --manifests data/manifests --out release/DATA_CARD_GENERATED.md
```

Packages pointers/hashes/masks-metadata/edit-plans/task-manifests/scripts; never
non-redistributable pixels by default. Anonymizes local absolute paths, writes
checksums.json, release_audit.json (no private paths, no forbidden pixels, license
summary, reproducibility commands, zero-cost statement), and README.md.

## V2 main pilot gate checks

```bash
python3 -m certvic.pipeline.pilot_gate_check --stage before_vlm --config configs/real_pilot_ade20k.yaml --out data/results/pilot_gate_before_vlm.json
```

See docs/MAIN_PILOT_200_RUNBOOK.md and docs/PILOT_GATE_CHECKS.md.

## V2.1 simulation stress lab

Run one simulation-only scenario:

```bash
python3 -m certvic.sim.generate_synthetic_run \
  --out-dir data/results/v2_1_sim/high_accuracy_low_consistency \
  --scenario high_accuracy_low_consistency \
  --n-items 500 \
  --seed 0
```

Run the full built-in stress matrix:

```bash
python3 -m certvic.sim.stress_scenarios \
  --out-dir data/results/v2_1_sim_matrix \
  --n-items 500 \
  --seed 0
```

All simulation artifacts are `SIMULATED_ONLY`, `simulated=true`,
`zero_cost=true`, and `not_for_paper_claims=true`. The lab exercises metrics,
certification, reporting, parse-failure, control-spurious-flip, and claim-gate
paths before real ADE20K/GPU/model runs. It is not real data, not VLM evidence,
and not paper evidence.

## Run ledger and provenance (V3)

Record every real run so its artifacts are hash-traceable and any paper number
can be tied back to the command/config that produced it:

```bash
python3 -m certvic.provenance.run_ledger init --out data/provenance/run_ledger.jsonl
python3 -m certvic.provenance.run_ledger add \
  --ledger data/provenance/run_ledger.jsonl \
  --stage scoring --run-id <ID> \
  --inputs <paths...> --outputs <paths...> \
  --config <config> --command "<cmd>" --evidence-status REAL_EVIDENCE
python3 -m certvic.provenance.artifact_graph \
  --ledger data/provenance/run_ledger.jsonl --out-dir data/provenance/artifact_graph
python3 -m certvic.provenance.trace_claim \
  --claim-ledger data/results/claim_ledger.json \
  --run-ledger data/provenance/run_ledger.jsonl \
  --out data/provenance/claim_trace_report.md
```

The ledger is metadata only: no downloads, no GPU, no paid services, no claims.
See `docs/RUN_LEDGER.md`.

## Storage and path policy (V3)

Estimate disk and audit output paths before a study:

```bash
python3 -m certvic.storage.dataset_roots --out data/results/dataset_root_policy.md
python3 -m certvic.storage.plan_storage --config configs/real_pilot_ade20k.yaml --scale 200  --out data/results/storage_plan_200.json
python3 -m certvic.storage.plan_storage --config configs/real_pilot_ade20k.yaml --scale 2000 --out data/results/storage_plan_2000.json
```

See `docs/STORAGE_AND_PATH_POLICY.md`. Planning only: no scanning, no downloads,
no paid services.

## Free-compute job bundles (V3)

Generate copy-safe Kaggle/Colab bundles (no pixels, no credentials, anonymized):

```bash
python3 -m certvic.compute.kaggle_packager --job diffusion_tiny --config configs/real_pilot_ade20k.yaml --out-dir compute_bundles/kaggle_diffusion_tiny
python3 -m certvic.compute.kaggle_packager --job vlm_tiny       --config configs/tiny_reviewed_eval.yaml --out-dir compute_bundles/kaggle_vlm_tiny
python3 -m certvic.compute.colab_packager  --job reports_only   --config configs/smoke.yaml              --out-dir compute_bundles/colab_reports_only
```

Bundles are planning artifacts (`JOB_PLANNED_ONLY`), never executed. See
`docs/FREE_COMPUTE_BUNDLES.md`.

## Scaled human review (V3)

```bash
python3 -m certvic.validation.review_batches --tasks data/manifests/pilot_eval_tasks_tiny.jsonl --out-dir data/annotations/review_batches --reviewers reviewer_a reviewer_b --overlap-rate 0.2 --seed 0
python3 -m certvic.validation.review_progress --ratings-dir data/annotations/review_batches --out data/annotations/review_progress.json
python3 -m certvic.validation.adjudicate_review --ratings data/annotations/visual_review_ratings.csv --out data/annotations/visual_review_adjudicated.csv
```

Balanced batching + overlap for IAA, progress/disagreement tracking, majority-vote
adjudication. No paid annotation. See `docs/HUMAN_REVIEW_OPERATIONS.md`.

## Local run dashboard (V3)

Build a static HTML dashboard over local artifacts (runs, metrics, quality,
review, claims, provenance):

```bash
python3 -m certvic.dashboard.build_dashboard --results-root data/results --out-dir data/dashboard
# open data/dashboard/index.html
```

Static files only — no external services, no JS framework, no pixels. Highlights
missing gates and non-evidence flags. See `docs/LOCAL_DASHBOARD.md`.

## Dockerless reproduction scripts (V3)

Normal-shell, no-Docker reproduction (CPU-only except the dry-run pilot, which
needs a local ADE20K root):

```bash
bash scripts/reproduce_smoke.sh
bash scripts/reproduce_simulation.sh
export ADE20K_ROOT=/path/to/ADEChallengeData2016
bash scripts/reproduce_tiny_pilot_dry_run.sh
bash scripts/reproduce_reports.sh
python3 -m certvic.release.reproduction_audit --scripts scripts --out docs/REPRODUCTION_AUDIT.md
```

Each script uses `set -euo pipefail`, no `rm -rf`, no paid markers. See
`docs/DOCKERLESS_REPRODUCTION.md`.

## V4 real-run command bundles

Generate exact run-later command bundles without executing any real run:

```bash
python3 -m certvic.commands.generate_real_run_commands --stage tiny_pilot --out-dir commands/tiny_pilot
python3 -m certvic.commands.generate_real_run_commands --stage main_200 --out-dir commands/main_200
python3 -m certvic.commands.generate_real_run_commands --stage full_2000 --out-dir commands/full_2000
```

Each bundle writes `commands.sh`, `commands.md`, `command_manifest.json`,
`expected_inputs.md`, `expected_outputs.md`, and `resume_notes.md`. The bundles
are `RUN_COMMANDS_PLANNED_ONLY`: generation does not download datasets or model
weights, run GPU jobs, run VLM inference, or create paper evidence. Absolute
local roots are anonymized to `<ADE20K_ROOT>` and `<MODEL_CACHE_ROOT>` by
default. See `docs/V4_COMMAND_INDEX.md`.
