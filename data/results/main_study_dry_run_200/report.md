# Main Study Dry Run — scale 200

Generated: 2026-06-23

Stages: 15 (3 GPU)  |  bottleneck: free_gpu_quota

**No GPU/VLM jobs executed. This is a plan only.**

## Stages

| # | Stage | GPU | Evidence status | Gate after |
| --- | --- | --- | --- | --- |
| 1 | ADE20K readiness (dry-run inspection) | no | READINESS_ONLY |  |
| 2 | Source + mask manifests | no | MANIFEST_ONLY |  |
| 3 | Label policy report | no | POLICY_ONLY |  |
| 4 | Pilot selection (target 200) | no | CANDIDATE_ONLY | before_edit_generation |
| 5 | Edit plan | no | PLANNED_ONLY |  |
| 6 | Diffusion job queue (shard + resume) | no | JOB_PLANNED_ONLY |  |
| 7 | Photorealistic edit generation (200) | yes | GENERATED_EDIT_ONLY |  |
| 8 | Edit quality report + detectability | no | QUALITY_ONLY | before_visual_review |
| 9 | Human review (batches + IAA + adjudicate) | no | HUMAN_REVIEWED_NON_EVIDENCE | before_vlm |
| 10 | Open-local VLM preflight | yes | PREFLIGHT_ONLY |  |
| 11 | VLM inference (matrix, 200, resumable) | yes | REAL_EVIDENCE |  |
| 12 | Scoring + power + triage | no | REAL_EVIDENCE | before_claims |
| 13 | Anytime-valid certification + cluster diagnostics | no | REAL_EVIDENCE |  |
| 14 | Paper report + result injection | no | REAL_EVIDENCE | before_release |
| 15 | Recipe-first artifact + privacy audit | no | RELEASE_RECIPE |  |

See stage_plan.json, commands.sh, gate_sequence.md, runtime_estimates.md,
required_inputs.md, and expected_outputs.md in this directory.
