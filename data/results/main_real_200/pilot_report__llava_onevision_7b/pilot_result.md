# CertVIC Pilot Result -- llava-onevision-qwen2-7b-ov (single model)

Generated: 2026-07-08T09:30:49.777468+00:00

**Status: REAL PILOT. Provenance: real ADE20K images + real llava-hf/llava-onevision-qwen2-7b-ov-hf (open weights, free Kaggle T4x2). NOT synthetic / NOT smoke / NOT mock.**

**evidence_status: HUMAN_REVIEWED_NON_EVIDENCE -- this is a pilot, not paper evidence. n=91, one model, one dataset.** Every number below is reproduced from an ingested raw prediction file (see Provenance); none is transcribed.

## Headline (presence-question intervention)

Same objective question on original and edited image: *"Is there a clearly visible {object} in the image?"* (45/91 items use a negated-polarity variant -- see Caveats). Edits are single-object remove / occlude / displace that pass quality + low-detectability gates (detectability AUC approx. 0.349, near chance).

- original-image accuracy a = **0.890** (81/91)
- intervention consistency p = **0.143** (answer updates with the change)
- edited-image accuracy = 0.220
- **intervention-consistency gap Delta = a - p = 0.747**
- anytime-valid CS lower bound = **0.364** (> 0.05 threshold), upper bound = 1.000, alpha = 0.05
- certified = **False** (gate errors: ['certified claim blocked: evidence_status is UNKNOWN', 'n_overall 91 < min_n_overall 150', 'family affordance_reachability n 31 < min_n_by_family 40', 'family occlusion_safety n 6 < min_n_by_family 40', 'control_spurious_flip_rate missing; specificity gate is required', 'non-evidence status present: UNKNOWN'])
- answer-update rate: model gave the SAME yes/no answer on original vs edited in **75/91** items (0.824); it updated only 16.

By edit type:

| edit_type | n | orig acc | consistency | gap |
|---|---|---|---|---|
| displace | 54 | 0.963 | 0.148 | 0.815 |
| occlude | 6 | 0.833 | 0.333 | 0.500 |
| remove | 31 | 0.774 | 0.097 | 0.677 |

Reading: the model answers the presence question correctly on the unedited image 89% of the time, but after the object is edited out it keeps its original answer 82% of the time, so it is consistent with the change only 14% of the time. It largely fails to update.

Positive-only subset (drops the negated questions, n=46): a=0.870, p=0.196, gap=0.674 -- the gap is not a phrasing artifact.

## Decisive confound control (natural absent-object perception)

Same question, NO edits, balanced natural present/absent images, ground-truth ADE20K labels. Rules out "the model never looks and just answers the question's presupposition".

- absent images answered correctly: **60/60** (1.000)
- present images answered correctly: **58/60** (0.967)
- overall: 118 (0.983, n=120)

The model reports NATURAL absence almost perfectly, but fails to register EDITED absence. The gap is a visual-update failure, not a presupposition artifact.

Scaled + held-out replication (validation (held-out), 369 items, 8 objects): absent 156/177 (0.881), present 188/192 (0.979). The perception result holds at scale on unseen images.

## Specificity control (spurious flips under irrelevant edits)

Same no_change pairs, but the edit is an irrelevant blur+jitter patch placed in an OBJECT-FREE region (object pixels untouched) -- the correct answer stays "yes". A model that flips here is reacting to irrelevant pixels.

- spurious-flip rate = **0.032** (3/94), gate <= 0.10: **PASS**
- yes->no flips among correctly-seen originals: 1/88

This observed rate is a descriptive specificity diagnostic. A passing rate supports, but does not by itself establish, a fully policy-qualified claim; a failing rate remains a blocker. (Crude CPU perturbation; a diffusion-realistic irrelevant edit is future work.)

## Claimed (pilot, this run, this model)

- llava-onevision-qwen2-7b-ov fails to update its object-presence decision under low-detectability removal/occlusion/displacement edits, while correctly reporting natural absence (confound-controlled).
- The numeric anytime-valid CS threshold is crossed for this fixed item order (LB 0.364 > 0.05), but full policy certification is blocked.

## NOT claimed

- NOT paper evidence (MACHINE_ASSISTED_PRELIMINARY; pilot n=91; single model; single dataset).
- This report covers only llava-onevision-qwen2-7b-ov; cross-model statements require the multi-model summary (`multimodel_pilot_summary.md`), and each model row is filled only from its own real run.
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
- `spurious`: data/results/main_real_200/raw_predictions__llava_onevision_7b/spurious__pred_llava_onevision_7b_spurious_merged.jsonl  (sha256 `81d40e6942b8db14...`, 188 records)
- `perception_scaled`: data/results/main_real_200/raw_predictions__llava_onevision_7b/perception_scaled__pred_llava_onevision_7b_perception_scaled_merged.jsonl  (sha256 `e42223879642fc4b...`, 738 records)

Scored / certification artifacts written alongside this file. Raw image pixels are NOT redistributed (ADE20K pointer-only). No paid services were used.
