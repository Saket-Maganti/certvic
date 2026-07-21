# CertVIC Repository Forensic Inventory

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

The inventory separates live code and evidence from generated, stale, synthetic, and release material.

## Current filesystem census

| Measure | Count |
|---|---|
| Regular files (excluding V11 output/caches) | 4,019 |
| Directories | 300 |
| Bytes | 562,128,071 |
| Empty files | 5 |
| Symlinks | 0 |
| Package Python modules | 300 |
| Test files | 131 |
| Python scripts | 35 |
| Notebooks | 31 |
| Config files | 19 |
| Paper-tree files | 71 |
| Docs-tree files | 276 |

The walk excludes this V11 output directory plus `.git`, test/lint caches, and `__pycache__`.
The final tree contains 660 byte-identical content groups,
786 redundant copies, and 35,800,485 redundant bytes.
Those duplicates are retained because many are historical provenance or packaged copies; the
builder does not delete or silently choose among them.

## Largest current files

| Path | Bytes |
|---|---|
| kaggleoutputs/certvic_main200_diffusion_results.zip | 82,728,166 |
| kaggleoutputs/diffusion_out.zip | 82,558,629 |
| dist/certvic_remaining_kaggle_runbooks.zip | 71,815,111 |
| dist/kaggle_remaining_runs/certvic_perception_control_scaled.zip | 34,888,263 |
| dist/certvic_perception_control_scaled.zip | 34,851,026 |
| data/edits/main_real_200.zip | 21,982,793 |
| dist/certvic_absent_object_control.zip | 12,734,926 |
| dist/kaggle_remaining_runs/certvic_polarity_ablations.zip | 12,467,701 |
| dist/kaggle_remaining_runs/certvic_mechanism_probes.zip | 12,453,137 |
| dist/certvic_main200_session2_data.zip | 12,430,402 |
| data/results/main_real_200/ade20k_masks.jsonl | 12,141,279 |
| dist/kaggle_remaining_runs/certvic_spurious_flip_control.zip | 12,032,606 |
| dist/certvic_spurious_flip_control.zip | 12,022,781 |
| dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip | 6,090,214 |
| data/results/tiny_real_pilot/ade20k_masks.jsonl | 1,056,066 |

## Empty files

- `data/results/main_real_200/output_triage/parse_failure_examples.jsonl`
- `data/results/main_real_200/pilot_generated_rejected.jsonl`
- `data/results/tiny_real_pilot/pilot_generated_rejected.jsonl`
- `data/results/v1_1_smoke_matrix/mock_parser_fail/report/failure_gallery.jsonl`
- `data/results/v1_1_smoke_matrix/mock_perfect/report/failure_gallery.jsonl`

## Broken symlinks

- none

## Baseline-to-final discrepancy

The initial audit snapshot recorded `ade20kdataset/ade20k.zip` and a substantially larger tree.
That path is absent from the final repository census. No V11 result depends on that archive, and
this pass did not restore it from a sibling project because cross-project copying was not authorized.
Treat the missing local source archive as a data-availability blocker for mining a new independent
control set; use `<PROJECT_PARENT>/certGen/ade20kdataset/ade20k.zip` only after the owner explicitly
confirms that it is the intended source copy.

## Evidence-bearing zones

- `data/results/main_real_200`: real raw outputs, derived reports, diagnostics, review templates, and historical audits coexist.
- `data/edits/spurious_flip_control`: canonical 94-item V1 control tasks and image pairs.
- `data/edits/spurious_v2_control`: 30-item retrospective stricter-control package.
- `data/results/v1_1_smoke_matrix` and `data/results/v2_1_sim_matrix`: software fixtures, never empirical evidence.
- `dist`: execution and release packages whose embedded manifests must be checked independently.
- `paper`: current V11 draft plus historical sections and generated intermediates.

## High-risk ambiguity

Historical V7--V10 reports use many ad hoc evidence-status strings. V11 does not normalize
the raw files in place. Instead, `configs/certvic_v11_protocol.yaml` and the evidence ledger
provide a hash-preserving canonical override. In particular, embedded
`HUMAN_REVIEWED_NON_EVIDENCE` labels do not establish human review.
