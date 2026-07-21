# Main-200 Failure Taxonomy & Qualitative Gallery

**Qualitative, NOT evidence** (`evidence_status = QUALITATIVE_GALLERY_NON_EVIDENCE`). Built from canonical raw predictions over the 91 human-approved presence items. Examples reference image paths + sha256 (pixels not duplicated); machine-readable in `data/results/main_real_200/failure_gallery/gallery.json`.

## Taxonomy counts (of 91)

| category | n matching |
|---|---|
| all_model_failure | 58 |
| full_non_update_after_removal | 25 |
| partial_update_single_model | 15 |
| llava_only_update | 3 |
| natural_absence_success_vs_edited_failure | 13 |
| residual_cue_candidate_uncertain | 25 |
| prompt_polarity_sensitive | pending (needs ablation predictions) |

## Natural-absence vs edited-absence (the headline dissociation)

Absent-object control (natural absence, no edits) vs the edited-absence failures below:

| model | control absent | control present |
|---|---|---|
| `qwen2_5_vl_7b` | 60/60 | 50/60 |
| `internvl_8b` | 58/60 | 58/60 |
| `llava_onevision_7b` | 60/60 | 58/60 |

Models are near-perfect at *natural* absence yet frequently fail to revise after a controlled *edited* removal — that contrast is the qualitative core.

## Example categories

### all_model_failure

- Criteria: all 3 models post-edit-incorrect (edited_correct=False)
- Selection: deterministic: items matching criteria, sorted by item_id, first 3 · matching: 58
  - `preview_pilot_019f0637cabf` (displace, target=sofa): expected edited=no; edited answers [qwen2:yes, internvl:yes, llava:yes]; sha256=`51fbc0ce388c`
  - `preview_pilot_01fc561f2ad1` (displace, target=sofa): expected edited=yes; edited answers [qwen2:no, internvl:no, llava:no]; sha256=`322060fe3144`
  - `preview_pilot_059c9c1b14f2` (displace, target=sofa): expected edited=no; edited answers [qwen2:yes, internvl:yes, llava:yes]; sha256=`6f3ff8c563af`

### full_non_update_after_removal

- Criteria: edit_type=remove AND all 3 models kept their original answer (no update)
- Selection: deterministic: items matching criteria, sorted by item_id, first 3 · matching: 25
  - `preview_pilot_0c14103036aa` (remove, target=table): expected edited=yes; edited answers [qwen2:no, internvl:no, llava:no]; sha256=`f8c7aa43c415`
  - `preview_pilot_1754bf5e0dc4` (remove, target=table): expected edited=yes; edited answers [qwen2:no, internvl:no, llava:no]; sha256=`a17f6b993794`
  - `preview_pilot_299953cec30c` (remove, target=table): expected edited=yes; edited answers [qwen2:no, internvl:no, llava:no]; sha256=`c6baec35a428`

### partial_update_single_model

- Criteria: exactly 1 of 3 models post-edit-correct, other 2 fail
- Selection: deterministic: items matching criteria, sorted by item_id, first 3 · matching: 15
  - `preview_pilot_176c9612c64a` (displace, target=sofa): expected edited=no; edited answers [qwen2:yes, internvl:no, llava:yes]; sha256=`7aec28720f17`
  - `preview_pilot_1ff79de6fa95` (displace, target=sofa): expected edited=no; edited answers [qwen2:no, internvl:yes, llava:yes]; sha256=`333ea80590c7`
  - `preview_pilot_21bcefc89fec` (remove, target=table): expected edited=no; edited answers [qwen2:yes, internvl:no, llava:yes]; sha256=`6d43f7ace796`

### llava_only_update

- Criteria: llava_onevision_7b post-edit-correct AND qwen & internvl both fail
- Selection: deterministic: items matching criteria, sorted by item_id, first 3 · matching: 3
  - `preview_pilot_305c8d329d20` (remove, target=table): expected edited=yes; edited answers [qwen2:no, internvl:no, llava:yes]; sha256=`b00fae21a29f`
  - `preview_pilot_e7a4280b4ffa` (remove, target=table): expected edited=yes; edited answers [qwen2:no, internvl:no, llava:yes]; sha256=`abca82ff7d72`
  - `preview_pilot_ff8eed607a75` (remove, target=table): expected edited=no; edited answers [qwen2:yes, internvl:yes, llava:no]; sha256=`cd310f42704e`

### natural_absence_success_vs_edited_failure

- Criteria: edit_type=remove, gold edited='no', >=2 models fail on edited absence (contrast with absent-object control success rates)
- Selection: deterministic: items matching criteria, sorted by item_id, first 3 · matching: 13
  - `preview_pilot_21bcefc89fec` (remove, target=table): expected edited=no; edited answers [qwen2:yes, internvl:no, llava:yes]; sha256=`6d43f7ace796`
  - `preview_pilot_46e1bd3d5152` (remove, target=table): expected edited=no; edited answers [qwen2:yes, internvl:no, llava:yes]; sha256=`9f0dc5fdd212`
  - `preview_pilot_667aa11a75bc` (remove, target=table): expected edited=no; edited answers [qwen2:yes, internvl:yes, llava:yes]; sha256=`92821cc628a9`

### residual_cue_candidate_uncertain

- Criteria: models DISAGREE (model_fail_count in {1,2}) -> candidate for residual-cue review; NOT an asserted residual cue (no human label yet)
- Selection: deterministic: items matching criteria, sorted by item_id, first 3 · matching: 25
  - `preview_pilot_176c9612c64a` (displace, target=sofa): expected edited=no; edited answers [qwen2:yes, internvl:no, llava:yes]; sha256=`7aec28720f17`
  - `preview_pilot_1ff79de6fa95` (displace, target=sofa): expected edited=no; edited answers [qwen2:no, internvl:yes, llava:yes]; sha256=`333ea80590c7`
  - `preview_pilot_21bcefc89fec` (remove, target=table): expected edited=no; edited answers [qwen2:yes, internvl:no, llava:yes]; sha256=`6d43f7ace796`

### prompt_polarity_sensitive

- Criteria: items whose verdict flips across abl_positive/abl_negative/abl_pixelonly/abl_short
- Selection: pending: requires prompt-ablation predictions (see prompt 08); none yet · matching: 0

## Hard rules honored

- Only human-approved items; only canonical raw predictions for model answers.
- Deterministic selection (recorded criteria); no hand-picking.
- No image pixels duplicated (paths + hashes only).
