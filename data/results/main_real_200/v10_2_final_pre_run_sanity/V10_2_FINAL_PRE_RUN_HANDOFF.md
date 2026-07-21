# V10.2 Final Pre-Run Handoff

Verdict: ready to run Qwen Spurious V2 on Kaggle. Stop upgrading.

## Direct Answers

- Two zips present and hash-locked: `true`
- Three Spurious V2 notebooks static-valid: `true`
- Importer failed safely on missing outputs: `true`
- Selected tests passed: `true` (`20 passed in 4.98s`)
- Full tests passed: `true` (`657 passed in 42.80s`)
- Claim guard passed: `true`; findings: `0`
- Privacy guard passed: `true`; findings: `0`
- `paper_evidence` changed: `false`
- Main-500 allowed: `false`

## Zip Hashes

- `dist/certvic_kaggle_main200_bundle.zip`: `12962bb9a0e518c998ae90ddacaac4c372cf10e7761db56c21aaf38ee7e11b77`
- `dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip`: `edfa44d3aae4dc9ba7cadde42c11eb3d38de0a6a23a8a92055d21c0dd2269102`

## Remaining Blockers

- Qwen Spurious V2 provider output is missing.
- InternVL Spurious V2 provider output is missing.
- LLaVA-OneVision Spurious V2 provider output is missing.
- Real human labels are missing.
- Spurious V2 ingest/gate decision has not run on real outputs.
- Main-500 remains blocked.

## Exact Next Action

Run notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb on Kaggle with PROVIDER="qwen2_5_vl_7b" and RUN_TAG="spurious_v2".

Do not run Main-500.
