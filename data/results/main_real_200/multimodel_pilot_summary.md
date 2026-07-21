# CertVIC Multi-Model Pilot Summary

**PILOT ONLY (evidence_status=HUMAN_REVIEWED_NON_EVIDENCE, paper_evidence=False).** 3/3 models run. Rows marked `not_run` are placeholders with no numbers -- they are NOT filled from any other model.

Presence-question intervention (same 91 reviewed items) + absent-object control (120 items). `gap = a - p`; `certified` = anytime-valid CS lower bound > 0.05 for that model's own run.

| model | status | n | a (orig acc) | p (consistency) | gap | CS LB | certified | control absent | control present | spurious flip |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen/Qwen2.5-VL-7B-Instruct | run | 91 | 0.923 | 0.176 | 0.747 | 0.364 | False | 60/60 | 50/60 | 0.128 |
| OpenGVLab/InternVL2-8B | run | 91 | 0.923 | 0.099 | 0.824 | 0.441 | False | 58/60 | 58/60 | 0.011 |
| llava-hf/llava-onevision-qwen2-7b-ov-hf | run | 91 | 0.890 | 0.143 | 0.747 | 0.364 | False | 60/60 | 58/60 | 0.032 |

Sources (per-model real reports):

- `qwen2_5_vl_7b`: data/results/main_real_200/pilot_report/pilot_result.json
- `internvl_8b`: data/results/main_real_200/pilot_report__internvl_8b/pilot_result.json
- `llava_onevision_7b`: data/results/main_real_200/pilot_report__llava_onevision_7b/pilot_result.json

Cross-model interpretation is descriptive only; a single model's certified gap is not cross-model evidence. Run the remaining models with `scripts/pilot_report_from_raw.py --provider <id> --model-name <hf-id> --run-label <id> --raw-presence ... --raw-control ...`.
