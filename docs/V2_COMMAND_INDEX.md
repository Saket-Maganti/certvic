# V2 Command Index

Audits
- `python3 -m certvic.v2.baseline_audit --out docs/V2_BASELINE_AUDIT_REPORT.md`
- `python3 -m certvic.v2.full_audit --out docs/V2_FULL_SYSTEM_AUDIT_REPORT.md`
- `python3 -m certvic.v2.pre_run_master_audit --out docs/V2_7_PRE_RUN_MASTER_AUDIT_REPORT.md [--tasks <manifest>]`
- `python3 -m certvic.v2.reviewer_attack_harness --out docs/REVIEWER_ATTACK_HARNESS_REPORT.md`

Pre-run hardening (no data/GPU)
- `python3 -m certvic.sim.anytime_validity --out-dir data/results/anytime_validity --n 400 --n-trials 3000 [--figure]`
- `python3 -m certvic.validation.paper_numbers_guard [--manifest <provenance.json>]`
- `python3 -m certvic.eval.adversarial_audit --tasks <manifest> --out-dir data/results/adversarial_audit`
- `python3 -m certvic.edit.diffusion_preflight --edit-plan <plan.jsonl> --engine diffusers_inpaint_optional --weights-dir <local_weights> --check-gpu`

Data / label policy
- `python3 -m certvic.data.ade20k_adapter --ade20k-root <ROOT> --out-sources ... --out-masks ...`
- `python3 -m certvic.data.label_policy_report --masks ... --policy configs/ade20k_label_policy.yaml --out-dir ...`
- `python3 -m certvic.data.select_pilot_items --sources ... --masks ... --out ... --label-policy configs/ade20k_label_policy.yaml [--per-family-target-json '{"support_stability":50}']`
- `python3 -m certvic.edit.plan_edits --selection ... --out ... --summary-out ... --label-policy configs/ade20k_label_policy.yaml`

Edit engine
- `python3 -m certvic.edit.engines --edit-plan ... --out-dir ... --out-manifest ... --rejected-out ... --summary-out ... --engine simple_fill --max-items 20 --resume`

Visual review
- `python3 -m certvic.validation.export_visual_review --tasks ... --generated-edits ... --out ... --max-items 50`
- `python3 -m certvic.validation.build_review_gallery --review-sheet ... --out-dir ...`
- `python3 -m certvic.validation.aggregate_visual_review --ratings ... --out ... --keep-list ... --drop-list ...`
- `python3 -m certvic.data.apply_visual_review --tasks ... --keep-list ... --out ... --summary-out ...`
- `python3 -m certvic.reporting.visual_review_report --summary ... --tasks ... --out-dir ...`

Baselines / ablations
- `python3 -m certvic.eval.run_ablations --tasks ... --out-dir ... --max-items 50`
- `python3 -m certvic.reporting.ablations --pred-dir ... --tasks ... --out-dir ...`

Certification / power
- `python3 -m certvic.metrics.power_plan --config configs/real_pilot_ade20k.yaml --out-dir ... --optional-stopping`

Inference readiness / eval
- `python3 -m certvic.eval.vlm_preflight --provider qwen2_5_vl_7b --config configs/tiny_reviewed_eval.yaml --tasks ... --out ... --check-gpu`
- `python3 -m certvic.eval.run_eval --config ... --tasks ... --out ... --provider qwen2_5_vl_7b --run-id ... --max-items 20 --evidence-run`

Reporting / gallery
- `python3 -m certvic.reporting.build_v2_report --scores ... --preds ... --tasks ... --out-dir ...`
- `python3 -m certvic.reporting.failure_gallery_v2 --tasks ... --preds ... --scores ... --out-dir ...`

Release
- `python3 -m certvic.release.build_artifact --config configs/release_recipe.yaml --out-dir release/certvic_recipe_artifact`
- `python3 -m certvic.release.data_card --manifests data/manifests --out release/DATA_CARD_GENERATED.md`

Orchestrators / gates
- `python3 -m certvic.pipeline.run_tiny_pilot --config configs/real_pilot_ade20k.yaml --ade20k-root <ROOT> --out-dir ... --dry-run`
- `python3 -m certvic.pipeline.run_tiny_eval --config configs/tiny_reviewed_eval.yaml --tasks ... --provider qwen2_5_vl_7b --out-dir ... --max-items 20`
- `python3 -m certvic.pipeline.pilot_gate_check --stage before_vlm --config configs/real_pilot_ade20k.yaml --out ...`
