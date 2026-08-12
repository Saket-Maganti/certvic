# CertVIC certificate definition (C12)

Status: frozen technical methodology for prospective implementation. This is not a results section
and does not assert that any model has earned a certificate.

## Units and endpoints

Let each frozen task pair contain an original image, an edited image, one fixed question, and
canonical expected answers. The relevant endpoint contains answer-changing interventions. The
irrelevant endpoint contains controlled edits for which the expected answer is invariant.

For model (m) and relevant item (i), define semantic-update success as one only when the
original response is parseable and correct, the edited response is parseable and correct, the gold
answer changes, and the model changes to the edited gold answer. For irrelevant item (j), define
specificity failure as one when the normalized model answer changes even though the gold answer is
unchanged.

Missing responses, abstentions, and parser failures count as relevant-endpoint failures and
irrelevant-endpoint flips in the fixed primary analysis. A validity-filtered analysis may also be
reported, but it is secondary and cannot replace the full frozen denominator.

## Per-model gates

The prospective v3 allocation is 120 relevant items and 240 irrelevant controls per model. The
scientific thresholds remain

\[
\tau_{update}=0.50,\qquad \tau_{spurious}=0.10.
\]

There are three frozen primary models and two gates per model. Bonferroni allocation of family
alpha 0.05 gives one-sided alpha (0.05/6) for each gate. Responsiveness passes only when the exact
one-sided Clopper–Pearson lower bound is strictly greater than 0.50. Specificity passes only when
the exact one-sided upper bound is at most 0.10. At the amended sample sizes, the critical values
are at least 74 relevant successes out of 120 and at most 13 irrelevant flips out of 240.

The interval construction is the inversion of exact binomial tail tests. Its fixed-sample coverage
property follows from that inversion; see Clopper and Pearson, “The Use of Confidence or Fiducial
Limits Illustrated in the Case of the Binomial,” *Biometrika* 26(4), 1934,
doi:10.1093/biomet/26.4.404. The guarantee assumes a fixed sample and the declared Bernoulli
endpoint. It does not make Clopper–Pearson intervals optional-stopping-valid.

## Certificates and claim regimes

A model-level certificate requires both of that model's gates to pass and also requires the exact
prospective task, review, detectability, permission, model-revision, parser, code, and result hashes.
A statistical pass without those artifacts is not a certificate.

The primary all-model claim uses `ALL_THREE_MODELS_MUST_JOINTLY_CERTIFY`: all six gates must pass.
Scoped `MODEL_LEVEL_CERTIFICATES_WITH_FAMILYWISE_ERROR_CONTROL` may be reported for individual
models under the same six-gate correction, but they must not be described as an all-model result.
Optional future models belong to `SECONDARY_MODEL_EXPANSION`; they never enter or alter the frozen
primary family retroactively.

## Responsiveness–specificity regimes

- `RESPONSIVE_AND_SPECIFIC`: responsiveness exceeds 0.50 and specificity failure is at most 0.10.
- `RESPONSIVE_BUT_SPURIOUS`: responsiveness exceeds 0.50 but specificity failure exceeds 0.10.
- `INERT_BUT_SPECIFIC`: responsiveness is at most 0.50 and specificity failure is at most 0.10.
- `INERT_AND_SPURIOUS`: responsiveness is at most 0.50 and specificity failure exceeds 0.10.

These coordinate labels describe endpoint rates. Only simultaneous exact bounds plus the evidence
gates produce a certificate.

## Confidence sequences

Confidence sequences are secondary operational diagnostics. They may support monitoring under
optional inspection, but they do not change the fixed primary sample, thresholds, critical counts,
or decision. Fixed-sample Clopper–Pearson bounds must never be repeatedly inspected and treated as
anytime-valid.

## Scope and integrity

The certificate is limited to the frozen domain, task construction, model and processor revisions,
prompt, parser, decoding policy, and reviewed item universe. It does not establish causal reasoning,
universal visual understanding, deployment safety, or cross-domain generalization.

Historical V1 and retrospective V2 results may motivate diagnostics but cannot satisfy prospective
claims. Candidate construction, matching, detectability, protocol amendment, and sample allocation
must not read prospective provider outcomes. Main-500 and a second domain require separate,
machine-readable authorization after their upstream gates pass.

Executable property tests cover exact critical counts, monotonicity of bounds and power, evidence
class separation, outcome-blind matching, and fail-closed missing-data behavior.
