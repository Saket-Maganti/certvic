# Specificity Branch Decision

- Branch: `MODEL_DEPENDENT_SPECIFICITY_V2_PENDING`
- V2 status: `BLOCKED_MISSING_PREDICTIONS`
- All-model specificity claim allowed: `false`
- Paper evidence: `false`

## Current Branch Language

- InternVL and LLaVA pass the irrelevant-edit specificity gate.
- Qwen shows a strong update-gap result but elevated sensitivity to irrelevant controls.
- The evidence supports model-dependent specificity, not all-model specificity.
- Main conclusions must be conditioned on this limitation.

## Why

Qwen failed the V1 spurious specificity gate at `12/94 = 0.1277`, above the fixed `<= 0.10` threshold. Spurious V2 is prepared but blocked on missing Kaggle predictions, so it cannot resolve the branch today.
