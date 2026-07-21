# main_real_200 — canonical result pointer

**Canonical pilot result: [`pilot_report/pilot_result.md`](pilot_report/pilot_result.md)**
(machine-readable: `pilot_report/pilot_result.json`). Regenerate with:

```
python3 scripts/pilot_report_from_raw.py
```

This is a **pilot** (`evidence_status = HUMAN_REVIEWED_NON_EVIDENCE`), real ADE20K + real
Qwen — **not** synthetic/smoke. Not paper evidence.

## Multi-model (pilot)

`pilot_report_from_raw.py` is model-agnostic. Each model gets its own report dir and the
cross-model table is regenerated into `multimodel_pilot_summary.{md,csv,json}` — unrun
models show `not_run` with **no** numbers (never copied from another model). Run a new model:

```
python3 scripts/pilot_report_from_raw.py --provider internvl_8b \
  --model-name OpenGVLab/InternVL2-8B --run-label internvl_8b \
  --raw-presence /tmp/internvl/pred_internvl_8b_merged.jsonl \
  --raw-control  /tmp/internvl_ctrl/pred_internvl_8b_merged.jsonl
```

The provider-match gate refuses if the raw preds' `provider_name` ≠ `--provider`, so one
model's predictions can never be filed under another's row. Status so far: **qwen2_5_vl_7b =
run; internvl_8b, llava_onevision_7b = not_run.**

## Two intervention arms exist — do not confuse them

| arm | question style | raw preds | original acc | gap | certified | status |
|---|---|---|---|---|---|---|
| **presence (headline)** | "Is there a clearly visible {obj}?" | `raw_predictions/presence__*` | 0.923 | 0.747 | **yes** (CS LB 0.364) | use this |
| affordance (secondary) | "Can the person use the target object?" etc. | `raw_predictions/affordance__*` | 0.407 (~chance) | 0.297 | no | confounded; descriptive only |

The presence arm is the methodologically clean one (high original accuracy → the gap is
interpretable as a visual-update failure). The affordance arm is the earlier run whose low
original accuracy (~chance) confounds the gap; kept for transparency, not certified.

Decisive confound control (natural absent-object perception, no edits): **60/60 absent
correct, 50/60 present** — see `pilot_report/absent_object_control.json`. Rules out the
"answers the question's presupposition without looking" confound.

## ⚠ `final_report/` and `final_report_v2/` are NOT canonical

Both were produced by the smoke-template builder (`certvic.reporting.build_report`), whose
`report.md` is hard-coded to say *"MOCK_ONLY synthetic fixture report"*. That narrative is
**wrong** for this real data. Their `certification.json` / `summary.json` **numbers are real**
(`final_report` = affordance/v1; `final_report_v2` = presence/v2), but the markdown is a
template artifact. Use `pilot_report/` instead.

## Provenance

Raw Qwen2.5-VL predictions were generated on free Kaggle T4×2 and originally lived only in
ephemeral `/tmp`. They are now ingested + sha256-locked under `raw_predictions/`
(`raw_predictions/provenance.json`). Every number in `pilot_result.md` is recomputed from
those files by the script above, not transcribed. ADE20K image pixels are not redistributed.
