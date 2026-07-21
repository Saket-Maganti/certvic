# CertVIC V1.1 Scaffold Hardening Report

Date: 2026-06-21

Verdict: PASS

CertVIC V1.1 hardens the pre-real-data scaffold only. This remains a
zero-cost, local, `MOCK_ONLY` smoke/audit baseline. No real evidence claims are
made, no paid services were used, no datasets were downloaded, and no GPU is
required.

## What Changed

- Added adversarial mock-provider variants:
  - `mock_perfect`
  - `mock_inconsistent`
  - `mock_spurious_flip`
  - `mock_parser_fail`
  - `mock_always_yes`
  - `mock_always_no`
  - `mock_random_seeded`
- Marked mock providers as `MOCK_ONLY`, non-evidence, zero-cost providers.
- Extended prediction and score metadata with provider type, split,
  evidence-status, and synthetic-smoke provenance.
- Hardened certification gates so certified claims are blocked unless all of
  the following are true:
  - split is not smoke
  - evidence status is not `MOCK_ONLY`
  - provider type is not mock
  - data are not synthetic smoke fixtures
  - anytime-valid CS is available
  - CS lower bound exceeds the configured threshold
  - claim wording passes the forbidden-claim scanner
- Added descriptive paired-bootstrap intervals labeled
  `descriptive_only_not_anytime_valid`.
- Added by-family, by-domain, and by-required-change descriptive bootstrap
  blocks.
- Added control-edit spurious flip and parse-failure sensitivity summaries.
- Updated report builder outputs:
  - `main_model_table.csv`
  - `main_model_table.tex`
  - `by_family_table.csv`
  - `by_domain_table.csv`
  - `control_edit_table.csv`
  - `parse_failure_table.csv`
  - `certification_status.json`
  - `claim_ledger.json`
  - `failure_gallery.jsonl`
  - `report.md`
- Strengthened leakage tests for prompt and filename leakage terms including
  `removed`, `occluded`, `edited`, `displaced`, `answer`, `label`,
  `ground_truth`, `unsupported`, `unsafe`, and `changed`.
- Fixed runner `--overwrite` behavior so repeated smoke-matrix runs replace
  prediction JSONL outputs instead of appending duplicate rows.

## Tests Run

```bash
python3 -m pytest -q
```

Result: 85 passed.

## Smoke Matrix

Matrix root:

```text
data/results/v1_1_smoke_matrix/
```

The matrix used 12 synthetic smoke items and 24 predictions per provider.

| Provider | n | Original Acc | Edited Acc | Consistency | Gap | Parse Failure | Control Spurious Flip | Certified |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `mock_perfect` | 12 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | false |
| `mock_inconsistent` | 12 | 1.000 | 0.500 | 0.500 | 0.500 | 0.000 | 0.000 | false |
| `mock_spurious_flip` | 12 | 1.000 | 0.500 | 0.500 | 0.500 | 0.000 | 1.000 | false |
| `mock_parser_fail` | 12 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | false |

Notes:

- `mock_parser_fail` reports control spurious flip under the
  parse-fail-as-inconsistent sensitivity convention; this is not a real answer
  flip and remains a parser stress test.
- All matrix reports explicitly say smoke is `MOCK_ONLY`, no evidence claims
  are made, no paid services were used, and real pilot data are required before
  paper claims.
- All matrix audits passed, and all matrix artifacts block certified claims for
  smoke/mock/synthetic/CS-unavailable reasons.

## Certification Status

No V1.1 smoke-matrix provider is certified.

This is expected and required. V1.1 certification gates correctly prevent
certified claims for:

- smoke split
- `MOCK_ONLY` evidence status
- mock provider type
- synthetic smoke fixtures
- unavailable anytime-valid CS

Descriptive bootstrap intervals may be generated for debugging and reporting
shape only. They are not anytime-valid and are never used to certify claims.

## Remaining Limitations

- Smoke images are synthetic fixtures only.
- Mock providers are deterministic adversarial checks, not model evidence.
- No real-image source licenses have been verified beyond templates.
- No real edit quality, human validity, or open-model behavior has been tested.
- Optional `confseq` remains optional; certification stays unavailable without
  it and without eligible non-smoke evidence.
- Paper sections still contain `[RESULT REQUIRED]` placeholders and no fake
  result values.

## Next Recommended Step

Preserve this V1.1 scaffold state, then begin the real-data preparation path
only when ready:

1. Provide a local ADE20K root.
2. Build recipe-first source and mask manifests without downloads.
3. Select the 200-item pilot.
4. Run edit quality gates and human validation sheets.
5. Run open local VLMs on free Kaggle GPU only.
6. Keep all paper claims blocked until real, non-smoke artifacts and
   anytime-valid certification gates support them.
