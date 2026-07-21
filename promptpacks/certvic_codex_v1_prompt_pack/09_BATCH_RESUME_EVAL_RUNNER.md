# Codex Prompt 09 — Batch/Resume Evaluation Runner

Harden the evaluation runner for Kaggle’s 12-hour cap and free compute constraints.

## Goal

Build a robust runner that:
- reads task manifests
- runs provider on original and edited images
- writes prediction JSONL incrementally
- resumes safely
- validates leakage
- supports max_items and sharding
- survives interrupted sessions

## Files to create/update

```text
certvic/eval/runner.py
certvic/eval/run_eval.py
certvic/eval/resume.py
certvic/eval/sharding.py
certvic/eval/parse.py
tests/test_resume.py
tests/test_sharding.py
tests/test_runner_resume.py
tests/test_runner_cli.py
docs/REPRO.md
notebooks/kaggle/04_run_open_vlms.md
```

## Required CLI

Implement:
```bash
python -m certvic.eval.run_eval \
  --config configs/smoke.yaml \
  --tasks data/manifests/smoke_tasks.jsonl \
  --out data/predictions/smoke_mock.jsonl \
  --provider mock_inconsistent \
  --run-id smoke_mock_v1 \
  --max-items 10
```

Options:
- `--config`
- `--tasks`
- `--out`
- `--provider`
- `--run-id`
- `--max-items`
- `--shard-index`
- `--num-shards`
- `--dry-run`
- `--strict-leakage`
- `--overwrite` default false

## Resume logic

Completed key:
```python
(run_id, item_id, image_variant)
```

Never redo completed predictions unless `--overwrite`.

Append JSONL and flush after each prediction.

At startup:
- load existing predictions
- validate JSONL
- count completed
- print resume summary

## Sharding

Implement deterministic sharding by stable hash of item_id:
```python
assign item to shard if stable_hash(item_id) % num_shards == shard_index
```

This allows parallel Kaggle/Colab runs without overlap.

## Parsing

Runner should:
- save raw output
- parse answer
- record parse confidence
- record parse_ok
- never discard raw output

## Error handling

If one item fails:
- write an error prediction record with metadata error field
- continue unless `--fail-fast`

Do not crash entire 12-hour run for one bad image.

## Run metadata

At the start, write sidecar:
```text
<out>.run_manifest.json
```

Include:
- run_id
- provider
- config hash
- task manifest hash
- timestamp
- command args
- zero_cost_policy_ack=true
- paid_services_used=false

## Tests

Test:
- resume does not duplicate predictions
- overwrite works
- sharding has no overlap and complete union
- CLI smoke run produces original+edited predictions
- failed provider item records error and continues

## Kaggle doc

Create `notebooks/kaggle/04_run_open_vlms.md` with:
- Kaggle session tips
- cache weights
- resume command
- shard command
- storage warnings
- zero-cost warning

## Finish

Run:
```bash
python -m pytest -q
python -m certvic.data.build_tasks --smoke --out data/manifests/smoke_tasks.jsonl
python -m certvic.eval.run_eval --config configs/smoke.yaml --tasks data/manifests/smoke_tasks.jsonl --out data/predictions/smoke_mock.jsonl --provider mock_inconsistent --run-id smoke_mock_v1 --max-items 10
```

Report:
- files changed
- tests run
- prediction count
- next prompt: `10_SCORING_REPORTS_AND_FAILURE_GALLERY.md`
