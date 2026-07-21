# Main Study Dry Run (V3)

Plans the full 200/1k/2k study **without executing any GPU/VLM jobs**. It composes
the staged pipeline, the gate sequence, runtime/storage estimates, required
inputs, and expected outputs into reviewable planning artifacts.

## Modules

| Module | Purpose |
| --- | --- |
| `certvic.pipeline.main_study_plan` | Ordered stage plan + gate sequence + runtime estimate (reuses the scale planner). |
| `certvic.pipeline.main_study_dry_run` | Writes the 7 planning artifacts; no execution. |

## Stages (15)

readiness → manifests → label policy → selection → edit plan → diffusion job
queue → edit generation (GPU) → quality + detectability → human review → VLM
preflight (GPU) → VLM inference (GPU) → scoring + triage → certification +
cluster diagnostics → paper report + injection → recipe-first release.

## Gate sequence

`pre_run_master_audit` → `before_edit_generation` → `before_visual_review` →
`before_vlm` → `before_claims` → `before_release` → `security_privacy_audit` →
`final_pre_real_run_audit`. Gates must pass in order; the two cross-cutting audits
bracket the whole study.

## Commands

```bash
python3 -m certvic.pipeline.main_study_dry_run --scale 200  --out-dir data/results/main_study_dry_run_200
python3 -m certvic.pipeline.main_study_dry_run --scale 2000 --out-dir data/results/main_study_dry_run_2000
```

Outputs per scale: `stage_plan.json`, `commands.sh` (with gates inlined after
gated stages), `required_inputs.md` (e.g. `<ADE20K_ROOT>`, `<WEIGHTS_DIR>`),
`expected_outputs.md`, `gate_sequence.md`, `runtime_estimates.md`, `report.md`.

Nothing runs: `executed=false`, `vlm_inference_run=false`,
`downloads_attempted=false`. Review the plan, provide the user inputs, then
execute stage by stage with the gates.
