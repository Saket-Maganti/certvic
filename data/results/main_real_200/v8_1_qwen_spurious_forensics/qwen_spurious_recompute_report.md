# V8.1 Qwen Spurious Recompute Report

`paper_evidence=false` `canonical_gate_threshold=0.10`

No scenario updates the canonical gate. Claim-valid scenarios are raw, parser-error-only, and image-mismatch-only; all fail because they exclude zero items.

| Scenario | Excluded | Evaluable | Flips | Rate | Gate | Claim-valid |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `A_RAW_GATE` | 0 | 94 | 12 | 0.1277 | FAIL | True |
| `B_PARSER_ERROR_ONLY_EXCLUSION` | 0 | 94 | 12 | 0.1277 | FAIL | True |
| `C_PROVENANCE_IMAGE_MISMATCH_EXCLUSION` | 0 | 94 | 12 | 0.1277 | FAIL | True |
| `D_OBJECTIVE_CONTROL_INVALID_EXCLUSION` | 20 | 74 | 10 | 0.1351 | FAIL | False |
| `E_SOFT_SUBJECTIVE_PRELIMINARY_EXCLUSION` | 8 | 86 | 4 | 0.0465 | PASS | False |
| `F_BEST_CASE_CODEX_PRELIMINARY_EXCLUSION` | 10 | 84 | 2 | 0.0238 | PASS | False |

## Interpretation

- `A_RAW_GATE`: Current canonical gate: all 94 items, no exclusions.
- `B_PARSER_ERROR_ONLY_EXCLUSION`: Objective parser-error-only exclusion. No parser errors were found in the Qwen paired rows.
- `C_PROVENANCE_IMAGE_MISMATCH_EXCLUSION`: Objective image/provenance mismatch exclusion. No missing or mismatched image pairs were found.
- `D_OBJECTIVE_CONTROL_INVALID_EXCLUSION`: Objective geometry/pathology candidate rule across all 94 items. It is not a canonical gate rule in the current repository policy.
- `E_SOFT_SUBJECTIVE_PRELIMINARY_EXCLUSION`: Diagnostic only: excludes machine-preliminary patch-too-salient, patch-near-target, and prompt-ambiguous labels among the 12 Qwen failures.
- `F_BEST_CASE_CODEX_PRELIMINARY_EXCLUSION`: Not claim-valid: excludes every Qwen failed item not labeled CODEX_PRELIM_VALID_FAILURE by this preliminary AI-assisted triage.

Blunt result: no claim-valid scenario passes. The raw Qwen gate remains failed at 12/94 = 0.1277.
