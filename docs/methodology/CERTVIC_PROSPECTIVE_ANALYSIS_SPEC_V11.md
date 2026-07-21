# CertVIC Prospective Analysis Specification V11

Status: `DEPRECATED_NOT_FOR_EXECUTION`  
Effective date: 2026-07-11  
Machine-readable lock: `configs/certvic_v11_protocol.yaml`

This is a historical V11 record only. It is superseded by
`configs/studies/specificity_confirmatory_cvpr.yaml` and
`configs/studies/certvic_confirmatory_authority.json`. Its gap endpoint and prospective execution
order do not authorize current confirmatory execution. Historical observations remain immutable.

This specification preserves every historical V1 decision and governs only future
Spurious V2 and Main-500 work. It was written while all three Spurious V2 provider
outputs and real V2 human judgments were absent. Unknown future results are not filled
in here.

## 1. Evidence boundary

The model prediction files already present for the 91-item intervention pilot and the
94-item V1 spurious control are real observed outputs. Their derived point estimates and
confidence-sequence trajectories are reproducible. The item-validity review used to form
the 91-item pilot was performed by `assistant_visual_review_v1`; the independent second
rater sheet remains blank. V11 therefore classifies those validity judgments as
`MACHINE_ASSISTED_PRELIMINARY`, not human review. Numerical CS threshold crossings must
not be described as a fully evidence-eligible scientific certificate until the human and
policy gates pass.

The 30-item Spurious V2 set, its images, notebooks, and blank annotation templates are
`DIAGNOSTIC_ONLY` or `HUMAN_REVIEW_PENDING`. They are not new model evidence. All 30
underlying items come from the 94-item V1 pool. Four of the twelve known Qwen failures are
retained and eight are filtered out by rules developed after V1. This set is therefore a
retrospective stricter-control sensitivity set, not an independent confirmatory sample.

## 2. Estimands

For eligible item \(i\):

- \(A_i=1\) when the parsed original-image response equals the locked original answer;
  otherwise \(A_i=0\).
- \(C_i=1\) when a parse-valid response pair changes when the locked intervention
  requires a change, or remains unchanged when the locked control requires no change;
  otherwise \(C_i=0\). This historical consistency indicator does not itself require
  that the edited response equals the edited gold answer.
- \(U_i=1\) when both original and edited responses equal their respective locked gold
  answers. For a change item this is a correct semantic update, and it must be reported
  alongside \(C_i\).
- \(a=n^{-1}\sum_i A_i\) is original-image accuracy.
- \(p=n^{-1}\sum_i C_i\) is raw answer-change/invariance consistency. Despite the historical symbol
  \(p\), it is not a p-value.
- \(\Delta=n^{-1}\sum_i(A_i-C_i)=a-p\) is the descriptive intervention-consistency gap.
- For a no-change control, \(F_i=1-C_i\) and
  \(\hat f=n^{-1}\sum_i F_i\) is the spurious flip rate. Lower is better.
- Perception success is ordinary accuracy on the natural present/absent control, with
  present, absent, and combined denominators reported separately.
- Relevant-edit success is \(n^{-1}\sum_i U_i\), with original and edited accuracy also
  shown. A change from one wrong answer to another is never called a successful update.
- Polarity and mechanism outputs are diagnostics. They are not part of the confirmatory
  certification family unless a later version locks them prospectively.

The unit of analysis is an item pair, not an image row. Models evaluated on the same item
set are paired. An item may appear once per declared model and endpoint. Retries may
replace a failed infrastructure attempt only when the exact prompt, model revision,
preprocessing, and deterministic decoding settings are unchanged; every attempt remains
logged.

## 3. Missing data and parsing

The primary analysis is fail closed:

- A missing original or edited row, duplicate item/variant key, wrong provider, wrong run
  tag, unexpected item, or source-hash mismatch invalidates the import and creates no
  canonical output.
- A refusal, empty response, contradictory response, multiple answer, or otherwise
  unparseable pair counts as a failure for the primary endpoint and is reported in a
  separate parse-failure table.
- A diagnostic parser may preserve raw free-form text but cannot feed a certification
  endpoint through fail-open fallback behavior.
- Raw text, parsed answer, parser version, prompt, item ID, variant, provider, model
  revision, and source hash must remain traceable.

## 4. Historical V1 rule

The frozen V1 operational rule remains

```text
observed spurious flip rate <= 0.10
```

It is not retroactively replaced by an interval rule. Raw V1 results and any later
validity-filtered sensitivity analysis are reported side by side. An exclusion cannot
change the historical raw decision.

## 5. Confirmatory Spurious V2 rule

Qwen is the predeclared primary model because its V1 result motivated the follow-up. The
primary V2 endpoint is its item-paired spurious flip rate on a newly sourced independent
item set that contains no V1 item and whose rules are frozen before any provider output.
Let \(X\sim\mathrm{Binomial}(n,f)\) denote the number of primary failures after the
pre-result validity set is frozen. The confirmatory pass rule is:

