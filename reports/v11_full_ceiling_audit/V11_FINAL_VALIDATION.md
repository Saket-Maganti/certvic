# V11 Final Validation

**Verdict:** local-safe implementation and artifact validation are complete; the scientific project
remains pilot-only and submission-blocked; `paper_evidence=false`.

## Validated invariants

- Full repository suite: 747 passed; focused repaired surfaces: 170 passed; Ruff: clean.
- Required Phase-14 reports: 25/25 present and non-empty.
- Evidence ledger: 23 entries; gate ledger: 22 gates; blocker register: 11 blockers.
- `paper_evidence=true`: 0 entries. `human_reviewed=true`: 0 entries.
- Real observed pairs: 91/provider on the intervention pilot and 94/provider on V1 specificity;
  all six raw files have 182 parse-valid rows.
- Numeric CS lower bounds cross 0.05 for all three models, but no model is fully policy-certified.
- Frozen V1 result preserved: Qwen 12/94 fails; InternVL 1/94 and LLaVA 3/94 pass the historical
  observed-rate rule only.
- Current V2 remains retrospective diagnostic-only: 30/30 items overlap V1; 0/3 provider outputs;
  no result was invented or promoted.
- Human packet is structurally valid and blank. Default validation exits 2; no human label or
  agreement statistic exists.
- Main-500 remains `execution_allowed_now=false` and was not run.
- Claim guard and text-tree privacy audit each pass with 0 findings. The historical session2 data ZIP
  remains deprecated/non-release because its internal JSONL contains 182 private-path occurrences.
- Six notebooks pass static validation only. All still require exact immutable model revisions before
  execution; no notebook-execution claim is made.
- V2, main-code, and reviewer packages are deterministic and hash-locked; the strict main-bundle
  security audit has 0 findings.
- The anonymous V11 PDF compiles twice to 3 visually inspected pages; delivered and paper copies match.

## Honest blocked checks

- Bibliography/citations: blocked; no `.bib` or citation command exists.
- Human validity/IAA: blocked; two independent rater sheets and adjudication are blank.
- Confirmatory specificity: blocked; the current V2 is post-outcome, reuses V1, and has no outputs.
- Exact historical model revisions: unavailable; future notebooks fail closed until revisions are set.
- Public release: blocked by missing project license, unresolved ADE-derived image redistribution, and
  the separately quarantined session2 archive.
- Main-500 and second-domain execution: blocked until the specificity, review, revision, quality, and
  importer gates are genuinely complete.

## Final artifact locks

| Artifact | SHA-256 / state |
|---|---|
| `dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip` | `61102740bb1ad76d0315b65839c3a73ad502fd204b77b1634a5003913e29d277` |
| `dist/certvic_kaggle_main200_bundle.zip` | `3e311fcb3f16ab6fdad839e2e340965bf5d65dca96938ef5a206b77d727b8447` |
| `reports/v11_full_ceiling_audit/human_review_packet/certvic_v11_blinded_reviewer_bundle.zip` | `d6e777d035fa806d0b4ffb42cd6c140e08c1187a571770ba87b70c629c3f044f` |
| `paper/main_v11.pdf` | `d9a01c930c892059268d119f0d296b8ff1a5d924b42c2799631866e9213fa76b`; 3 pages; anonymous |
| Main-500 | `BLOCKED`; `execution_allowed_now=false` |

The exact command/exit evidence is in `V11_COMMAND_AND_EXIT_CODE_LOG.md`. Expected blocker exits are
reported as blockers and were not converted into passes.
