# Local ingest and report commands

Place downloaded prediction files into these local directories before running commands:

- Spurious: `data/results/main_real_200/kaggle_spurious/`
- Scaled perception: `data/results/main_real_200/kaggle_perception_scaled/`
- Polarity: `data/results/main_real_200/kaggle_polarity/`
- Mechanism: `data/results/main_real_200/kaggle_mechanism/`

Provider/model-name pairs:

- `qwen2_5_vl_7b` -> `Qwen/Qwen2.5-VL-7B-Instruct`
- `internvl_8b` -> `OpenGVLab/InternVL2-8B`
- `llava_onevision_7b` -> `llava-hf/llava-onevision-qwen2-7b-ov-hf`

## After spurious

For each provider:

```bash
python3 scripts/pilot_report_from_raw.py \
  --provider <provider> \
  --model-name <model_name> \
  --run-label <provider> \
  --raw-spurious data/results/main_real_200/kaggle_spurious/pred_<provider>_spurious_merged.jsonl
```

Then:

```bash
python3 -m certvic.validation.edit_detectability \
  --tasks data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl \
  --out-dir data/results/spurious_flip_control/edit_detectability

python3 -m certvic.v7.spurious_control_integration
```

## After scaled perception

For each provider:

```bash
python3 scripts/pilot_report_from_raw.py \
  --provider <provider> \
  --model-name <model_name> \
  --run-label <provider> \
  --raw-perception-scaled data/results/main_real_200/kaggle_perception_scaled/pred_<provider>_perception_scaled_merged.jsonl
```

## After polarity

The current repo has a real ablation reporter CLI, but it reports baseline
construct-validity ablations from a `run_ablations` prediction directory; it does
not directly score the new VLM polarity JSONL by itself. Stage the downloaded
VLM files in `data/results/main_real_200/kaggle_polarity/`, then run the existing
CPU baseline/reporting path with explicit args:

```bash
python3 -m certvic.eval.run_ablations \
  --tasks data/results/main_real_200/pilot_eval_taskitems_v2.jsonl \
  --out-dir data/results/main_real_200/construct_validity_ablations \
  --max-items 91 \
  --seed 0

python3 -m certvic.reporting.ablations \
  --pred-dir data/results/main_real_200/construct_validity_ablations \
  --tasks data/results/main_real_200/pilot_eval_taskitems_v2.jsonl \
  --out-dir data/results/main_real_200/construct_validity_ablation_report
```

Do not invent polarity metrics from the staged VLM JSONL until a dedicated scorer exists.

## After mechanism

For each provider:

```bash
python3 -m certvic.mechanisms.intervention_analysis \
  --baseline data/results/main_real_200/pair_scores_v2.jsonl \
  --intervention data/results/main_real_200/kaggle_mechanism/pred_<provider>_mechanism.jsonl \
  --out-dir data/results/main_real_200/mechanism_<provider>
```

## Final audits

```bash
python3 scripts/build_multimodel_summary.py
python3 -m certvic.v7.post_result_reviewer_attack_audit
python3 -m certvic.v7.v7_post3model_final_audit
python3 -m certvic.validation.claim_language_guard \
  --root docs \
  --out data/results/claim_language_guard_after_remaining_runs.json
python3 -m certvic.security.release_privacy_audit \
  --root . \
  --out data/results/privacy_audit_after_remaining_runs.json
python3 -m pytest -q
```