```text
one-sided 95% Clopper-Pearson upper confidence bound for f <= 0.10
```

The historical observed-rate rule is also reported for continuity but cannot override the
confirmatory interval decision. A simultaneous statement covering the three declared
models requires a Bonferroni family at 0.05, using one-sided bounds at
\(\alpha=0.05/3\) for each model. Model-paired risk differences, exact McNemar tests, and
paired bootstrap intervals are exploratory unless a later amendment declares a smaller
family before unblinding.

The current reused \(n=30\) set is reported only as retrospective sensitivity and cannot
clear the confirmatory gate, regardless of its result. It is also underpowered for a
broad three-model upper-bound claim. At
one-sided alpha 0.05, even the primary-model rule effectively requires zero observed
failures; under alpha 0.05/3, zero failures at \(n=30\) still cannot put the upper bound
below 0.10. This is a design limitation, not a result.

## 6. Human validity review and exclusions

Human review must be completed before reviewers see V2 provider outcomes. At least two
independent raters use randomized anonymous item IDs. Required fields are target
unaffected, expected answer unchanged, perturbation acceptable, prompt unambiguous,
image answerable, retain/exclude, and confidence. Provider identity, provider outputs,
V1 failure status, and original file naming are hidden.

Every exclusion records the item ID, objective reason, reviewer or rule source,
timestamp, evidence reference, whether the criterion preceded outcome inspection, and
its effect on each model. Raw and validity-filtered analyses are both mandatory.
Disagreements are adjudicated by a third blinded rater or by a locked deterministic rule.
Agreement is reported per field using percent agreement and Cohen's kappa where defined;
no agreement number is created until real labels exist.

## 7. Confidence sequence for the intervention gap

For a predeclared order, the implementation transforms

\[
D_i=(A_i-C_i+1)/2\in[0,1],\qquad \Delta=2\mathbb{E}[D_i]-1.
\]

`certvic.metrics.anytime_cs.hoeffding_mixture` constructs a time-uniform bounded-mean
confidence sequence using a data-independent mixture scale chosen from the planned
horizon. Its lower bound is valid under optional stopping when the conditional-mean and
boundedness assumptions hold and the order/tuning rule are fixed before outcomes.
Exchangeability is not required for the martingale statement, but adaptive item
selection based on observed responses would invalidate the declared target population.

Crossing the numerical CS threshold is only one gate. Full claim eligibility additionally
requires the locked sample-size, parser, evidence-class, human-validity, specificity,
provenance, and multiplicity conditions. Bootstrap intervals are descriptive and never
substitute for the anytime-valid bound.

## 8. Main-500 endpoints and go/no-go

Main-500 is not authorized. If later opened, its primary endpoint is the paired
intervention gap for a locked, human-approved, outcome-blind sample. Specificity is a
co-primary safety/construct-validity gate. Secondary endpoints are declared edit-family
and object-category strata. Polarity, mechanism, failure taxonomy, and qualitative
examples remain diagnostic.

Main-500 can open only after:

1. real V2 labels are completed before outcome unblinding;
2. every declared V2 provider file passes the transactional importer;
3. the frozen V2 decision and model-dependent narrative branch are signed off;
4. objective quality and detectability gates pass;
5. exact model and processor revisions are pinned; and
6. the item-selection seed, strata, replacement policy, and analysis code are hash-locked.

A Qwen V2 failure does not mechanically forbid a scientifically useful Main-500 study.
It requires the paper to make model-dependent specificity the declared question and to
avoid a universal specificity claim. Any such branch must be selected by the rule above,
not improvised after examining Main-500 outputs.

## 9. Multiplicity and reporting

The confirmatory family is limited to the declared primary endpoint and, only if claimed,
the three-model joint specificity family. Per-stratum, prompt, mechanism, polarity,
domain, and failure-taxonomy analyses are exploratory and labeled accordingly. Exact
unadjusted and adjusted values are both reported with their family definition. No
correction is applied to a single predeclared primary Qwen endpoint merely because
diagnostics also exist.

## 10. Required execution order

The earlier order placed human review after provider execution. V11 changes that order to
reduce outcome-aware selection:

1. freeze hashes, model revisions, notebooks, parser, and importer;
2. complete blinded two-rater V2 review and freeze the raw/retained sets;
3. if useful, execute the current 30-item Qwen, InternVL, and LLaVA-OneVision notebooks
   as retrospective sensitivity only (Qwen first is operational, not statistical);
4. source an independent unseen control set and freeze its construction;
5. execute and import the independent set transactionally;
6. compute raw and pre-result validity-filtered decisions under the rules above;
7. select the already-declared narrative branch; and
8. rerun the Main-500 go/no-go gate.

No step promotes `paper_evidence` automatically.
