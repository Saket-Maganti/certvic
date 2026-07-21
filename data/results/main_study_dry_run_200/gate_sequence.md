# Gate Sequence

Gates must pass in order; cross-cutting audits bracket the study.

| Gate | Checks | Command |
| --- | --- | --- |
| `pre_run_master_audit` | all systems green before any real work | `python3 -m certvic.v2.pre_run_master_audit` |
| `before_edit_generation` | selection meets target, label policy clean, sources eligible | `python3 -m certvic.pipeline.pilot_gate_check --stage before_edit_generation --config configs/real_pilot_ade20k.yaml` |
| `before_visual_review` | edits generated, quality gates pass, detectability acceptable | `python3 -m certvic.pipeline.pilot_gate_check --stage before_visual_review --config configs/real_pilot_ade20k.yaml` |
| `before_vlm` | reviewed tasks exist with adequate IAA; only reviewed items proceed | `python3 -m certvic.pipeline.pilot_gate_check --stage before_vlm --config configs/real_pilot_ade20k.yaml` |
| `before_claims` | real open-local predictions scored; no high parse failure / control flip | `python3 -m certvic.pipeline.pilot_gate_check --stage before_claims --config configs/real_pilot_ade20k.yaml` |
| `before_release` | certified or honest-null report; privacy audit clean; numbers traced | `python3 -m certvic.pipeline.pilot_gate_check --stage before_release --config configs/real_pilot_ade20k.yaml` |
| `security_privacy_audit` | no private paths / secrets / pixels leak | `python3 -m certvic.security.release_privacy_audit --root . --release-dir release/certvic_recipe_artifact --out docs/SECURITY_PRIVACY_AUDIT.md` |
| `final_pre_real_run_audit` | V3 final gate (built in prompt 19) | `python3 -m certvic.v3.final_pre_real_run_audit` |
