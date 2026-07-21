# Codex Prompt 04 — Metrics, Bootstrap, and Anytime-Valid Certification

Implement the statistical core of CertVIC.

## Goal

Add metrics for consistency rates, intervention-consistency gaps, bootstrap confidence intervals, and anytime-valid confidence sequences.

This is the main methodological differentiator. Keep it clean, tested, and conservative.

## Files to create/update

```text
certvic/metrics/summary.py
certvic/metrics/bootstrap.py
certvic/metrics/confseq_wrappers.py
certvic/metrics/certification.py
certvic/metrics/report_metrics.py
tests/test_metrics_summary.py
tests/test_bootstrap.py
tests/test_confseq_wrappers.py
tests/test_certification.py
docs/METRICS_SPEC.md
docs/CLAIM_LEDGER.md
```

## Definitions

For item i:
- `a_i = 1` if the original-image prediction is correct.
- `C_i = 1` if the original/edited pair respects required_change.
- Consistency rate: `p = mean(C_i)`.
- Observational accuracy: `a = mean(a_i)`.
- Gap: `Delta = a - p`.

For control/no-change items:
- consistency still means respecting required_change.
- spurious flip rate should be separately calculated as the fraction of no_change items where answer changed.

## Summary metrics

Implement:
```python
def summarize_pair_scores(scores: list[PairScore]) -> dict:
    ...
```

Return:
- n
- original_accuracy
- edited_accuracy
- consistency_rate
- intervention_consistency_gap
- parse_failure_rate
- spurious_flip_rate
- by_task_family
- by_domain
- by_required_change

## Bootstrap

Implement paired bootstrap:
```python
def paired_bootstrap_ci(values, statistic_fn, n_boot=2000, alpha=0.05, seed=0):
    ...
```

For gap:
- resample item-level pairs, not individual predictions.
- return lower, upper, estimate.

Use numpy only. Keep tests fast with small n_boot.

## Confseq wrapper

Create `certvic/metrics/confseq_wrappers.py`.

Preferred:
- use `confseq.betting.betting_cs` for bounded means if installed.

Required behavior:
- If confseq is installed, compute CS.
- If not installed, raise a clear `MissingOptionalDependencyError` or return a structured “unavailable” result only when `allow_unavailable=True`.
- Never silently replace anytime-valid CS with a normal CI.
- Tests should monkeypatch or use fallback-safe behavior.

Functions:
```python
def bounded_mean_cs_01(x, alpha=0.05, breaks=1000, allow_unavailable=False) -> dict:
    ...
def consistency_cs(C, alpha=0.05, breaks=1000, allow_unavailable=False) -> dict:
    ...
def gap_cs(a, C, alpha=0.05, breaks=1000, allow_unavailable=False) -> dict:
    ...
```

Gap mapping:
- `D = (a_i - C_i + 1.0) / 2.0`
- Run CS on D in [0,1].
- Map back: `2*lo - 1`, `2*hi - 1`.

Return:
```python
{
  "available": true,
  "alpha": 0.05,
  "lo": [...],
  "hi": [...],
  "latest": {"lo": ..., "hi": ...},
  "method": "confseq.betting.betting_cs"
}
```

## Certification

Create:
```python
def certify_gap(a, C, delta_threshold=0.05, alpha=0.05, allow_unavailable=False) -> dict:
    ...
```

Certified if:
- CS is available
- latest lower bound > delta_threshold

Return:
- certified bool
- lower_bound
- upper_bound
- threshold
- alpha
- statement
- safe_claim string

Example safe claim:
“Under the configured item order and anytime-valid CS, the intervention-consistency gap lower bound exceeds 0.05 at alpha=0.05 for this run.”

Avoid overclaiming.

## Reporting CLI

Create:
```bash
python -m certvic.metrics.report_metrics --scores data/results/smoke_pair_scores.jsonl --out data/results/smoke_metrics.json --alpha 0.05 --gap-threshold 0.05
```

It should produce:
- metrics summary
- bootstrap CIs
- CS availability
- certification decision
- safe claim text
- claim ledger compatible JSON

## Docs

Update `METRICS_SPEC.md` with:
- definitions
- paired structure
- bootstrap
- anytime-valid CS
- optional stopping explanation
- what can/cannot be claimed

Update `CLAIM_LEDGER.md` with:
- claim templates
- certification requirement
- forbidden claim examples

## Tests

Add tests:
- perfect consistency gap = 0 if original acc = consistency
- inconsistent model has positive gap
- gap mapping range works
- bootstrap CI deterministic with seed
- certification only passes when lower bound > threshold
- confseq unavailable behavior is explicit

## Finish

Run:
```bash
python -m pytest -q
```

Report:
- files changed
- tests run
- next prompt: `05_SOURCE_MANIFESTS_AND_LICENSES.md`
