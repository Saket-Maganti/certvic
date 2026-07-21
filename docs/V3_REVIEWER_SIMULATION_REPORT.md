# V3 Prompt 14 — Rebuttal and Reviewer Simulation Report

## Goal

Generate harsh simulated reviews and rebuttal prep from current artifacts,
complaining honestly about missing results when absent.

## What was built

- `certvic/review/simulate_reviews.py` — `assess_state` (placeholders remaining, certified-claim presence, defense infrastructure) + six reviewer profiles (benchmark skeptic, stats, vision/editing, reproducibility, construct-validity, open-model-scope). When results are missing, every reviewer complains and rejects; `hallucinated_results` is always false. Emits `reviews.json` + `reviews.md`.
- `certvic/review/rebuttal_pack.py` — keyword→defense map with `addressable_now` vs `blocked_on_results` status; lists blocked-on-results points explicitly; `fabricated_results` always false. Emits `rebuttal_pack.md`.

## Tests

`tests/test_v3_reviewer_simulation.py` — 7 tests: six profiles present; complains when no results + never hallucinates + low mean score; scores improve when results present; output writing; rebuttal marks blocked-on-results; rebuttal maps the stats defense (anytime-valid); no heavy imports.

## Verification

- `python3 -m pytest -q` — full suite green (386 passed; was 379).
- CLI smoke against the real paper (no results yet): mean score 2.0/5, all six reviewers complain about missing results, zero hallucinated results; rebuttal pack over 24 points marks 6 as honestly blocked on a real run, 0 fabricated.

## Evidence / cost discipline

No inference, no downloads, no paid services. The simulation never invents results
(`any_hallucinated_results=false`); the rebuttal never fabricates
(`fabricated_results=false`). `evidence_claims_made=false`. No heavy imports.

## Status

**PASSED.**

## Remaining blockers

The dominant simulated objection — "no empirical results" — is correctly
unrebuttable until a real open-VLM run exists. That is the next real step, not
more infrastructure.
