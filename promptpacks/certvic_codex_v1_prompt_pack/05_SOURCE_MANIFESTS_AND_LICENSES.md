# Codex Prompt 05 — Source Manifests, License Tracking, and Recipe-First Data Policy

Implement source manifest tooling and license-aware dataset handling.

## Goal

CertVIC must avoid licensing mistakes. Build tooling that treats data as recipe-first:
- source pointers
- hashes
- license metadata
- redistribution flags
- no rehosting unless safe

## Files to create/update

```text
certvic/data/source_manifest.py
certvic/data/license_policy.py
certvic/hashing.py
certvic/data/build_source_manifest.py
tests/test_source_manifest.py
tests/test_license_policy.py
docs/DATA_CARD.md
docs/REPRO.md
data/sources/README.md
```

## Hashing

In `certvic/hashing.py`, implement:
- `sha256_file(path)`
- `sha256_bytes(data)`
- `stable_json_dumps(obj)`
- `stable_record_hash(obj)`

Stable hashes must sort keys and avoid nondeterministic formatting.

## License policy

Implement:
```python
def can_rehost_pixels(license_category: str, redistribution_allowed: bool) -> bool:
    ...
def release_mode_for_source(record: SourceImageRecord) -> str:
    ...
def validate_license_for_split(record: SourceImageRecord, split: str) -> list[str]:
    ...
```

Release modes:
- `pixel_release_ok`
- `recipe_only`
- `blocked_until_verified`

Rules:
- CC0/public_domain with redistribution_allowed true -> pixel_release_ok.
- CC_BY may be pixel_release_ok only with attribution metadata present; otherwise recipe_only.
- research_only/pointer_only -> recipe_only.
- unknown -> blocked_until_verified for pilot/main, allowed only in smoke with warning.

## Source manifest builder

Create CLI:
```bash
python -m certvic.data.build_source_manifest \
  --input data/sources/source_records.jsonl \
  --out data/manifests/source_manifest.jsonl \
  --split pilot
```

It should:
- load SourceImageRecord JSONL
- compute hashes if local_path exists
- validate license
- attach release mode
- write manifest JSONL
- emit summary counts by license/release mode

## Starter source templates

Add example templates, not actual dataset downloads:
```text
data/sources/source_records.example.jsonl
data/sources/README.md
```

Include sample records for:
- CC0/public domain placeholder
- ADE20K pointer-only placeholder
- COCO pointer-only placeholder
- BDD100K/nuScenes pointer-only placeholder

Make clear these are templates, not verified final records.

## Data card

Update `docs/DATA_CARD.md`:
- recipe-first artifact
- source pointer + hash strategy
- release modes
- license verification checklist
- redistribution policy
- no paid datasets

## Tests

Test:
- hash deterministic
- CC0 release allowed
- unknown license blocked for real split
- pointer-only becomes recipe-only
- manifest builder writes expected fields

## Finish

Run:
```bash
python -m pytest -q
python -m certvic.data.build_source_manifest --input data/sources/source_records.example.jsonl --out data/manifests/source_manifest_example.jsonl --split smoke
```

Report:
- files changed
- tests run
- manifest summary
- next prompt: `06_EDIT_PIPELINE_STUBS_AND_QUALITY_GATES.md`
