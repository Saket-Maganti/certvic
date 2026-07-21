# CertVIC Codex V3 Prompt 06 — Cluster-Aware Certification Diagnostics


## Global constraints

- Work in `/Users/saketmaganti/Projects/certVIC`.
- Do not initialize git, commit, or tag.
- Do not use paid APIs, paid cloud, paid datasets, paid annotation, paid credits, or paid tracking.
- Do not download large datasets or model weights.
- Do not run GPU jobs or VLM inference in tests.
- Do not fabricate results or insert fake paper numbers.
- Keep heavy dependencies optional and import-safe.
- Normal tests must run locally without GPU.
- Simulated/pre-run artifacts must be marked non-evidence and blocked from claims.
- Preserve backward compatibility and run `python3 -m pytest -q`.

## Goal

Quantify sensitivity to clustered dependence from repeated source images, labels, edit engines, prompts, or domains without replacing the primary anytime-valid CS.

## Inspect first

Certification, summary, schema task/prediction, claim gates.

## Build / modify

Create `certvic/metrics/cluster_diagnostics.py` and `cluster_sensitivity.py`. Compute source/label/engine clusters, effective-n heuristics, cluster bootstrap descriptive CI, leave-one-source-out, leave-one-label-out, influence summaries.

## CLI commands to add or verify

`python3 -m certvic.metrics.cluster_diagnostics --scores data/results/pair_scores.jsonl --tasks data/manifests/tasks.jsonl --out-dir data/results/cluster_diagnostics`

## Outputs / behavior

All cluster bootstrap outputs must be labeled descriptive only, not certification. Claim gates must not treat them as CS.

## Tests

Create or update:

`tests/test_v3_cluster_diagnostics.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/CLUSTER_DEPENDENCE_DIAGNOSTICS.md`, `docs/V3_CLUSTER_DIAGNOSTICS_REPORT.md`; update `docs/METRICS_SPEC.md`.

## Extra notes

This preempts dependence/p-hacking attacks.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
