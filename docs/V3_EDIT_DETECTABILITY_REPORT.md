# V3 Prompt 05 — Edit Detectability Probe Report

## Goal

Build a CPU-only artifact-risk probe: can cheap low-level features distinguish
original from edited images? If yes, the VLM gap may be artifact-confounded.

## What was built

- `certvic/validation/edit_detectability.py` — per-image features (file size, edge density, sharpness, color stats, uniform fraction), paired features (histogram distance, mean abs diff, edge/sharpness deltas, outside-mask change), a scikit-learn cross-validated `LogisticRegression` classifier with a deterministic rank-AUC fallback, per-item detectability scoring, artifact-risk flag, and output writer (`detectability_summary.json`, `features.csv`, `report.md`, `highly_detectable_items.jsonl`).
- `certvic/reporting/edit_detectability_report.py` — markdown report with risk band, per-feature AUC table, flagged items, and mitigations.

## Tests

`tests/test_v3_edit_detectability.py` — 10 tests: per-image/paired features, missing-image handling, **detectable (gray-blob) edits → AUC ≥ 0.8 + artifact_risk True**, subtle edits → AUC < 0.8, sklearn-disabled fallback path, item skipping, output writing + report content, top-fraction item flagging, unknown-AUC report rendering, and a no-GPU/no-heavy-import guard.

## Verification

- `python3 -m pytest -q` — full suite green (307 passed; was 297).
- CLI smoke on 12 synthetic items with flat-gray-blob edits: backend `sklearn_logreg_cv`, **AUC 1.0, artifact_risk True**, 2 items flagged. This reproduces the known construct-validity risk: the crude `simple` edit engine is trivially detectable, motivating photorealistic diffusion edits.

## Evidence / cost discipline

CPU-only, no GPU, no downloads, no paid services. Output marked
`CONSTRUCT_VALIDITY_DIAGNOSTIC_NON_EVIDENCE`; `evidence_claims_made=false`. No
heavy imports (torch/diffusers absent); uses core numpy/PIL/sklearn only.

## Status

**PASSED.** One of the most important CVPR reviewer defenses is now measurable.

## Remaining blockers

None. Run against the real reviewed tasks once photorealistic edits exist; the
probe will quantify whether diffusion edits lower detectability vs the simple
engine.
