# Codex Prompt 11 — Baselines and Ablations

Implement the construct-validity shields:
- random/majority baseline
- text-only baseline
- caption-only baseline stub
- control edits
- original-only recognition accuracy

## Goal

The paper must defend that items are visually grounded and not solvable through text leakage. Add baseline runners and scoring hooks.

## Files to create/update

```text
certvic/eval/baselines.py
certvic/providers/text_only.py
certvic/providers/caption_only.py
certvic/providers/random_baseline.py
certvic/reporting/ablations.py
tests/test_random_baseline.py
tests/test_text_only_baseline.py
tests/test_ablation_reporting.py
docs/METRICS_SPEC.md
docs/REPRO.md
```

## Random / majority baseline

Implement:
- seeded random yes/no
- majority answer baseline from task manifest
- deterministic outputs

## Text-only baseline

Provider sees:
- prompt only
- no image
- must use no answer metadata
- for now use simple heuristic/random baseline, not external LLM

Purpose:
- If text-only does well, item may be leaked or not visual.

## Caption-only baseline

Implement a stub architecture:
- optional open captioner later
- no heavy dependencies in tests
- if caption file exists, provider answers from caption through deterministic heuristic/mock
- if no caption file, mark unavailable

No paid captioning.

## Control edits

Make sure control_irrelevant items are:
- generated in smoke fixtures
- scored as no_change
- reported separately as spurious flip rate

## Ablation report

Create:
```bash
python -m certvic.reporting.ablations \
  --reports data/results/*_report/summary.json \
  --out data/results/ablation_summary.md
```

It should compare:
- model vs text-only
- model vs random
- control spurious flips
- caption-only availability/status

## Tests

Test:
- random baseline deterministic
- text-only does not receive image path
- caption-only unavailable status is explicit
- ablation report writes markdown

## Docs

Update:
- METRICS_SPEC.md with construct-validity baselines.
- REPRO.md with baseline commands.

## Finish

Run:
```bash
python -m pytest -q
```

Report:
- files changed
- tests run
- next prompt: `12_HUMAN_VALIDATION_MINIMAL.md`
