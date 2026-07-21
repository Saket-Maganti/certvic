# Reproduce the main_200 3-Model Pilot

This reproduces the **pilot** result (`evidence_status = HUMAN_REVIEWED_NON_EVIDENCE`,
`paper_evidence = false`) end-to-end on free compute. No paid APIs, GPUs, datasets, or
annotation. ADE20K pixels and model weights are **not** redistributed — you obtain them under
their own licenses.

## 0. Prerequisites

- Python 3.11, this repo, and a free Kaggle account (T4×2) for GPU steps.
- ADE20K (`ADEChallengeData2016`) obtained by you under its license. Place it where the
  adapter expects (see `docs/runbooks/DATASET_DECISION.md`).

## 1. Fastest path — re-score from the locked raw predictions (CPU, no GPU)

The raw VLM predictions are sha256-locked in the repo, so you can reproduce every reported
number **without** any GPU:

```bash
# Per-model report (already wired to the locked raw predictions):
python3 scripts/pilot_report_from_raw.py                                  # Qwen2.5-VL-7B
# (InternVL / LLaVA reports are regenerated the same way from their raw_predictions__* dirs)

# Cross-model table + paper tables:
python3 scripts/build_multimodel_summary.py
python3 scripts/build_main200_paper_tables.py

# Verify provenance hashes:
python3 -m certvic.v7.result_ledger_audit --ledger registry/results/main200_pilot_result_ledger.json
```

Expected: the 3-model table in `data/results/main_real_200/multimodel_pilot_summary.md`
(Qwen Δ=0.747 / CS LB 0.364; InternVL Δ=0.824 / 0.441; LLaVA Δ=0.714 / 0.331), all certified
under the pilot protocol; ledger audit `passed: true`. Runtime: seconds to ~1 min/model on CPU.

## 2. Full path — regenerate predictions on free Kaggle (GPU)

1. **Edits + gates** (one-time): generate ADE20K edits and pass the detectability + quality
   gate — `notebooks/kaggle/certvic_main200_diffusion_T4x2.ipynb`, then the detectability gate.
   Do not proceed to VLM inference until the gate is GO.
2. **Human visual review** of the edited images (see `docs/HUMAN_REVIEW_OPERATIONS.md`); keep
   only approved items (the 91-item reviewed set).
3. **VLM eval per provider** — `notebooks/kaggle/certvic_main200_vlm_T4x2_AFTER_GATES.ipynb`
   for `qwen2_5_vl_7b`, and the self-download notebooks for `internvl_8b` /
   `llava_onevision_7b`. Save predictions + `run_manifest.json`.
4. **Ingest + score locally** with `scripts/pilot_report_from_raw.py --provider <id>
   --model-name <hf-id> --run-label <id> --raw-presence ... --raw-control ...`.

## 3. Hash verification

```bash
python3 -m certvic.v7.result_ledger_audit --ledger registry/results/main200_pilot_result_ledger.json
python3 -m certvic.security.release_privacy_audit --root .
```

## What this reproduces (and does not)

- **Does:** the pilot 3-model presence-arm result + absent-object control, fully from locked
  raw predictions, with hash verification.
- **Does not:** establish a paper-grade or general claim. Open blockers (spurious-flip
  specificity control, scale, second domain, IAA) are tracked in
  `docs/V7_POST3MODEL_PROJECT_STATE.md`.
