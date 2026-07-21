# Model Run Matrix (V3)

Plans future open-model evaluation runs as a matrix of **providers × prompt
variants × shards** over a task set, so free GPU sessions are not wasted on
re-running completed work. Planning only: no inference, no downloads, no GPU, no
paid providers.

## Modules

| Module | Purpose |
| --- | --- |
| `certvic.eval.model_matrix` | Build the matrix; memory estimates; resumable `run_eval` commands. |
| `certvic.eval.run_matrix_planner` | CLI: write `run_matrix.json`, `commands.sh`, report. |
| `certvic.eval.run_status` | Detect completed vs missing predictions; emit resume commands. |

## Cells

Each cell is one `(provider, prompt_variant, shard)` run with a stable `run_id`,
an expected predictions path (`<pred_root>/<provider>/<run_id>.jsonl`), the three
sidecars `run_eval` writes (`.run_manifest.json`, `.provider_metadata.json`,
`.environment.json`), a GPU memory estimate (full + 4-bit), and a resumable
command:

```bash
python3 -m certvic.eval.run_eval --config <config> --tasks <tasks> \
  --out <out> --provider <provider> --run-id <run_id> \
  --max-items <N> --shard-index <s> --num-shards <S> --evidence-run
```

Paid providers are rejected at build time; each provider is flagged for
evidence-eligibility (only non-mock open-local providers qualify).

## Commands

```bash
python3 -m certvic.eval.run_matrix_planner \
  --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl \
  --providers qwen2_5_vl_7b internvl_8b llava_onevision_7b \
  --out-dir data/results/model_run_matrix --max-items 200 --num-shards 4

python3 -m certvic.eval.run_status \
  --matrix data/results/model_run_matrix/run_matrix.json \
  --pred-root data/predictions \
  --out data/results/model_run_matrix/status.json
```

`run_status` marks a cell **completed** only when its predictions file is
non-empty **and** all sidecars are present; otherwise **missing**, with a resume
command emitted. This reduces wasted free-GPU inference sessions.
