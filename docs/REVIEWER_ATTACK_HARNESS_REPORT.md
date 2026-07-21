# Reviewer Attack Harness (V2.5)

Generated: 2026-06-22

Overall: **PASS** - 10/10 blocking defenses tooling-ready.

Each known reviewer attack is bound to a live, executable defense check.
`blocking` defenses must be ready before real runs; `enhancement` items are
tracked on the roadmap.

| Attack | Kind | Tooling ready | Evidence |
| --- | --- | --- | --- |
| The edits are fake / not photorealistic. | blocking | ready | quality gates + diffusion preflight + visual-review export are importable |
| This isn't about causal understanding. | blocking | ready | forbidden-phrase gate fires (2 errors on a causal overclaim) |
| The scale is too small. | blocking | ready | anytime-valid CS available at n=30 (method=certvic.anytime_cs.hoeffding_mixture) |
| Labels are ambiguous. | blocking | ready | ADE20K label policy module is importable |
| Licensing of released data. | blocking | ready | recipe-first release builder + zero-cost audit are importable |
| Only open models were tested. | blocking | ready | no paid providers registered (PAID_PROVIDER_NAMES=[]) |
| Optional stopping invalidates the statistics. | blocking | ready | validity lab: CS controls Type-I under peeking; peeked fixed-n inflates |
| The task is gameable without vision. | blocking | ready | adversarial audit + 8 construct-validity baselines available |
| Parser choices hide failures. | blocking | ready | summary exposes parser-sensitivity buckets |
| The reported numbers could be fabricated / hand-entered. | blocking | ready | paper number-provenance guard passes (0 violations) |
| You mined subgroups until one looked bad (multiple comparisons). | enhancement | ready | pre-registration declares a primary endpoint and a multiplicity policy |
| Items from the same source image are correlated; effective n is inflated. | enhancement | ready | clustering/independence policy documented (per-source aggregation diagnostic still on roadmap) |

Tooling-ready means the defense machinery runs today; it does not by itself
constitute empirical evidence. Post-run, each defense must also emit its
artifact (e.g. the construct-validity table, the certification trajectory).
