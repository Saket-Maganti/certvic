# Pilot Gate Checks

```bash
python3 -m certvic.pipeline.pilot_gate_check --stage before_vlm \
  --config configs/real_pilot_ade20k.yaml --out data/results/pilot_gate_before_vlm.json
```

Stages: before_edit_generation, before_visual_review, before_vlm, before_claims,
before_release. Each verifies the prerequisites for advancing; the run must not
proceed past a failing gate. Gate checks run no inference and make no claims.

| Stage | Requires |
| --- | --- |
| before_edit_generation | source + mask manifests, selection, edit plan, label policy, zero-cost |
| before_visual_review | generated edits + quality report |
| before_vlm | reviewed tasks + review summary, certification + tiny-eval configs |
| before_claims | certification policy, claim ledger, paper claim checklist |
| before_release | release config, reviewer defenses doc |
