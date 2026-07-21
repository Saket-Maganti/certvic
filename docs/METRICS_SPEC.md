# Metrics Specification

For item `i`:

- `a_i = 1` when the original-image prediction is correct.
- `C_i = 1` when the original/edited prediction pair respects
  `required_change`.
- Consistency rate: `p = mean(C_i)`.
- Observational original accuracy: `a = mean(a_i)`.
- Intervention-consistency gap: `Delta = a - p`.

For `no_change` control items, consistency means the answer should remain stable.
Spurious flip rate is reported separately as the fraction of `no_change` items
where the parsed answer changes.

Paired bootstrap intervals resample item-level pairs. Anytime-valid confidence
sequences require the optional `confseq` dependency. If unavailable, CertVIC
marks certification unavailable rather than substituting a normal confidence
interval.

Construct-validity baselines include random, majority, text-only, caption-only
stubs, control edits, and original-only recognition accuracy.

## Construct-validity baselines and parser/prompt sensitivity (V2)

Baselines reproduce the main scoring rule (a_i = original correct; C_i = pair
respects required_change) so non-visual and single-image baselines can be shown
to achieve low consistency. original_only / edited_only cannot detect the change
and therefore fail change items by construction. Parser sensitivity reports
strict vs lenient parsing with explicit ambiguous/recovered/fail buckets and the
parse-failure-as-wrong vs excluded policies; failures are never hidden. Prompt
sensitivity covers canonical/terse/yes-no-strict/multiple-choice/
rationale-forbidden/leakage-stress variants.

## Power, optional stopping, certification policy (V2)

estimate_n_for_gap / minimum_detectable_gap_grid give normal-approximation
planning sizes on the bounded transform d=(a-C+1)/2 (variance <= 0.25); these are
planning only. simulate_optional_stopping shows the anytime-valid CS controls
Type-I error under continuous peeking, unlike fixed-n tests. evaluate_certification_policy
(configs/certification_policy.yaml) is the gate: it requires sufficient overall and
per-family n, bounded parse-failure and control spurious-flip rates, a reviewed
evidence status, an allowed (non-mock, non-baseline) provider type, and a CS lower
bound above the gap threshold.

## Simulation stress metrics (V2.1)

The simulation lab creates `SIMULATED_ONLY` task, prediction, and pair-score
records to stress the same descriptive metrics before real runs. The scenario
matrix reports original accuracy, consistency, intervention-consistency gap,
parse-failure rate, control spurious-flip rate, CS/certification status, and
whether claim gates blocked simulated artifacts.

These metrics are engineering diagnostics only. They can reveal implementation
bugs or weak assumptions in scoring/reporting/certification logic, but they
cannot validate data quality, edit validity, VLM behavior, or paper claims.

## Cluster-dependence diagnostics (V3)

CertVIC items share sources, labels, and edit engines, so they are not i.i.d.
`certvic.metrics.cluster_diagnostics` quantifies the gap's sensitivity to this
clustered dependence:

- **ICC / design effect / effective-n** — `n_eff = n / (1 + (mean_cluster_size − 1)·ICC)`.
- **Cluster bootstrap CI** — percentile interval for `Delta` resampling whole clusters.
- **Leave-one-cluster-out influence** — gap change when each source/label is removed.

All three are **descriptive only and are NOT anytime-valid certification.** The
certified gap claim comes solely from the anytime-valid CS; these diagnostics are
reported alongside it to show robustness. See
`docs/CLUSTER_DEPENDENCE_DIAGNOSTICS.md`.

## Model output / parse triage (V3)

Before trusting consistency scores, `certvic.eval.output_triage` triages raw VLM
outputs per provider: parse-ok rate, refusal rate, output length/latency, unique
raw count, top-repeat fraction, and mode answer. It flags `high_parse_failure`,
`answer_prior` (mode collapse), `degenerate_repeat` (broken decoding), and
`high_refusal`. These are descriptive run-quality diagnostics, not evidence; a
flagged provider's gap must not be reported until the output issue is fixed. See
`docs/MODEL_OUTPUT_TRIAGE.md`.
