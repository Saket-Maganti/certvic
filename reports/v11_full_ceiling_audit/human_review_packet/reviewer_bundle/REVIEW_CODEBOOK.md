# CertVIC V11 blinded pair-review codebook

## Independence and blinding

- Complete only the sheet assigned to you. Do not inspect another rater's sheet.
- Do not discuss ratings until both signed sheets have been returned to the coordinator.
- Pair IDs and A/B order are randomized. Do not infer which image was changed.
- The packet contains no system outputs or prior ratings. Rate only visible content.
- Never review more than one track containing the same pixels. By default the coordinator
  obtains ratings once on `control94` and derives its subset decisions only after both
  sheets are locked. Direct subset review requires a completely disjoint rater pool.
- Leave no required field blank. Use `uncertain` when the image does not support a firm call.
- Use an assigned non-identifying reviewer code and an ISO-8601 UTC completion time.

## Allowed values

| Field | Allowed values | Meaning |
|---|---|---|
| `prompt_unambiguous` | `yes`, `no`, `uncertain` | The question has one clear visual interpretation. |
| `image_answerable` | `yes`, `no`, `uncertain` | The pair contains enough visible evidence to answer the question. |
| `target_visible_a` | `yes`, `no`, `uncertain` | The questioned target is visibly present in image A. |
| `target_visible_b` | `yes`, `no`, `uncertain` | The questioned target is visibly present in image B. |
| `target_unaffected` | `yes`, `no`, `uncertain`, `not_applicable` | For control tracks, whether the questioned target itself is unaffected. Use `not_applicable` only for the intentional intervention track. |
| `expected_answer_relation_valid` | `yes`, `no`, `uncertain` | Whether the visible pair supports the track's intended changed-or-unchanged answer relation. |
| `expected_answer_unchanged` | `yes`, `no`, `uncertain`, `not_applicable` | For control tracks, whether the expected answer should remain unchanged. Use `not_applicable` only for the intentional intervention track. |
| `perturbation_acceptable` | `yes`, `no`, `uncertain` | The change is localized, plausible, and free of a material scene confound. |
| `artifact_severity` | `none`, `minor`, `major`, `uncertain` | Visible editing or patch artifact severity. |
| `retention_decision` | `retain`, `exclude`, `uncertain` | Explicit visual-quality retain/exclude recommendation. |
| `confidence` | `high`, `medium`, `low` | Confidence in the row-level ratings. |

Free-text notes must not contain names or other personal information. Human review verifies
visual validity; it does not by itself turn a diagnostic cohort into paper evidence.
