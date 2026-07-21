# Main-200 Prompt-Polarity & Phrasing Ablation Plan

**Status: ablation tasks generated (CPU), not yet run, NOT evidence**
(`evidence_status = PROMPT_ABLATION_NON_EVIDENCE`).

A reviewer may argue the post-edit failure depends on awkward prompt polarity (the v2 set
mixes positive and negated phrasing). These ablations test whether the effect survives clean,
single-phrasing question forms over the **same 91 reviewed items**. No GPU inference runs here.

Generate / regenerate:
```bash
python3 scripts/build_prompt_ablation_tasks.py
```
→ `data/results/main_real_200/prompt_ablations/<family>/tasks.jsonl` (+ `summary.json`).

## Ablation forms (distinct run labels)

| family | run label | polarity | question |
|---|---|---|---|
| positive | `abl_positive` | positive | "Is there a clearly visible {obj} in the image? Answer yes or no." |
| negative | `abl_negative` | **negative** | "Is the {obj} absent from the image? Answer yes or no." |
| pixel_only | `abl_pixelonly` | positive | "Answer from visible pixels only, not scene context: is there a clearly visible {obj}?" |
| short | `abl_short` | positive | "Visible {obj}? yes/no." |

Each family has **182 tasks** = 91 items × {original, edited} variants, so the edit-and-recheck
structure is preserved.

## Polarity validator (the important part)

Gold answers must stay correct under phrasing changes. The **negated** form inverts the gold
relative to the presence (base) gold:

- positive / pixel_only / short → `gold = base_gold` (presence answer as-is)
- negative ("is {obj} absent?") → `gold = invert(base_gold)`

Worked example (`table`, remove edit): original image is present →
positive gold `yes`, negative gold `no`; edited image target gone →
positive gold `no`, negative gold `yes`.

`build_prompt_ablation_tasks.py` validates **every** task against this rule and **fails
closed** (refuses to write manifests) if any gold is inconsistent with its polarity. The
current run reports `polarity_validation: passed`.

## Provenance & integrity

- Every task traces to its reviewed item (`item_id`, `edit_id`, `source_id`).
- Each task carries a `task_hash` (stable sha256 over item_id + run_label + variant +
  question + gold) and `base_gold` for auditability.
- Distinct `run_label` per family keeps each ablation's predictions in its own scored report.

## Interpretation (after real predictions land)

If the gap between original-image accuracy and post-edit consistency persists across the
positive, pixel-only, and short forms — and the negated form shows the inverted-but-consistent
pattern — then the effect is not an artifact of one awkward phrasing. Keep
`evidence_status = PROMPT_ABLATION_NON_EVIDENCE` until scored from real predictions.

## Next step (only if you want to run)

Run each family's `tasks.jsonl` on the free Kaggle VLM notebook per provider (set the matching
`run_label`), then score locally against `gold_answer`.
