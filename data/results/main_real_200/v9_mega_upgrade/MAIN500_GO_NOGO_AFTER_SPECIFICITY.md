# Main-500 Go/No-Go After Specificity

- Decision: `HOLD_FOR_SPURIOUS_V2`
- Main-500 can start: `false`
- Resolved specificity branch: `false`
- Spurious V2 status: `BLOCKED_MISSING_PREDICTIONS`
- Human review status: `PENDING_REAL_HUMAN_REVIEW`
- Paper branch: `MODEL_DEPENDENT_SPECIFICITY_V2_PENDING`

## Reasons

- Spurious V2 provider predictions are missing.
- Qwen V1 specificity remains failed.
- Real Qwen human review packet is pending and blank.
- Model-dependent paper language is prepared but does not by itself create new control evidence.

## Future GO Conditions

- All Spurious V2 provider outputs imported and gated cleanly.
- Or Qwen fails V2 but the paper explicitly proceeds under a signed-off model-dependent Main-500 plan.
- Human audit sheet is filled and applied if used to justify exclusions.

## Current Action

Do not start Main-500 locally or on Kaggle from this state.
