# Codex Prompt 15 — CI Tests, Audit Gates, and Pre-Run Checklist

Add project-wide audit gates so the repo cannot accidentally make unsafe claims or run invalid experiments.

## Goal

Create a full audit/check command that validates:
- zero-cost policy
- schema integrity
- leakage guards
- manifest hashes
- license modes
- prediction completeness
- metrics availability
- claim certification
- paper overclaim prevention

## Files to create/update

```text
certvic/audit.py
certvic/validation/zero_cost.py
certvic/validation/claims.py
certvic/validation/paper_claims.py
tests/test_zero_cost_audit.py
tests/test_claim_validation.py
tests/test_paper_claims.py
docs/REPRO.md
docs/CLAIM_LEDGER.md
README.md
```

## Audit CLI

Implement:
```bash
python -m certvic.audit \
  --config configs/smoke.yaml \
  --tasks data/manifests/smoke_tasks.jsonl \
  --preds data/predictions/smoke_mock.jsonl \
  --scores data/results/smoke_pair_scores.jsonl \
  --paper paper/main.tex \
  --strict
```

It should output:
```json
{
  "passed": true,
  "checks": {
    "zero_cost": ...,
    "schemas": ...,
    "leakage": ...,
    "licenses": ...,
    "metrics": ...,
    "claims": ...,
    "paper": ...
  }
}
```

## Zero-cost validation

Search config/docs/code for suspicious paid-service markers:
- openai
- anthropic
- paid
- billing
- stripe
- aws
- gcp
- azure
- runpod
- replicate
- together
- modal
- vast.ai
- lambda labs

Do not blindly fail on words inside ZERO_COST_POLICY.md where they are forbidden examples. Implement allowlist paths/contexts.

Fail if:
- config enables paid provider
- provider registry contains paid provider
- API endpoint is enabled by default
- docs recommend paid fallback

## Claim validation

Claims require:
- metric evidence
- certification status
- allowed wording
- limitations

Fail strict mode if:
- certified claim lacks CS lower bound
- overclaim words appear
- frontier reference is described as reproducible core

Forbidden phrases:
- “proves causal understanding”
- “VLMs cannot reason causally”
- “safe for autonomous driving”
- “unsafe for deployment”
- “frontier models fail”
- “all VLMs”

## Paper claim scanner

Scan paper text for:
- forbidden phrases
- fake numeric results near result placeholders
- missing limitations section
- missing zero-cost or reproducibility mention

## Pre-run checklist

Update README and REPRO with:
- before pilot
- before main
- before paper claim
- before release

## Tests

Test:
- audit passes on smoke artifacts
- audit catches enabled paid provider in fake config
- audit catches forbidden claim
- paper scanner catches bad phrase
- allowlist works for ZERO_COST_POLICY forbidden examples

## Finish

Run:
```bash
python -m pytest -q
python -m certvic.audit --config configs/smoke.yaml --strict
```

Report:
- files changed
- tests run
- audit status
- next prompt: `16_REAL_PILOT_ADE20K_PLAN.md`
