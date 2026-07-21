# V3 Prompt 06 — Cluster-Aware Certification Diagnostics Report

## Goal

Quantify sensitivity to clustered dependence (repeated source images, labels,
edit engines, prompts, domains) without replacing the primary anytime-valid CS.

## What was built

- `certvic/metrics/cluster_sensitivity.py` — `gap`, `icc_and_design_effect` (one-way ANOVA ICC → design effect → effective-n), `cluster_bootstrap_ci` (resamples whole clusters; descriptive), `leave_one_cluster_out` (per-cluster influence). All carry `is_certification=False`.
- `certvic/metrics/cluster_diagnostics.py` — best-effort cluster-key extraction (`source`, `label`, `engine`, `edit_type`, `task_family`, `domain`, `model`) enriched from the task manifest, per-dimension orchestration, worst-dimension-by-effective-n highlight, JSON + markdown report.

## Tests

`tests/test_v3_cluster_diagnostics.py` — 11 tests: gap math; high ICC when clusters are homogeneous; independent (design_effect=1) when one item per cluster; bootstrap CI is descriptive/not-certification and brackets the point; leave-one-cluster-out influence; full diagnostics positive path with discipline flags; single-cluster dimension skipped; cluster-key extraction with task enrichment; output writing + report content (asserts "NOT certification"); empty scores; no heavy imports.

## Verification

- `python3 -m pytest -q` — full suite green (318 passed; was 307).
- CLI smoke on 20 synthetic scores across 5 sources: dimensions analyzed, overall gap 0.5, worst dimension by effective-n reported, `is_certification: false`.

## Evidence / cost discipline

No GPU, no downloads, no paid services. Every diagnostic is explicitly marked
`is_certification=False` / `descriptive_only=True` / `replaces_anytime_valid_cs=False`;
`evidence_claims_made=false`. No heavy imports. This preempts dependence/p-hacking
attacks while keeping the anytime-valid CS as the sole certification path.

## Status

**PASSED.**

## Remaining blockers

None. Cluster keys for `engine`/`label` are best-effort from metadata; once real
runs record engine and label fields in the score metadata, those dimensions
become precise automatically.
