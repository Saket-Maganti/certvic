# Software Validation and Repair Report

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

This report records the root-cause repairs already made in the V11 working tree and the remaining validation boundary.

## Repairs

| Area | Root cause | Repair | Regression surface |
|---|---|---|---|
| V2 importer | Earlier import accepted under-specified or stale inputs. | Transactional schema, row/key/provider/run/hash checks; atomic writes; idempotency and conflict refusal. | `tests/test_v9_spurious_v2_ingest_decision.py` |
| V2 notebooks | Provider scaffold did not guarantee two-device execution, exact model identity, or exact merged rows. | Generated notebooks now use the working runner spine, `Popen`, device-local processes, revision/cache locks, bundle and image hashes, resume checks, and the V11 v3 output manifest. | V2 builder/runbook and static notebook tests |
| Certification policy | A numerical gap helper could be confused with the complete policy. | Full sample, family, parse, specificity, evidence, and CS gates are applied together. | certification-policy tests |
| Historical review labels | Machine-assisted approval was represented as human-reviewed metadata. | V11 adds hash-preserving canonical overrides and fail-closed review integration. | claim and integration tests |
| Prompt ablations | Alternating source answers corrupted gold polarity. | Builders normalize source presence before applying ablation format. | prompt/mechanism tests |
| Detectability | Item variants could leak between folds and directional AUC could invert. | Grouped-by-item validation and symmetric AUC. | detectability tests |

## Validation boundary

The focused repaired surfaces passed 124 tests during the V11 working session. The authoritative
final count, lint status, notebook result, package integrity, claim guard, privacy scan, and paper
checks must be taken from the command ledger after they are rerun. A historical statement such as
"657 passed" is not treated as current merely because it appears in an older handoff.

No repair changes a raw model response, V1 item membership, frozen threshold, or failure count.
