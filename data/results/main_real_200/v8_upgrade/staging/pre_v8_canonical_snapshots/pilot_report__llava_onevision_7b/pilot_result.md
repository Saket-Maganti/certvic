# CertVIC Pilot Result -- llava-onevision-qwen2-7b-ov (single model)

Generated: 2026-06-24T19:22:59.618619+00:00

**Status: REAL PILOT. Provenance: real ADE20K images + real llava-hf/llava-onevision-qwen2-7b-ov-hf (open weights, free Kaggle T4x2). NOT synthetic / NOT smoke / NOT mock.**

**evidence_status: HUMAN_REVIEWED_NON_EVIDENCE -- this is a pilot, not paper evidence. n=91, one model, one dataset.** Every number below is reproduced from an ingested raw prediction file (see Provenance); none is transcribed.

## Headline (presence-question intervention)

Same objective question on original and edited image: *"Is there a clearly visible {object} in the image?"* (45/91 items use a negated-polarity variant -- see Caveats). Edits are single-object remove / occlude / displace that pass quality + low-detectability gates (detectability AUC approx. 0.349, near chance).

- original-image accuracy a = **0.890** (81/91)
- intervention consistency p = **0.176** (answer updates with the change)
- edited-image accuracy = 0.220
- **intervention-consistency gap Delta = a - p = 0.714**
- anytime-valid CS lower bound = **0.331** (> 0.05 threshold), upper bound = 1.000, alpha = 0.05
- certified = **True** (gate errors: none)
- answer-update rate: model gave the SAME yes/no answer on original vs edited in **75/91** items (0.824); it updated only 16.

By edit type:

| edit_type | n | orig acc | consistency | gap |
|---|---|---|---|---|
| displace | 54 | 0.963 | 0.148 | 0.815 |
| occlude | 6 | 0.833 | 0.333 | 0.500 |
| remove | 31 | 0.774 | 0.194 | 0.581 |

Reading: the model answers the presence question correctly on the unedited image 89% of the time, but after the object is edited out it keeps its original answer 82% of the time, so it is consistent with the change only 18% of the time. It largely fails to update.

Positive-only subset (drops the negated questions, n=46): a=0.870, p=0.196, gap=0.674 -- the gap is not a phrasing artifact.

## Decisive confound control (natural absent-object perception)

Same question, NO edits, balanced natural present/absent images, ground-truth ADE20K labels. Rules out "the model never looks and just answers the question's presupposition".

- absent images answered correctly: **60/60** (1.000)
- present images answered correctly: **58/60** (0.967)
- overall: 118 (0.983, n=120)

The model reports NATURAL absence almost perfectly, but fails to register EDITED absence. The gap is a visual-update failure, not a presupposition artifact.

## Claimed (pilot, this run, this model)

- llava-onevision-qwen2-7b-ov fails to update its object-presence decision under low-detectability removal/occlusion/displacement edits, while correctly reporting natural absence (confound-controlled).
- The intervention-consistency gap is certified by anytime-valid CS for this fixed item order (LB 0.331 > 0.05).

## NOT claimed

- NOT paper evidence (HUMAN_REVIEWED_NON_EVIDENCE; pilot n=91; single model; single dataset).
- This report covers only llava-onevision-qwen2-7b-ov; cross-model statements require the multi-model summary (`multimodel_pilot_summary.md`), and each model row is filled only from its own real run.
- No spurious-flip baseline yet: run the CPU spurious-flip control (`data/edits/spurious_flip_control/`) to separate "fails to update" from "insensitive to any edit".
- The negated-polarity presence questions (45/91) are awkwardly phrased and mix polarity; the positive-only subset should be confirmed before any external claim.
- Residual inpainting cues are not yet ruled out as an alternative explanation.

## Blockers before a paper-grade claim

1. Run >=2 more open VLMs (InternVL, LLaVA-OneVision) on the identical 91 items + control.
2. Add a gentle CPU spurious-flip control (control_irrelevant) and a residual-cue probe.
3. Confirm the positive-only presence subset; clean up negated-question phrasing.
4. Scale n beyond the 91-item pilot.
5. Mechanism probes (region-focused / describe-then-answer / object-list prompts).

## Provenance (number -> artifact)

- `presence`: data/results/main_real_200/raw_predictions__llava_onevision_7b/presence__pred_llava_onevision_7b_presence_merged.jsonl  (sha256 `10900a3c992fbc5c...`, 182 records)
- `control`: data/results/main_real_200/raw_predictions__llava_onevision_7b/control__pred_llava_onevision_7b_control_merged.jsonl  (sha256 `f25b6f341a20568f...`, 240 records)

Scored / certification artifacts written alongside this file. Raw image pixels are NOT redistributed (ADE20K pointer-only). No paid services were used.
