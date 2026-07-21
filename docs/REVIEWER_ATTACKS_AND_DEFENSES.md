# Reviewer Attacks and Defenses

Anticipated reviewer objections and how CertVIC answers them. Each row is now
bound to a *live, executable* defense check by the reviewer attack harness
(`python3 -m certvic.v2.reviewer_attack_harness`); see also
`docs/STATISTICAL_VALIDITY.md` and `docs/PRE_REGISTRATION.md`.

| Attack | Defense |
| --- | --- |
| "The edits are fake / not photorealistic." | Edit-quality gates (mask area, inside/outside change, allowed regions, degenerate-edit and duplicate detectors) plus human review of photorealism and single-factor validity; crude (CPU) and photorealistic (diffusion) engines are explicitly separated; only reviewed items become tasks. |
| "This isn't about causal understanding." | We make no causal-understanding claim. We measure decision consistency under a controlled intervention; forbidden phrases are blocked by the claim gate. |
| "The scale is too small." | Anytime-valid CS gives a valid certified lower bound at small n; a power analysis justifies the chosen n and reports the minimum detectable gap. We scale n where the budget allows and report honest null results otherwise. |
| "Labels are ambiguous." | An ADE20K label policy restricts eligible families/edits per label; unverified labels are limited to control edits; background "stuff" is blocked. |
| "Licensing of released data." | Recipe-first release: pointers, hashes, and scripts only; no non-rehostable pixels; release audit verifies no private paths or forbidden pixels. |
| "Only open models were tested." | Open-local models are a deliberate, reproducible, zero-cost choice; any frontier reference is non-core, version-dated, and disabled by default; we scope generalization claims accordingly. |
| "Optional stopping invalidates the statistics." | The CS is time-uniform; `certvic/sim/anytime_validity.py` empirically demonstrates Type-I control (~0.001 at alpha=0.05) under continuous peeking, while a peeked fixed-n CI inflates to ~0.67 and a no-peek fixed-n CI sits at ~alpha. Bootstrap/normal CIs are descriptive only. |
| "The numbers might be fabricated or hand-entered." | The paper number-provenance guard (`certvic/validation/paper_numbers_guard.py`) forbids untraced numbers in result prose; results enter only via `\input` of generated tables traced to eligible (non-mock/non-simulated) runs. |
| "You mined subgroups until one looked bad." | `docs/PRE_REGISTRATION.md` fixes a single primary endpoint; all subgroup analyses are exploratory or Bonferroni-corrected across the K simultaneous subgroup CS claims. |
| "Items from one source image are correlated; effective n is inflated." | The pre-registration caps confirmatory items per source and reports a per-source cluster-aggregated sensitivity analysis; a dedicated cluster CS is tracked as a roadmap enhancement. |
| "The task is gameable without vision." | Construct-validity baselines (text-only, caption-only, single-image, answer-prior, prompt-shuffle) and control edits show non-visual baselines achieve low consistency; a flag fires if any non-visual baseline exceeds the threshold. |
| "Dataset contribution is weak." | The contribution is a certified, recipe-first evaluation \emph{protocol} with edit-validity and construct-validity gates, not a static benchmark; the artifact is reproducible end to end. |
| "Parser choices hide failures." | Parser sensitivity reports strict vs lenient with explicit ambiguous/recovered/fail buckets and both parse-failure policies; failures are never hidden. |

## Simulated reviews and rebuttal prep (V3)

Beyond the live defense harness, V3 adds a reviewer *simulation* that drafts six
harsh reviews from the current artifacts and a rebuttal pack:

```bash
python3 -m certvic.review.simulate_reviews --paper-dir paper --reports-root data/results --out-dir docs/reviewer_simulation
python3 -m certvic.review.rebuttal_pack --reviews docs/reviewer_simulation/reviews.json --out docs/rebuttal_pack.md
```

When results are missing, the simulated reviewers complain and reject rather than
hallucinate; the rebuttal pack tags such points `blocked_on_results` (answerable
only by a real run, never by fabrication). See `docs/REBUTTAL_PREP.md`.
