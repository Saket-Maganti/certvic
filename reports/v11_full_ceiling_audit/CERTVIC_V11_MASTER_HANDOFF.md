# CertVIC V11 Master Handoff

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

This is the authoritative operational entry point for the current repository state.

## Executive verdict

CertVIC contains real, internally coherent pilot outputs for three open models, but it is not
scientifically certified or submission-ready. Numerical intervention-gap bounds cross the configured
threshold, yet the sample-size/family policy fails, validity screening is machine-assisted, Qwen
fails the frozen V1 specificity gate, current V2 is retrospective and has no outputs, revisions are
unpinned, and Main-500 is blocked. `paper_evidence=false` remains the only defensible setting.

## Verified observations

| Model | n | a | raw answer-change p | gap | CS LB | full certified |
|---|---|---|---|---|---|---|
| Qwen2.5-VL-7B | 91 | 0.9231 | 0.1758 | 0.7473 | 0.363958 | false |
| InternVL2-8B | 91 | 0.9231 | 0.0989 | 0.8242 | 0.440881 | false |
| LLaVA-OneVision-7B | 91 | 0.8901 | 0.1758 | 0.7143 | 0.330991 | false |

| Model | V1 flips | rate | frozen V1 status |
|---|---|---|---|
| Qwen2.5-VL-7B | 12/94 | 0.127660 | FAIL |
| InternVL2-8B | 1/94 | 0.010638 | PASS observed rule only |
| LLaVA-OneVision-7B | 3/94 | 0.031915 | PASS observed rule only |

The Qwen count is not explained by parse, duplicate, missing-row, provider, or pair-key failures.
All twelve flips are Qwen-only in the three-model V1 matrix. The observation motivates a
model-dependent specificity question; it does not establish why the model differs.

## Current decision state

- Current V2: `DIAGNOSTIC_ONLY_RETROSPECTIVE_STRICTER_CONTROL`; 30/30
  items overlap V1, 4/12 Qwen failures retained, 0/3 outputs present.
- Human review: pending; stale embedded labels are superseded by V11 canonical overrides.
- Main-500: **NO-GO**.
- Second domain: defer until the specificity branch is valid.
- Model matrix: keep three models, but pin immutable revisions before new execution.
- Public image release: blocked pending licensing.
- Grouped detectability diagnostics: main91 symmetric AUC 0.5783; V1 control94 symmetric
  AUC 0.7123; retrospective V2-30 symmetric AUC 0.6922. These measure classifier
  separability, not semantic validity.

## Exact next sequence

1. Complete two-rater blinded review of the 91 intervention items and 94 V1 specificity items;
   adjudicate while preserving raw sheets.
2. Build and hash-lock an independent, unseen, prospectively powered specificity set.
3. Pin immutable model/processor revisions and run the three-model matrix under the frozen rule.
4. Import transactionally; report raw and validity-filtered outcomes with missing pairs fail-closed.
5. Sign off the specificity branch. Only then reconsider Main-500 and a small second domain.

Running the existing 30-item V2 package is optional and diagnostic. It must not replace step 2 or
unlock Main-500. Read the evidence, gate, blocker, and claim ledgers before any paper update.

## Final local validation and locks

- Tests: 170 focused and 747 full-suite tests passed; Ruff is clean.
- Guards: claim language and text-tree privacy both have 0 findings.
- Ledgers: 23 evidence entries, 22 scientific/operational gates, 11 explicit blockers; no
  `paper_evidence=true` or `human_reviewed=true` entry.
- V2 private ZIP: `61102740bb1ad76d0315b65839c3a73ad502fd204b77b1634a5003913e29d277`.
- Main code ZIP: `3e311fcb3f16ab6fdad839e2e340965bf5d65dca96938ef5a206b77d727b8447`.
- Blinded reviewer ZIP: `d6e777d035fa806d0b4ffb42cd6c140e08c1187a571770ba87b70c629c3f044f`.
- Anonymous 3-page PDF: `d9a01c930c892059268d119f0d296b8ff1a5d924b42c2799631866e9213fa76b`.

The external ADE annotation tree is not mounted inside this checkout. The V8.1 rebuild therefore
uses the preserved annotation-derived quality audit only after validating exact 94-item coverage,
paths, and live image-difference boxes; it labels this `FROZEN_DERIVED_REAL_EVIDENCE_CACHE`, not a
fresh annotation rerun. The V2 builder now refuses to overwrite canonical artifacts unless exactly
the frozen 30 items pass preflight. The remaining-runbook builder deletes and packages only files it
owns, so it can no longer erase or absorb the V2 archive.

## Operational files

- Protocol: `configs/certvic_v11_protocol.yaml`
- Prospective analysis: `docs/methodology/CERTVIC_PROSPECTIVE_ANALYSIS_SPEC_V11.md`
- Exact V2 execution card: `reports/v11_full_ceiling_audit/SPURIOUS_V2_EXECUTION_CARD.md`
- Human packet: `reports/v11_full_ceiling_audit/human_review_packet/`
- Evidence/gate/blocker/claim ledgers: this directory's `CERTVIC_*LEDGER*` and blocker register.
- Exact final commands and exits: `V11_COMMAND_AND_EXIT_CODE_LOG.md`
- Final validation: `V11_FINAL_VALIDATION.md`
- Evidence-safe draft: `paper/main_v11.pdf` and `output/pdf/certvic_v11_evidence_safe_draft.pdf`

Do not execute the current 30-item V2 merely to seek a favorable Qwen result. The immediate required
work is the blinded two-rater review plus freezing a powered, outcome-unseen control set. Only after
those are locked should immutable revisions be filled, the three notebooks run, outputs imported
transactionally, and the prospective specificity decision computed.
