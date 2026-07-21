# Remaining GPU / CPU / human runtime estimates

These are conservative estimates, not results. No model outputs are produced by
building these runbooks.

## Timing anchors

- LLaVA-OneVision-7B on one Kaggle T4: 182 generations took 1689 seconds, about 0.10-0.11 generation/sec.
- 120 absent-control items = 240 generations.
- 91 intervention items = 182 generations.
- Spurious set: 94 pairs = 188 generations/model.
- Scaled perception: 369 pairs = 738 generations/model.
- Mechanism: 364 generations/model.
- Polarity: 728 generations/model.

## Per-provider estimates

| RUN_TAG | generations/model | Qwen single GPU | Qwen T4x2 | InternVL single/shared fallback | InternVL T4x2 | LLaVA single GPU | LLaVA T4x2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| spurious | 188 | ~10-20 min | ~5-12 min | ~15-30 min | ~8-20 min depending memory/load mode | ~30-45 min | ~15-30 min if true parallel; ~30-45 min if fallback |
| perception_scaled | 738 | ~30-60 min | ~15-30 min | ~40-90 min | ~20-45 min | ~2-2.5 hr | ~60-90 min if true parallel; ~2-2.5 hr if fallback |
| polarity | 728 | ~20-40 min | ~10-20 min | ~30-60 min | ~15-30 min | ~1-2 hr | ~45-75 min if true parallel; ~1-2 hr if fallback |
| mechanism | 364 | ~15-30 min | ~8-15 min | ~20-50 min | ~10-25 min | ~55 min | ~25-45 min if true parallel; ~55 min if fallback |

InternVL defaults to a safer shared T4x2 sequential mode if two model copies are
not memory-safe without bitsandbytes/triton.

## Main-scale estimates

| stage | compute | conservative estimate |
|---|---|---:|
| Main-500 planning | CPU | ~10-30 min |
| Main-500 diffusion | Kaggle GPU T4x2 | ~6-8 hr |
| Main-500 quality/detectability | CPU | ~15-60 min |
| Main-500 human review | human | ~20-25 hr |
| Main-500 VLM | Kaggle GPU | model-dependent; for projected 566 tasks, estimate from measured per-generation rates and the final reviewed count |

Main-scale remains gated. Do not run the diffusion template until the remaining
controls and go/no-go checks are satisfied.
