# Codex Prompt 02 — Schemas, Validators, and Leakage Guards

Implement the core data schemas and validation logic.

## Goal

Create strong Pydantic schemas for all CertVIC artifacts:
- source image records
- masks
- edit specs
- task items
- prompts
- predictions
- scored predictions
- run manifests
- claim ledger entries

These schemas are the backbone of the project. Everything else should depend on them.

## Files to create

```text
certvic/schema/base.py
certvic/schema/source.py
certvic/schema/edit.py
certvic/schema/task.py
certvic/schema/prediction.py
certvic/schema/manifest.py
certvic/schema/claims.py
certvic/schema/__init__.py
certvic/validation/leakage.py
certvic/validation/schema_checks.py
tests/test_schema_source.py
tests/test_schema_task.py
tests/test_schema_prediction.py
tests/test_leakage_guards.py
```

## Required enums

Implement enums or Literal fields for:

Task families:
- `support_stability`
- `occlusion_safety`
- `affordance_reachability`
- `control_irrelevant`

Domains:
- `household`
- `driving`
- `synthetic_sanity`

Edit types:
- `remove`
- `occlude`
- `displace`
- `control_color`
- `control_texture`
- `none`

Required change:
- `change`
- `no_change`

Answer format:
- `yes_no`
- `multiple_choice`
- `short_action`

License category:
- `cc0`
- `public_domain`
- `cc_by`
- `research_only`
- `pointer_only`
- `unknown`

Provider type:
- `mock`
- `open_local`
- `free_tier_reference`

## SourceImageRecord

Fields:
- `source_id: str`
- `source_name: str`
- `source_url_or_pointer: str | None`
- `local_path: str | None`
- `sha256: str | None`
- `license_category`
- `license_text: str | None`
- `redistribution_allowed: bool`
- `notes: str | None`

Rules:
- If `redistribution_allowed=False`, local pixels should not be assumed releasable.
- `unknown` license should trigger warning-level validation failure for real runs.

## MaskRecord

Fields:
- `mask_id`
- `source_id`
- `mask_path`
- `object_label`
- `bbox_xyxy`
- `mask_sha256`
- `method`
- `quality_notes`

Validate bbox length 4 and nonnegative.

## EditSpec

Fields:
- `edit_id`
- `source_id`
- `mask_id`
- `edit_type`
- `task_family`
- `domain`
- `seed`
- `params: dict`
- `expected_effect: str`
- `single_factor: bool`
- `edited_image_path: str | None`
- `edited_sha256: str | None`

Rules:
- `single_factor` must be true for non-control main items.
- `edit_type=none` allowed only for smoke/mock/control use.

## TaskItem

Fields:
- `item_id`
- `source: SourceImageRecord`
- `mask: MaskRecord | None`
- `edit: EditSpec`
- `original_image_path`
- `edited_image_path`
- `question_original`
- `question_edited`
- `answer_original`
- `answer_edited`
- `required_change`
- `answer_format`
- `task_family`
- `domain`
- `split`
- `metadata`

Rules:
- If required_change is `change`, answer_original and answer_edited should differ.
- If required_change is `no_change`, they should be same unless task metadata explicitly defines a safety invariant.
- Prompt text must not leak edit type or answer.
- Filenames used in prompt must not include labels like “removed”, “falls”, “unsafe”, etc.

## PredictionRecord

Fields:
- `run_id`
- `item_id`
- `provider_name`
- `provider_type`
- `model_name`
- `model_version`
- `image_variant`: original or edited
- `prompt`
- `raw_output`
- `parsed_answer`
- `parse_confidence`
- `latency_s`
- `timestamp_utc`
- `metadata`

## PairScore

Fields:
- `run_id`
- `item_id`
- `provider_name`
- `model_name`
- `original_correct: bool`
- `edited_correct: bool`
- `consistent: bool`
- `required_change`
- `parse_ok: bool`
- `notes`

## Leakage guard

In `certvic/validation/leakage.py`, implement:

```python
FORBIDDEN_PROMPT_TERMS = [...]
FORBIDDEN_FILENAME_TERMS = [...]
def check_prompt_no_leakage(prompt: str, answers: list[str] | None = None) -> list[str]
def check_path_no_leakage(path: str) -> list[str]
def validate_task_no_leakage(task: TaskItem) -> list[str]
```

Forbidden terms should include obvious leakage words:
- removed
- occluded
- displaced
- edited
- changed
- unsupported
- fall
- falls
- safe
- unsafe
- answer
- label
- ground_truth

But do not overblock normal question words unless they reveal labels. Make warnings configurable.

## Schema read/write helpers

In `certvic/io.py`, implement:
- `read_json`
- `write_json`
- `read_jsonl`
- `write_jsonl`
- `append_jsonl`
- Pydantic model load/save helpers.

## Tests

Create tests for:
- valid source record
- invalid bbox
- required_change consistency
- leakage detection in prompt
- leakage detection in filename
- prediction record creation
- PairScore creation
- schema JSON roundtrip

## Finish

Run:
```bash
python -m pytest -q
```

Report files changed, tests run, and next prompt:
`03_SMOKE_FIXTURES_AND_MOCK_PROVIDER.md`
