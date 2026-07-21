# Main 200-Item Pilot Runbook

Run only after the tiny pilot succeeds and you have a local ADE20K root + free GPU.

## Stages (gate-checked)

1. Real ADE20K inspection — `certvic.data.pilot_readiness --dry-run`
2. Manifests — `certvic.data.ade20k_adapter`
3. Label policy report — `certvic.data.label_policy_report`
4. Selection (target 200) — `certvic.data.select_pilot_items --label-policy ... --per-family-target-json ...`
   - GATE: `pilot_gate_check --stage before_edit_generation`
5. Edit plan — `certvic.edit.plan_edits --label-policy ...`
6. Preview + plan report — `certvic.data.preview_tasks`, `certvic.reporting.pilot_plan_report`
7. Edit generation — `certvic.edit.engines --max-items 200`
8. Quality report — `certvic.edit.quality_report`
   - GATE: `pilot_gate_check --stage before_visual_review`
9. Visual review — export/gallery/aggregate/apply (`certvic.validation.*`, `certvic.data.apply_visual_review`)
   - GATE: `pilot_gate_check --stage before_vlm`
10. Open-local VLM preflight — `certvic.eval.vlm_preflight --check-gpu`
11. VLM inference — `certvic.pipeline.run_tiny_eval --provider qwen2_5_vl_7b` (or run_eval --evidence-run)
12. Scoring + power — `certvic.metrics.score_predictions`, `certvic.metrics.power_plan`
    - GATE: `pilot_gate_check --stage before_claims`
13. Certification — certification policy + anytime-valid CS
14. Paper report — `certvic.reporting.build_v2_report`
    - GATE: `pilot_gate_check --stage before_release`
15. Artifact release — `certvic.release.build_artifact`

## Targets

200 items balanced across families; min ~40/family for per-family certification
(see configs/certification_policy.yaml). Report honest null results if the gap is
not certifiable.

## Dry-run the full study first (V3)

Before running, generate the complete plan (stages, gates, runtime, inputs,
outputs) without executing anything:

```bash
python3 -m certvic.pipeline.main_study_dry_run --scale 200  --out-dir data/results/main_study_dry_run_200
python3 -m certvic.pipeline.main_study_dry_run --scale 2000 --out-dir data/results/main_study_dry_run_2000
```

The emitted `commands.sh` inlines each gate after its stage. See
`docs/MAIN_STUDY_DRY_RUN.md`.
