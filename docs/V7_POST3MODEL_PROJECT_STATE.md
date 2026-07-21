# V7 Post-3-Model Project State

**Status: strong pilot, not paper-grade yet.** Claim level = **pilot only**
(`evidence_status = HUMAN_REVIEWED_NON_EVIDENCE`, `paper_evidence = false`).

Machine-readable companion: [`data/results/main_real_200/v7_post3model_state.json`](../data/results/main_real_200/v7_post3model_state.json)
(numbers below are derived from canonical artifacts, not transcribed by hand).

This memo is the working context for the rest of the V7 post-3-model elevation pack. It
lists the canonical artifacts, the current 3-model result, what is real vs pilot-only,
what is blocked, what must not be touched, and the exact next step.

---

## Scientific core (one line)

Open VLMs can **detect natural object absence** (absent-object control) but **often fail
to revise a presence judgment after a controlled, low-detectability removal / occlusion /
displacement edit**. This dissociation replicates across three open VLMs under the pilot
protocol.

---

## Current 3-model result (pilot, presence arm — the clean headline arm)

Same 91 reviewed presence/intervention items; same 120-item absent-object control; same
protocol. `Δ = a − p` (gap); `certified` = anytime-valid CS lower bound > 0.05 for that
model's own run.

| model | provider | n | a (orig acc) | p (consistency) | Δ gap | CS LB | CS UB | certified | absent | present |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen/Qwen2.5-VL-7B-Instruct | `qwen2_5_vl_7b` | 91 | 0.923 | 0.176 | 0.747 | 0.364 | 1.0 | yes | 60/60 | 50/60 |
| OpenGVLab/InternVL2-8B | `internvl_8b` | 91 | 0.923 | 0.099 | 0.824 | 0.441 | 1.0 | yes | 58/60 | 58/60 |
| llava-hf/llava-onevision-qwen2-7b-ov-hf | `llava_onevision_7b` | 91 | 0.890 | 0.176 | 0.714 | 0.331 | 1.0 | yes | 60/60 | 58/60 |

Edit-detectability gate: AUC = 0.349 (below ~0.5 chance ⇒ edits are not trivially
detectable), quality passed, gate = **GO** (`go_no_go.json`).

Interpretation rule: cross-model agreement is **descriptive**; a single model's certified
gap is not by itself cross-model evidence. All three are certified *under the pilot
protocol* only.

---

## Canonical artifacts (the only files that may be cited)

**Per-model reports** (each self-identifies its `provider`; numbers recomputed from raw preds):
- `data/results/main_real_200/pilot_report/pilot_result.json` (+`.md`) — Qwen2.5-VL-7B
- `data/results/main_real_200/pilot_report__internvl_8b/pilot_result.json` — InternVL2-8B
- `data/results/main_real_200/pilot_report__llava_onevision_7b/pilot_result.json` — LLaVA-OneVision-7B

**Cross-model summary** (regenerated, never hand-edited):
- `data/results/main_real_200/multimodel_pilot_summary.{json,md,csv}`

**Raw predictions** (sha256-locked, one dir per model):
- `data/results/main_real_200/raw_predictions/` (Qwen), `…__internvl_8b/`, `…__llava_onevision_7b/`

**Inputs / gates:**
- Reviewed presence tasks: `data/results/main_real_200/pilot_eval_tasks_reviewed_v2.jsonl` (91 approved)
- Presence task-items: `data/results/main_real_200/pilot_eval_taskitems_v2.jsonl`
- Absent-object control: `data/results/main_real_200/pilot_report/absent_object_control.json`
- `go_no_go.json`, `reviewed_summary.json`, `score_summary_v2.json`

**Regenerate everything** (no numbers are transcribed; all recomputed):
```bash
python3 scripts/pilot_report_from_raw.py      # per-model report from raw preds
python3 scripts/build_multimodel_summary.py   # cross-model table
```

---

## ⚠ Non-canonical — must NOT be used as results

- `data/results/main_real_200/final_report/` and `final_report_v2/` — produced by the
  smoke-template builder (`certvic.reporting.build_report`); their `report.md` is
  hard-coded to say *"MOCK_ONLY synthetic fixture report"*. The `certification.json` /
  `summary.json` **numbers are real** (`final_report` = affordance/v1, `final_report_v2` =
  presence/v2), but the markdown narrative is a template artifact. **Cite `pilot_report*/`
  instead.**
- The **affordance intervention arm** (original accuracy ≈ 0.41, near chance) is
  **confounded** and **not certified** — descriptive only. The headline is the
  **presence** arm.

---

## Reviewer-critical blockers (what stands between pilot and paper)

1. **Specificity control — BLOCKED (high).** The spurious-flip / `control_irrelevant` arm
   has images + a task manifest built (`data/edits/spurious_flip_control/`, 189 files) but
   **no VLM predictions, no quality/detectability report, no `control_irrelevant_report/`**.
   Until those land, the objection *"models are sticky under any perturbation"* is
   unanswered. Integrate via **V7 prompt 14** once predictions exist — do not fabricate.
2. **Scale (high).** n=91 is a strong pilot but below CVPR main-claim scale.
3. **Single dataset (medium).** ADE20K only; second-domain readiness pending.
4. **Single-rater review / no IAA (medium).** No inter-annotator agreement yet.
5. **Mechanism (medium).** Context-anchoring vs residual-cue vs prompt-prior not yet
   disentangled by probes.
6. **Residual cue (medium).** No human audit yet of whether edited images leak subtle traces.
7. **Prompt polarity (low).** v2 tasks mix positive/negated phrasing; needs an ablation.

---

## Do not touch

- `pilot_report*/`, `raw_predictions*/`, `multimodel_pilot_summary.*` — regenerate via the
  scripts above; never hand-edit.
- Any experimental number in a canonical artifact.
- The spurious-flip control work in progress (separate effort) — integrate, don't duplicate.

---

## Exact next step

**Highest-leverage scientific step:** obtain the **spurious-flip / `control_irrelevant`
VLM predictions** for all three models (free Kaggle T4×2), then integrate:
```bash
# After running the Kaggle VLM notebook on data/edits/spurious_flip_control/ per provider:
python3 scripts/pilot_report_from_raw.py --provider <id> --model-name <hf-id> \
  --run-label <id> --raw-presence ... --raw-control ... --raw-spurious <control_preds>.jsonl
```

**Immediate CPU step (this pack):** V7 prompt 01 — build the canonical **result ledger +
audit** so every pilot number is hash-locked to its source artifact before any scaling:
```bash
python3 -m certvic.v7.result_ledger_audit --ledger registry/results/main200_pilot_result_ledger.json
```
