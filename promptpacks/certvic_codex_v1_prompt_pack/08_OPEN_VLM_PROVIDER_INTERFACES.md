# Codex Prompt 08 — Open VLM Provider Interfaces

Implement provider adapters for open local VLMs with safe optional imports.

## Goal

Add clean provider interfaces for open models while preserving zero-cost and smoke-test usability.

Core open-model targets:
- Qwen2.5-VL-7B-Instruct
- InternVL2 / current InternVL open checkpoint
- LLaVA-OneVision-7B
- optional Molmo/DeepSeek-VL placeholder

Do not force install or download these in normal tests.

## Files to create/update

```text
certvic/providers/base.py
certvic/providers/mock.py
certvic/providers/open_vlm.py
certvic/providers/qwen_vl.py
certvic/providers/internvl.py
certvic/providers/llava_onevision.py
certvic/providers/registry.py
certvic/providers/free_tier_reference.py
tests/test_provider_registry.py
tests/test_open_vlm_import_safety.py
docs/REPRO.md
docs/ZERO_COST_POLICY.md
configs/kaggle_open_vlm.yaml
```

## Base provider

Refine provider protocol/base class:
- `answer(image_path, prompt) -> str`
- metadata fields:
  - provider_name
  - provider_type
  - model_name
  - model_version
  - local_only
  - cost_policy

## Registry

Implement:
```python
def get_provider(name: str, config: dict) -> VLMProvider:
    ...
```

Supported:
- `mock_perfect`
- `mock_inconsistent`
- `mock_random`
- `qwen2_5_vl_7b`
- `internvl_8b`
- `llava_onevision_7b`
- `free_tier_reference_stub`

If optional dependencies missing, raise clear errors.

## Open VLM adapters

Implement skeletons that are realistic but import-safe:
- Do not import torch/transformers at top-level.
- Load model lazily.
- Support config options:
  - model_id
  - device
  - dtype
  - load_in_4bit
  - max_new_tokens
  - temperature=0.0
  - batch_size
- Deterministic generation where possible.

If exact model-specific chat templates are uncertain, implement clear TODO comments and conservative placeholders, but structure the adapter so it can be filled in.

Important:
- Do not use paid endpoints.
- Do not add OpenAI/Anthropic paid providers.
- Do not add default Gemini calls here.

## Free-tier reference stub

Create a stub class:
- disabled by default
- requires explicit config flag `enable_free_tier_reference: true`
- requires environment variable for API key
- emits warning that this is non-core, version-dated, and only allowed if free
- do not implement actual network call unless a free official SDK is already configured
- no tests should require internet/API key

## Kaggle config

Update `configs/kaggle_open_vlm.yaml`:
- provider
- model_id
- load_in_4bit
- batch_size
- resume true
- input manifest path
- output prediction JSONL
- max_items
- no paid services warning

## Tests

Test:
- registry returns mock providers
- open providers fail clearly when dependencies missing
- importing provider modules does not import torch if absent
- free-tier reference disabled by default
- no paid provider names exist in registry

## Finish

Run:
```bash
python -m pytest -q
```

Report:
- files changed
- tests run
- next prompt: `09_BATCH_RESUME_EVAL_RUNNER.md`
