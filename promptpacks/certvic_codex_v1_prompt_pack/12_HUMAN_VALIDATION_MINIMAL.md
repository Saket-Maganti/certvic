# Codex Prompt 12 — Minimal Human Validation Workflow

Build the small, honest human-validation system for edit validity, not answer-key creation.

## Goal

Human validation in CertVIC should validate:
- edit photorealism
- single-factor validity
- answer-change unambiguity

It should not create the primary labels; labels come from controlled edits.

## Files to create/update

```text
certvic/validation/human_sheet.py
certvic/validation/iaa.py
certvic/validation/aggregate_human.py
tests/test_human_sheet.py
tests/test_iaa.py
tests/test_aggregate_human.py
docs/DATA_CARD.md
docs/REPRO.md
docs/CLAIM_LEDGER.md
```

## Human rating schema

Create rating rows with:
- item_id
- rater_id
- photorealistic: yes/no/uncertain
- single_factor: yes/no/uncertain
- required_change_unambiguous: yes/no/uncertain
- notes
- timestamp

## Export sheet

CLI:
```bash
python -m certvic.validation.human_sheet \
  --tasks data/manifests/tasks.jsonl \
  --out data/annotations/human_validation_sheet.csv \
  --max-items 300 \
  --seed 0
```

CSV should include:
- item_id
- original path/pointer
- edited path/pointer
- task family
- domain
- neutral question
- rating fields blank

Do not include ground-truth answers unless config explicitly allows. Default: hide answers to avoid bias.

## IAA

Implement simple agreement:
- percent agreement for each binary field
- Cohen’s kappa for 2 raters
- Fleiss-like placeholder or majority agreement for 3+ raters

Do not overcomplicate. Tests should validate simple known cases.

## Aggregate

CLI:
```bash
python -m certvic.validation.aggregate_human \
  --ratings data/annotations/ratings.csv \
  --out data/annotations/human_validity_summary.json \
  --drop-list data/annotations/drop_items.txt
```

Drop item if:
- majority says not photorealistic
- majority says not single_factor
- majority says required_change ambiguous
- too many uncertain ratings

Output:
- aggregate rates
- agreement metrics
- drop list
- keep list

## Docs

Update DATA_CARD:
- humans validate item validity only
- target 200–400 items
- 2–3 volunteers
- limitations

Update CLAIM_LEDGER:
- item-validity claims require human validity summary for pilot/main.

## Tests

Test:
- sheet hides answers by default
- kappa perfect agreement = 1
- disagreement lower
- aggregate drops invalid item
- uncertain handling works

## Finish

Run:
```bash
python -m pytest -q
```

Report:
- files changed
- tests run
- next prompt: `13_KAGGLE_NOTEBOOK_GUIDES.md`
