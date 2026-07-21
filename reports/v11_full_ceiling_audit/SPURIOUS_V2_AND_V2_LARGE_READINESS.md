# Spurious V2 and V2-Large Readiness

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

The existing 30-item package is ready for a private retrospective diagnostic run, not a confirmatory claim.

## Current 30-item package

- Unique items: 30; V1 ID overlap: 30/30.
- Object distribution: {"car": 3, "chair": 8, "sofa": 11, "table": 8}.
- Patch-to-target-box distance: min 76.0 px,
  median 118.0 px, max
  280.0 px.
- Target-box intersections: 0; target-mask overlap: 0.
- Historical scores available to the retrospective selector: 4/30.
- V11 post-selection, pre-provider diagnostic scores now hash-locked: 30/30;
  they cannot justify retroactive exclusion or confirmatory status.
- Grouped-item symmetric set-level AUC: 0.6922, below the 0.80 repository flag but not proof
  of imperceptibility, semantic invariance, or outcome-unseen selection.
- V2 image entries hash-locked in the bundle manifest: 60/60.
- Current private control ZIP SHA-256: `61102740bb1ad76d0315b65839c3a73ad502fd204b77b1634a5003913e29d277` (recompute after every rebuild).
- Known Qwen V1 failures retained: 4/12; filtered out:
  8/12.
- Provider output files found: 0/3.
- Full local candidate audit: `SPURIOUS_V2_LOCAL_CANDIDATE_INVENTORY.csv` records all
  94 V1-derived candidates, 30 retained and 64 rejected, with geometry, available salience,
  duplicate-risk, and decision reasons. Every row is retrospective and confirmatory-ineligible.

Because all 30 items were selected from V1 after its outcomes, no result on this package can
confirm or clear specificity. It may quantify sensitivity to stricter geometry/salience filtering.
The raw V1 result must remain beside any V2 diagnostic result.

## V2-Large requirement

Create an independent pool with zero V1 overlap, lock exclusions and ordering before outputs,
complete two-rater blinded validity review, choose n from the prospective operating-characteristic
table, and hash-lock tasks. The one-model upper-bound rule needs at least 29 zero-failure items;
the simultaneous three-model best case needs at least 39, with larger n required for useful power
at nonzero rates.

`configs/certvic_v11_protocol.yaml` machine-locks zero target overlap, at least 75 px bbox distance,
set-level low-level AUC <= 0.80, category/spatial balance, exact/perceptual duplicate checks, image
quality, answer invariance, and two-rater acceptance. Perturbation-area, per-item salience,
category targets, image-quality, and perceptual-duplicate thresholds remain
`TBD_BEFORE_BUILD`; `unresolved_tbd_blocks_selection=true`, so no independent item selection is
authorized until those values are frozen.

Source rows state `redistribution_allowed=false`; the existing image zip is a private Kaggle input,
not a public release artifact until licensing is independently verified.

## Runtime contract

The importer requires exact schema `certvic.v11.spurious_v2.kaggle_output_manifest.v3`.
Each notebook must receive a 40-character immutable model revision and exact code/control-bundle
SHA-256 values. Static-valid notebooks are not runnable while `MODEL_REVISION` is null.
