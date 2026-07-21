# Statistical Sensitivity & Sequential Design — Main Study

**PLAN, NOT A RESULT** (`evidence_status = STATISTICAL_PLAN_NON_EVIDENCE`). Built around `Delta = E[a_i - C_i]`, certified via the project's anytime-valid CS. Certification thresholds are unchanged (gap > 0.05, alpha = 0.05).

## Observed pilot effect sizes (measured)

| model | n | a | p | observed Δ | CS LB |
|---|---|---|---|---|---|
| Qwen/Qwen2.5-VL-7B-Instruct | 91 | 0.9231 | 0.1758 | 0.7473 | 0.364 |
| OpenGVLab/InternVL2-8B | 91 | 0.9231 | 0.0989 | 0.8242 | 0.4409 |
| llava-hf/llava-onevision-qwen2-7b-ov-hf | 91 | 0.8901 | 0.1758 | 0.7143 | 0.331 |

Observed Δ range: 0.7143–0.8242. These are **not** used as guaranteed future effect sizes.

## Conservative planning sample sizes (projections)

| conservative Δ | feasible | planning n (per model, normal approx) |
|---|---|---|
| 0.2 | True | 275 |
| 0.3 | True | 99 |
| 0.4 | True | 51 |

Planning estimates only (normal approximation); the anytime-valid CS may require more items. Even the most conservative Δ here is far below the observed pilot gap.

## Minimum detectable gap by n

| n | min detectable gap over threshold | implied gap |
|---|---|---|
| 91 | 0.2607 | 0.3107 |
| 200 | 0.1758 | 0.2258 |
| 500 | 0.1112 | 0.1612 |
| 800 | 0.0879 | 0.1379 |
| 1000 | 0.0786 | 0.1286 |
| 2000 | 0.0556 | 0.1056 |

## Optional-stopping (anytime-valid) plan

Item-level anytime-valid CS allows checking after every item without alpha inflation. Simulation: Type-I error under H0 (true gap=0) with peeking at every step should stay <= alpha.

| n | Type-I error under H0 (continuous peeking) | available |
|---|---|---|
| 200 | 0.0 | True |
| 500 | 0.0 | True |

A Type-I error at or below alpha while peeking at every item is the property that lets us stop as soon as the CS clears — without a fixed-n penalty.

## Reporting policies

- **multiple_model_reporting** — Report each model's OWN anytime-valid certified CS. Cross-model agreement is descriptive; do not pool models into a single certified claim. For a joint claim, pre-register a primary model or apply a multiplicity adjustment across the model family.
- **per_family_analysis** — Pre-register the task-family split (support_stability, affordance_reachability, occlusion_safety). Report per-family gaps descriptively; do NOT certify families with tiny n (e.g. occlusion n=6). Certification is at the pooled presence-arm level.
- **exclusion_sensitivity_for_review_uncertainty** — Define a sensitivity set = items with rater disagreement (IAA gate) OR residual_target_visible in {yes, uncertain}. Recompute the CS with that set dropped; report both. Items are not silently removed from the canonical set.
- **control_reporting** — Report the absent-object control and (when run) the spurious-flip specificity control as SEPARATE arms with their own status; a passed intervention gap is not evidence of specificity until the control passes.

## What NOT to certify

- tiny task families (n too small for a meaningful CS)
- a single pooled cross-model claim (models are reported individually)
- anything via a naive fixed-n confidence interval as the primary claim
- the affordance arm (original accuracy ~chance => confounded)
- any mock/smoke/simulated artifact
- specificity, until the spurious-flip control predictions exist and pass

## Conservative design recommendation

Plan the main study at a conservative Δ = 0.30 with item-level anytime-valid monitoring and an optional-stopping rule; report each model individually; pre-register the family split and the exclusion/sensitivity set; treat specificity as a separate gated arm.
