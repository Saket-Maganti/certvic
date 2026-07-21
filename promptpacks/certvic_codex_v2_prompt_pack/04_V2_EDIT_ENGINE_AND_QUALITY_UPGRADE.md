# CertVIC Codex V2 Prompt 04 — Edit Engine and Quality Upgrade

Do not use paid services. Do not run VLM inference. Heavy dependencies must be optional. Do not make evidence claims.

## Goal

Upgrade edit generation from simple validation mode into a modular, replayable edit engine suitable for real pilot generation.

## Tasks

1. Add edit engine registry:
   - `certvic/edit/engines.py`

   Engines:
   - simple_fill
   - simple_occlude
   - simple_displace
   - simple_control
   - composite_occluder
   - diffusers_inpaint_optional
   - no_op_debug

2. Engine rules:
   - simple engines work locally in tests
   - heavy engines import lazily
   - no network downloads by default
   - no paid services

3. Add deterministic replay metadata:
   - generation_config_hash
   - source_image_sha256
   - mask_spec_hash
   - edit_plan_hash
   - seed
   - engine version
   - actual parameters

4. Improve mask extraction:
   - materialize binary mask from ADE20K annotation + label ID only when needed
   - cache masks with hashes
   - avoid writing full masks unless configured

5. Upgrade quality gates:
   - edit-type-specific thresholds
   - inside/outside mask change
   - destination-region handling for displace
   - image size preservation
   - blur/artifact indicators
   - all-black/all-white detection
   - duplicate edited image detection
   - changed-area ratio
   - control-edit destructiveness check

6. Add batch generation safety:
   - max_items required unless `--allow-full-run`
   - resume by edit_id
   - rejected file append/resume
   - fail-fast optional
   - no overwrite by default

7. Add config:
   - `configs/edit_quality.yaml`

8. Add tests:
   - `tests/test_v2_edit_engine_quality.py`

9. Update docs:
   - `docs/PILOT_ADE20K.md`
   - `docs/REPRO.md`
   - `docs/RISK_REGISTER.md`

10. Create:
   - `docs/V2_EDIT_ENGINE_QUALITY_REPORT.md`

11. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, commands added, whether edit-engine upgrade passed, and next prompt: `05_V2_OPEN_VLM_INFERENCE_READINESS.md`.
