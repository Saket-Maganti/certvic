# Cluster-Dependence Diagnostics (V3)

CertVIC items are not perfectly independent: many edits share a source image, a
semantic label, an edit engine, a prompt, or a domain. A reviewer will ask
whether the gap survives that clustered dependence. These diagnostics quantify
the sensitivity **without replacing the primary anytime-valid CS**.

**Every output here is descriptive only and NOT certification.** The certified
result must still come from the anytime-valid confidence sequence; claim gates
must never treat a cluster bootstrap CI as a CS.

## Modules

| Module | Purpose |
| --- | --- |
| `certvic.metrics.cluster_sensitivity` | ICC / design effect / effective-n, cluster bootstrap CI, leave-one-cluster-out. |
| `certvic.metrics.cluster_diagnostics` | Extract cluster keys, run all diagnostics per dimension, render report. |

## Metric

`d_i = a_i - C_i ∈ {-1, 0, 1}` (`a_i` = original correct, `C_i` = consistent),
and `Delta = mean(d_i)` — the same gap the CS certifies.

## Dimensions

`source`, `label`, `engine`, `edit_type`, `task_family`, `domain`, `model`
(best-effort extraction from score metadata, enriched from the task manifest).
Dimensions with a single cluster are skipped.

## What it computes per dimension

- **ICC / design effect / effective-n** — one-way ANOVA intraclass correlation;
  `design_effect = 1 + (mean_cluster_size − 1)·ICC`; `n_eff = n / design_effect`.
  A small `n_eff` warns that the nominal item count overstates the evidence.
- **Cluster bootstrap CI** — percentile interval for `Delta` resampling whole
  clusters with replacement. Descriptive; wider than the i.i.d. bootstrap when
  dependence is real.
- **Leave-one-cluster-out influence** — how much removing one source/label moves
  `Delta`; large values flag a gap driven by a single cluster.

## Command

```bash
python3 -m certvic.metrics.cluster_diagnostics \
  --scores data/results/pair_scores.jsonl \
  --tasks data/manifests/tasks.jsonl \
  --out-dir data/results/cluster_diagnostics
```

Outputs `cluster_diagnostics.json` and `cluster_diagnostics_report.md`. The
summary reports `is_certification: false`, `descriptive_only: true`,
`replaces_anytime_valid_cs: false`.
