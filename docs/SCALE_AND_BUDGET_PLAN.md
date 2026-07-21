# Scale & Free-Compute Budget Plan (V3)

Estimates the CPU / GPU / human / wall-clock / storage cost of a study at a given
scale under free Kaggle/Colab limits, names the bottleneck, and recommends
per-session batch sizes. Estimates are deliberately **conservative, not
optimistic**. Planning only: no inference, no downloads, no paid services.

## Modules

| Module | Purpose |
| --- | --- |
| `certvic.planning.free_compute_budget` | Free-tier envelopes + per-stage rate assumptions + wall-clock/batch helpers. |
| `certvic.planning.scale_planner` | Full per-scale GPU/CPU/human/storage estimate + bottleneck + report. |

## Assumptions (configurable)

Overgeneration 2.5× candidates/kept item; edit ~8 s/candidate (GPU); VLM ~3 s/image;
2 variants (original + edited); 3 models; 1.5× ablation multiplier; ~30 s/item
human review at 3 review-hours/day; Kaggle free GPU ~30 h/week, session ~11.5 h;
Colab session ~8 h. Storage reuses `certvic.storage.plan_storage`.

## Commands

```bash
python3 -m certvic.planning.scale_planner --scale 200  --out data/results/scale_plan_200.md  --json-out data/results/scale_plan_200.json
python3 -m certvic.planning.scale_planner --scale 2000 --out data/results/scale_plan_2000.md --json-out data/results/scale_plan_2000.json
```

Override any assumption, e.g. `--num-models 4 --vlm-seconds-per-item 5 --human-seconds-per-item 45`.

## Reference estimates (defaults)

| Scale | GPU-h | Wall-clock weeks (30 h/wk) | Human-h | Review days (3 h/day) | Storage | Bottleneck |
| --- | --- | --- | --- | --- | --- | --- |
| 200  | ~2.6  | ~0.1 | ~1.7  | ~0.6 | ~0.18 GB | free GPU quota |
| 2000 | ~26.1 | ~0.87 | ~16.7 | ~5.6 | ~1.8 GB | free GPU quota |

The bottleneck is whichever of free-GPU-quota / human-review / storage has the
largest calendar cost; storage overrides when the working set won't fit Kaggle.
Per-session batch sizes tell you how many items fit one free GPU session so a
study can be sharded across sessions/weeks. See `docs/SCALE_AND_BUDGET_PLAN.md`
alongside `docs/STORAGE_AND_PATH_POLICY.md` and `docs/FREE_COMPUTE_BUNDLES.md`.
