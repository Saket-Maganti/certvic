# CertVIC Statistical Validity

This documents the statistical core of CertVIC — the anytime-valid certification
of the intervention-consistency gap — and the empirical evidence that it does
what the paper claims. This is the contribution most exposed to a harsh reviewer,
so it is made concrete, runnable, and self-validating.

## The estimand

For item `i`: `a_i` (original-image correctness) and `C_i` (consistency under the
required change). The gap is `Delta = E[a_i] - E[C_i]`. We certify a lower bound
on `Delta` via a confidence sequence (CS) on the bounded transform
`d_i = (a_i - C_i + 1)/2 in [0, 1]`, whose mean is `(Delta + 1)/2`. A CS lower
bound on the mean maps linearly to a CS lower bound on `Delta`.

## Two CS backends (both anytime-valid)

`certvic/metrics/confseq_wrappers.py` selects a backend:

* **`confseq` betting CS** (`certvic[stats]`, preferred): the Waudby-Smith &
  Ramdas betting confidence sequence. Tightest / most powerful. Used automatically
  when installed.
* **native Hoeffding-mixture CS** (`certvic/metrics/anytime_cs.py`, always
  available): a Robbins normal/conjugate-mixture confidence sequence built on a
  Hoeffding supermartingale and Ville's inequality. Zero extra dependencies, so
  the method runs on any free CPU/Kaggle/Colab environment.

`backend="auto"` (the default) uses `confseq` if importable and otherwise falls
back to the native CS. This was a correctness fix: before it, with `confseq`
absent the entire certification path silently degraded to "CS unavailable", i.e.
the paper's central method did not run on the zero-cost environment it targets.

### Conservativeness

The native CS is **valid but conservative**: it is wider (less powerful) than the
betting CS, so it requires a larger gap or more items to certify. This is the safe
direction — it never over-certifies. For the strongest published bounds, install
`confseq`; the power plan (`certvic/metrics/power.py`) and the validity lab let
you size `n` for either backend. Example: at `n = 300`, a true gap of `0.5`
certifies under the native CS (lower bound `~0.29 > 0.05`), while a gap of `~0.2`
does not yet clear `tau = 0.05` and needs more items or the tighter backend.

## Empirical validation (the proof, not the promise)

`certvic/sim/anytime_validity.py` is a Monte-Carlo lab (tagged `SIMULATED_ONLY`;
it validates the *estimator*, never a VLM finding). It runs a "peeking analyst"
who checks after every item and certifies the first time the lower bound crosses
the threshold, under a boundary null (`true Delta = tau`):

```
python3 -m certvic.sim.anytime_validity --out-dir data/results/anytime_validity --n 400 --n-trials 3000
```

Representative result (`alpha = 0.05`, boundary null):

| quantity | anytime CS (peeking) | fixed-n CI (peeking) | fixed-n CI (no peek) |
| --- | ---: | ---: | ---: |
| P(ever falsely certify) | ~0.001 | ~0.67 | ~0.057 |

The anytime-valid CS holds false-certification at or below `alpha` under
continuous peeking; a fixed-n CI recomputed every step blows up to ~0.67, while
the same fixed-n CI with no peeking sits at ~`alpha`. This isolates optional
stopping as the cause and substantiates the reviewer-defense claim. The lab also
reports two-sided coverage (<= `alpha` miscoverage) and power at several gaps.

These verdicts are asserted in `tests/test_anytime_cs_validity.py`, so a
regression in the CS math fails CI rather than silently weakening the guarantee.

## Pre-registered analysis discipline

Validity of the *number* is necessary but not sufficient; the *analysis* must not
be gamed. See `docs/PRE_REGISTRATION.md` for the single primary endpoint, the
optional-stopping rule, the multiplicity policy for subgroup analyses, and the
clustering / per-source independence policy. The reviewer attack harness
(`certvic/v2/reviewer_attack_harness.py`) binds each of these to a live check.

## What this does NOT establish

The statistics are only as good as the construct. None of the above validates
edit photorealism, single-factor validity, label correctness, or that the
measured gap reflects perception rather than artifact reaction. Those are
addressed by the edit-quality gates, the diffusion pipeline, human review, the
prompt/task adversarial audit, and the construct-validity baselines — and they
remain the project's biggest scientific risk.
