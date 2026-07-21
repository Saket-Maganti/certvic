# CertVIC Main-200 Multi-Model Pilot Report

**PILOT ONLY** (`evidence_status = MACHINE_ASSISTED_PRELIMINARY`, `paper_evidence = false`). 3/3 registered open VLMs run. All numbers are recomputed from canonical per-model `pilot_result.json` files by `scripts/build_main200_paper_tables.py` — none are transcribed.

Each model's anytime-valid CS lower bound crosses the numeric 0.05 threshold. None is fully policy-certified: n=91 is below the 150-item minimum, two task families are underpowered, specificity/review gates remain unresolved, and the evidence class is non-paper.

## Table 1 — Presence-intervention (headline arm), same 91 reviewed items

`Δ = a − p`, where `a` = original-image accuracy and `p` = post-edit answer consistency.

| Model | Provider | n | a | p | Δ | CS LB | CS UB | CS threshold | Full certified | Parse fail |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen/Qwen2.5-VL-7B-Instruct | `qwen2_5_vl_7b` | 91 | 0.9231 | 0.1758 | 0.7473 | 0.364 | 1.0 | True | False | 0.0 |
| OpenGVLab/InternVL2-8B | `internvl_8b` | 91 | 0.9231 | 0.0989 | 0.8242 | 0.4409 | 1.0 | True | False | 0.0 |
| llava-hf/llava-onevision-qwen2-7b-ov-hf | `llava_onevision_7b` | 91 | 0.8901 | 0.1429 | 0.7473 | 0.364 | 1.0 | True | False | 0.0 |

CSV: `tables/main200_multimodel_results.csv` · TeX: `tables/main200_multimodel_results.tex`

## Table 2 — Absent-object control (natural absence, no edits)

Rules out the *answers-the-presupposition-without-looking* confound: when the object is naturally absent, all three models correctly say "no" at high rates.

| Model | Provider | absent acc | present acc | n absent | n present |
|---|---|---|---|---|---|
| Qwen/Qwen2.5-VL-7B-Instruct | `qwen2_5_vl_7b` | 60/60 (1.0) | 50/60 (0.8333) | 60 | 60 |
| OpenGVLab/InternVL2-8B | `internvl_8b` | 58/60 (0.9667) | 58/60 (0.9667) | 60 | 60 |
| llava-hf/llava-onevision-qwen2-7b-ov-hf | `llava_onevision_7b` | 60/60 (1.0) | 58/60 (0.9667) | 60 | 60 |

CSV: `tables/main200_control_results.csv`

## Table 3 — Per-edit-type (presence arm)

`control_irrelevant` is the spurious-flip specificity arm. If populated, `consistency` is 1 - spurious-flip-rate and `status` records the configured gate result. A `gate_fail` row remains a blocker; prediction existence alone is not a pass.

| Model | Edit type | n | original acc | consistency | gap | status |
|---|---|---|---|---|---|---|
| `qwen2_5_vl_7b` | remove | 31 | 0.9355 | 0.0 | 0.9355 | run |
| `qwen2_5_vl_7b` | occlude | 6 | 0.8333 | 0.3333 | 0.5 | run |
| `qwen2_5_vl_7b` | displace | 54 | 0.9259 | 0.2593 | 0.6667 | run |
| `qwen2_5_vl_7b` | control_irrelevant | 94 |  | 0.8723 |  | gate_fail |
| `internvl_8b` | remove | 31 | 0.8065 | 0.0 | 0.8065 | run |
| `internvl_8b` | occlude | 6 | 0.8333 | 0.3333 | 0.5 | run |
| `internvl_8b` | displace | 54 | 1.0 | 0.1296 | 0.8704 | run |
| `internvl_8b` | control_irrelevant | 94 |  | 0.9894 |  | gate_pass |
| `llava_onevision_7b` | remove | 31 | 0.7742 | 0.0968 | 0.6774 | run |
| `llava_onevision_7b` | occlude | 6 | 0.8333 | 0.3333 | 0.5 | run |
| `llava_onevision_7b` | displace | 54 | 0.963 | 0.1481 | 0.8148 | run |
| `llava_onevision_7b` | control_irrelevant | 94 |  | 0.9681 |  | gate_pass |

CSV: `tables/main200_per_edit_type.csv`

## What this report does and does not claim

- **Does:** report replicated numeric CS-threshold crossings and descriptive gaps between original-image accuracy and post-edit consistency on 91 machine-assisted preliminary ADE20K items across three open VLMs, alongside a natural-absence diagnostic.
- **Does not:** assert a paper-grade or general result. Open blockers: spurious-flip specificity control, scale (n=91), single dataset, single-rater review/IAA, mechanism, prompt polarity. See `docs/V7_POST3MODEL_PROJECT_STATE.md`.
