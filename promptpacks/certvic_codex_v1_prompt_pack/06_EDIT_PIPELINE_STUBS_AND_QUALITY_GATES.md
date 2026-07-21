# Codex Prompt 06 — Edit Pipeline Stubs and Quality Gates

Build the edit pipeline architecture with safe stubs first, then optional open-model hooks.

## Goal

Implement the pipeline for:
- mask handling
- remove edits
- occlude edits
- displace edits
- control edits
- quality gates

Do not require GPU or heavyweight model downloads for tests. Heavy open-model integrations must be optional.

## Files to create/update

```text
certvic/edit/masks.py
certvic/edit/inpaint.py
certvic/edit/occlude.py
certvic/edit/displace.py
certvic/edit/control.py
certvic/edit/quality_gates.py
certvic/edit/pipeline.py
certvic/edit/build_edits.py
tests/test_edit_masks.py
tests/test_edit_displace.py
tests/test_edit_quality_gates.py
tests/test_edit_pipeline_smoke.py
docs/REPRO.md
docs/RISK_REGISTER.md
```

## Mask utilities

Implement:
- load mask as binary PIL/numpy
- validate mask dimensions against image
- bbox from mask
- mask area fraction
- dilate/erode optional if cv2 available, otherwise pure numpy simple fallback

## Displace edit

Implement CPU-only deterministic displace:
- cut object region using mask
- inpaint hole with simple background fill/stub in smoke mode
- paste object at target offset
- save edited image
- return EditSpec

This is not paper-quality but supports pipeline testing.

## Occlude edit

Implement CPU-only occluder:
- place a neutral rectangle or simple object-like patch over masked area
- deterministic color/texture from seed
- smoke only
- return EditSpec

## Control edit

Implement irrelevant edit:
- mild color/texture change outside main object mask
- required_change=no_change
- used to measure spurious flips

## Inpainting hook

Create `certvic/edit/inpaint.py` with:
- an abstract/simple interface
- `SimpleFillInpainter` for smoke mode
- optional `DiffusersInpainter` class guarded by optional imports

Important:
- Do not import diffusers/torch at module import time.
- Import inside class initializer only.
- If unavailable, raise clear optional dependency error.
- No paid services.

Use open model names only in config examples, e.g.
- `stabilityai/stable-diffusion-2-inpainting`

## Quality gates

Implement:
```python
def outside_mask_change_fraction(original, edited, mask, threshold=0.05) -> float
def simple_artifact_score(original, edited, mask) -> dict
def pass_quality_gates(original, edited, mask, config) -> dict
```

Quality gate outputs:
- outside_mask_change_fraction
- mask_area_fraction
- image_size_ok
- changed_region_nonempty
- pass bool
- warnings list

Keep smoke tests deterministic.

## Pipeline

Implement:
```python
def build_edit_for_task(source_record, mask_record, task_family, edit_type, config) -> EditSpec:
    ...
```

CLI:
```bash
python -m certvic.edit.build_edits \
  --tasks data/manifests/smoke_tasks.jsonl \
  --out-dir data/edits/smoke \
  --out-manifest data/manifests/smoke_edits.jsonl \
  --mode smoke
```

For now, the CLI may operate on smoke tasks and local placeholder images.

## Tests

Test:
- mask bbox
- mask area
- displace output exists
- occlude output exists
- control edit expected no_change
- outside-mask quality gate catches global changes
- optional heavy imports do not break normal import

## Docs

Update:
- REPRO.md with smoke edit pipeline.
- RISK_REGISTER.md with edit realism risk and mitigation.

## Finish

Run:
```bash
python -m pytest -q
```

Report:
- files changed
- tests run
- next prompt: `07_TASK_GENERATION_AND_MANIFESTS.md`
