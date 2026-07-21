# V2 Next Actions

Exact sequences once a real ADE20K root + free GPU are available.

## 0a. Pre-run gate (run first, no data/GPU needed)
```
python3 -m certvic.v2.pre_run_master_audit --out docs/V2_7_PRE_RUN_MASTER_AUDIT_REPORT.md --json-out data/results/pre_run_master_audit.json
```
Must report CLEARED. Optionally pass `--tasks <manifest>` to adversarially audit a
task set. Tighter (more powerful) certification: `pip install certvic[stats]`
(adds `confseq`); the native CS is valid but conservative without it.

## 0b. Supply unblockers
- Local ADE20K root with images/{training,validation} + annotations/{training,validation}.
- Free Kaggle/Colab GPU for diffusion edits + open-VLM inference.
- Before diffusion edits: `python3 -m certvic.edit.diffusion_preflight --edit-plan <plan.jsonl> --engine diffusers_inpaint_optional --weights-dir <local_weights> --check-gpu`

## 1. Tiny pilot (no inference)
```
python3 -m certvic.pipeline.run_tiny_pilot --config configs/real_pilot_ade20k.yaml --ade20k-root <ROOT> --out-dir data/results/tiny_real_pilot --max-items 20 --dry-run
python3 -m certvic.pipeline.run_tiny_pilot --config configs/real_pilot_ade20k.yaml --ade20k-root <ROOT> --out-dir data/results/tiny_real_pilot --max-items 20
```

## 2. 200 pilot (gate-checked)
Follow docs/MAIN_PILOT_200_RUNBOOK.md; run `pilot_gate_check` at each gate stage.

## 3. Open-local VLM eval
```
python3 -m certvic.eval.vlm_preflight --provider qwen2_5_vl_7b --config configs/tiny_reviewed_eval.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out data/results/vlm_preflight_qwen.json --check-gpu
python3 -m certvic.pipeline.run_tiny_eval --config configs/tiny_reviewed_eval.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --provider qwen2_5_vl_7b --out-dir data/results/tiny_eval_qwen --max-items 20
```

## 4. Certification
```
python3 -m certvic.metrics.power_plan --config configs/real_pilot_ade20k.yaml --out-dir data/results/power_plan --optional-stopping
```
Certified only if certification policy passes AND CS lower bound > threshold.

## 5. Paper update
```
python3 -m certvic.reporting.build_v2_report --scores data/results/tiny_eval_qwen/pair_scores.jsonl --preds data/results/tiny_eval_qwen/predictions.jsonl --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/results/v2_report
```
Paste generated tables/figures; keep [RESULT REQUIRED] until eligible.

## 6. Artifact release
```
python3 -m certvic.release.build_artifact --config configs/release_recipe.yaml --out-dir release/certvic_recipe_artifact
```

## 7. Final audit
```
python3 -m certvic.v2.full_audit --out docs/V2_FULL_SYSTEM_AUDIT_REPORT.md
```

## Scale & budget planning (V3)

Before committing to a study size, estimate the GPU/human/storage budget under
free-tier limits (conservative):

```bash
python3 -m certvic.planning.scale_planner --scale 200  --out data/results/scale_plan_200.md
python3 -m certvic.planning.scale_planner --scale 2000 --out data/results/scale_plan_2000.md
```

Reference: 2000 items ≈ 26 GPU-h (~0.87 weeks at 30 h/week), ~16.7 human-h
(~5.6 review-days), ~1.8 GB; bottleneck is the free GPU quota. See
`docs/SCALE_AND_BUDGET_PLAN.md`.

## When a run fails (V3)

Diagnose first, panic never:

```bash
python3 -m certvic.playbooks.diagnose_failure --report-dir data/results/tiny_real_pilot --out docs/playbooks/DIAGNOSIS.md
```

See `docs/playbooks/README.md`.

## V3 complete — stop building, start running

The V3 final pre-real-run audit is green (13/13):

```bash
python3 -m certvic.v3.final_pre_real_run_audit
```

Per the V3 stop rule, the remaining work is empirical, not code. Provide a local
ADE20K root + free GPU and follow `docs/V3_STOP_BUILDING_START_RUNNING.md`. All V3
commands are indexed in `docs/V3_COMMAND_INDEX.md`.
