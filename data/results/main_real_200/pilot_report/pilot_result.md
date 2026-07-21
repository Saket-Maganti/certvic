# CertVIC Pilot Result -- Qwen2.5-VL-7B (single model)

Generated: 2026-07-08T09:29:14.565271+00:00

**Status: REAL PILOT. Provenance: real ADE20K images + real Qwen/Qwen2.5-VL-7B-Instruct (open weights, free Kaggle T4x2). NOT synthetic / NOT smoke / NOT mock.**

**evidence_status: HUMAN_REVIEWED_NON_EVIDENCE -- this is a pilot, not paper evidence. n=91, one model, one dataset.** Every number below is reproduced from an ingested raw prediction file (see Provenance); none is transcribed.

## Headline (presence-question intervention)

Same objective question on original and edited image: *"Is there a clearly visible {object} in the image?"* (45/91 items use a negated-polarity variant -- see Caveats). Edits are single-object remove / occlude / displace that pass quality + low-detectability gates (detectability AUC approx. 0.349, near chance).

- original-image accuracy a = **0.923** (84/91)
- intervention consistency p = **0.176** (answer updates with the change)
- edited-image accuracy = 0.253
- **intervention-consistency gap Delta = a - p = 0.747**
- anytime-valid CS lower bound = **0.364** (> 0.05 threshold), upper bound = 1.000, alpha = 0.05
- certified = **False** (gate errors: ['certified claim blocked: evidence_status is UNKNOWN', 'n_overall 91 < min_n_overall 150', 'family affordance_reachability n 31 < min_n_by_family 40', 'family occlusion_safety n 6 < min_n_by_family 40', 'control_spurious_flip_rate missing; specificity gate is required', 'non-evidence status present: UNKNOWN'])
- answer-update rate: model gave the SAME yes/no answer on original vs edited in **75/91** items (0.824); it updated only 16.

By edit type:

| edit_type | n | orig acc | consistency | gap |
|---|---|---|---|---|
| displace | 54 | 0.926 | 0.259 | 0.667 |
| occlude | 6 | 0.833 | 0.333 | 0.500 |
| remove | 31 | 0.935 | 0.000 | 0.935 |

Reading: the model answers the presence question correctly on the unedited image 92% of the time, but after the object is edited out it keeps its original answer 82% of the time, so it is consistent with the change only 18% of the time. It largely fails to update -- and for full removals it never updates (0/31).

Positive-only subset (drops the negated questions, n=46): a=0.870, p=0.217, gap=0.652 -- the gap is not a phrasing artifact.

## Decisive confound control (natural absent-object perception)

Same question, NO edits, balanced natural present/absent images, ground-truth ADE20K labels. Rules out "the model never looks and just answers the question's presupposition".

- absent images answered correctly: **60/60** (1.000)
- present images answered correctly: **50/60** (0.833)
- overall: 110 (0.917, n=120)

The model reports NATURAL absence almost perfectly, but fails to register EDITED absence. The gap is a visual-update failure, not a presupposition artifact.

Scaled + held-out replication (validation (held-out), 369 items, 8 objects): absent 165/177 (0.932), present 166/192 (0.865). The perception result holds at scale on unseen images.

## Specificity control (spurious flips under irrelevant edits)

Same no_change pairs, but the edit is an irrelevant blur+jitter patch placed in an OBJECT-FREE region (object pixels untouched) -- the correct answer stays "yes". A model that flips here is reacting to irrelevant pixels.

- spurious-flip rate = **0.128** (12/94), gate <= 0.10: **FAIL**
- yes->no flips among correctly-seen originals: 12/87

This observed rate is a descriptive specificity diagnostic. A passing rate supports, but does not by itself establish, a fully policy-qualified claim; a failing rate remains a blocker. (Crude CPU perturbation; a diffusion-realistic irrelevant edit is future work.)

## Secondary, CONFOUNDED arm (affordance/support/occlusion questions)

The earlier abstract questions ("Can the person use the target object?", "Is the upper object physically supported?") give original accuracy a = **0.407** (approx. chance), gap 0.319. Because the model is not reliably correct on the originals, this arm is NOT certifiable and is reported descriptively only. The presence framing supersedes it.

## Claimed (pilot, this run, this model)

- Qwen2.5-VL-7B fails to update its object-presence decision under low-detectability removal/occlusion/displacement edits, while correctly reporting natural absence (confound-controlled).
- The numeric anytime-valid CS threshold is crossed for this fixed item order (LB 0.364 > 0.05), but full policy certification is blocked.

## NOT claimed

- NOT paper evidence (MACHINE_ASSISTED_PRELIMINARY; pilot n=91; single model; single dataset).
- This report covers only Qwen2.5-VL-7B; cross-model statements require the multi-model summary (`multimodel_pilot_summary.md`), and each model row is filled only from its own real run.
- The negated-polarity presence questions (45/91) are awkwardly phrased and mix polarity; the positive-only subset should be confirmed before any external claim.
- Residual inpainting cues are not yet ruled out as an alternative explanation.

## Blockers before a paper-grade claim

1. Run >=2 more open VLMs (InternVL, LLaVA-OneVision) on the identical 91 items + control.
2. Add a gentle CPU spurious-flip control (control_irrelevant) and a residual-cue probe.
3. Confirm the positive-only presence subset; clean up negated-question phrasing.
4. Scale n beyond the 91-item pilot.
5. Mechanism probes (region-focused / describe-then-answer / object-list prompts).

## Provenance (number -> artifact)

- `presence`: data/results/main_real_200/raw_predictions/presence__pred_qwen2_5_vl_7b_merged.jsonl  (sha256 `becb2b59f6a4199f...`, 182 records)
- `control`: data/results/main_real_200/raw_predictions/control__pred_qwen2_5_vl_7b_merged.jsonl  (sha256 `a78c4b75aa71d4a0...`, 240 records)
- `affordance`: data/results/main_real_200/raw_predictions/affordance__pred_qwen2_5_vl_7b_merged.jsonl  (sha256 `f89ba378995c54ca...`, 182 records)
- `spurious`: data/results/main_real_200/raw_predictions/spurious__pred_qwen2_5_vl_7b_spurious_merged.jsonl  (sha256 `4be34d6826587eca...`, 188 records)
- `perception_scaled`: data/results/main_real_200/raw_predictions/perception_scaled__pred_qwen2_5_vl_7b_perception_scaled_merged.jsonl  (sha256 `14def3f2758bd8ed...`, 738 records)

Scored / certification artifacts written alongside this file. Raw image pixels are NOT redistributed (ADE20K pointer-only). No paid services were used.
