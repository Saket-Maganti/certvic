# CertVIC Detectability Gate Guide

Run after final confirmatory selection and before any provider output:
`python3 -m certvic.cvpr.detectability_gate --tasks <BUNDLE>/tasks.jsonl --bundle-root <BUNDLE>
--config configs/studies/specificity_confirmatory_cvpr.yaml --out <GATE.json>`.
The CPU-safe fixed classifier uses source-grouped folds, out-of-fold symmetric AUC, grouped bootstrap
uncertainty, fold results, and perturbation-family results. The prospective threshold is 0.80. FAIL
requires prospective reconstruction; do not remove items after observing provider outcomes. This
irrelevant-edit gate is not a semantic-intervention success metric.
