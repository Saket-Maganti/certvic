# Codex Prompt 03 — Smoke Fixtures and Mock Provider

Build a complete no-GPU smoke pipeline with tiny generated images and a deterministic mock VLM provider.

## Goal

Before real datasets or real models, the repo must run end-to-end using local synthetic fixture images. This catches schema, runner, scoring, metrics, and reporting bugs without spending any compute.

## Files to create/update

```text
certvic/data/smoke_fixtures.py
certvic/providers/base.py
certvic/providers/mock.py
certvic/eval/prompts.py
certvic/eval/parse.py
certvic/eval/runner.py
certvic/metrics/consistency.py
tests/test_smoke_fixtures.py
tests/test_mock_provider.py
tests/test_eval_runner_smoke.py
tests/test_parse.py
```

## Smoke fixtures

Generate tiny PIL images locally:
- 64x64 or 128x128.
- Simple shapes only.
- No external downloads.
- Save under a temp directory or `data/smoke/` only when explicitly requested.

Create about 12 smoke task items:
- support_stability / change
- affordance_reachability / change
- control_irrelevant / no_change
- a few intentionally invalid examples only used in tests

Do not pretend these are evidence. Mark them:
```json
"split": "smoke"
"metadata": {"evidence_status": "MOCK_ONLY"}
```

## Provider interface

Create `certvic/providers/base.py`:

```python
class VLMProvider(Protocol):
    name: str
    provider_type: str
    model_name: str
    model_version: str

    def answer(self, image_path: str, prompt: str) -> str:
        ...
```

## Mock provider

Create a deterministic `MockProvider`.

Behavior:
- It should not inspect pixels.
- It can use item IDs or metadata only in tests if passed through a controlled mock mode.
- It should produce predictable outputs so the smoke pipeline has known scores.
- Include variants:
  - `perfect`: always answers expected labels.
  - `inconsistent`: high original accuracy but poor edit consistency.
  - `random`: seeded random yes/no.

Make sure mock provider is clearly labeled as not evidence.

## Prompt builder

In `certvic/eval/prompts.py`:
- Build neutral prompts.
- No prompt should include terms like “edited image”, “removed object”, “ground truth”.
- For yes/no:
  - “Answer with exactly one token: yes or no.”
- For multiple-choice:
  - “Answer with exactly one option letter.”

## Parser

In `certvic/eval/parse.py`:
- Parse yes/no robustly.
- Parse option letters.
- Return parsed answer + parse confidence + parse_ok.
- Refuse ambiguous long answers in strict mode.

## Runner

In `certvic/eval/runner.py`:
- Run original and edited image prompts.
- Append predictions to JSONL.
- Resume by `(run_id, item_id, image_variant)`.
- Flush after every prediction.
- Validate leakage before running.
- Support max_items.
- Support dry_run.

CLI entrypoint:
```bash
python -m certvic.eval.runner --config configs/smoke.yaml --out data/predictions/smoke_mock.jsonl
```

Use argparse.

## Scoring

In `certvic/metrics/consistency.py`:
- Convert original + edited predictions into PairScore records.
- Compute:
  - original accuracy
  - edited accuracy
  - consistency rate
  - intervention-consistency gap
  - parse failure rate

CLI entrypoint:
```bash
python -m certvic.metrics.consistency --tasks data/manifests/smoke_tasks.jsonl --preds data/predictions/smoke_mock.jsonl --out data/results/smoke_scores.json
```

## Tests

Add tests for:
- smoke task generation
- prompt leakage absence
- parser behavior
- mock provider deterministic behavior
- runner writes/resumes JSONL
- scoring computes expected consistency/gap

## Finish

Run:
```bash
python -m pytest -q
python -m certvic.eval.runner --config configs/smoke.yaml --out data/predictions/smoke_mock.jsonl
python -m certvic.metrics.consistency --tasks data/manifests/smoke_tasks.jsonl --preds data/predictions/smoke_mock.jsonl --out data/results/smoke_scores.json
```

Report:
- files changed
- tests run
- smoke results summary
- next prompt: `04_METRICS_CERTIFICATION.md`
