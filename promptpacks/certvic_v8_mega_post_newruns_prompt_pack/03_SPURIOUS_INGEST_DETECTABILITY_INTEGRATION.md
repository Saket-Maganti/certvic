# V8 Spurious Ingest, Detectability Gate, and Specificity Integration

You are Codex operating inside the CertVIC repository as a careful ML systems engineer, reproducibility lead, statistical audit lead, and CVPR paper-hardening agent.

Repo:

/Users/saketmaganti/Projects/certVIC

New external outputs:

kaggleoutputs/newruns

Critical context:
- The V7/T4×2 runbook-prep stage created Kaggle notebooks and bundles, but did not create model results.
- The user now says all four phase GPU runs were completed using the main200 bundle.
- Expected run families: spurious, perception_scaled, polarity, mechanism.
- Expected providers: qwen2_5_vl_7b, internvl_8b, llava_onevision_7b.
- Old external audit said the project was infrastructure-complete with a real 91-item pilot but not CVPR-main ready because scaled evidence, human validation, spurious/edit-realism controls, and paper compilation were missing.
- V8 must ingest and verify the new Kaggle outputs, not fabricate them.

Hard constraints:
- No fake predictions, no fake results, no fake human review, no fake citations.
- Do not weaken gates or thresholds.
- Do not mark paper_evidence=true unless existing repo policy explicitly permits it after real gates pass.
- Preserve old/canonical V7 artifacts; never overwrite without provenance.
- If a required artifact is missing, mark the step BLOCKED with exact missing files and next commands.
- All tests must remain CPU/local.
- No git commit unless explicitly asked.
- Keep result language pilot-only unless evidence gates explicitly promote a claim.


Task:
Close the highest-priority specificity blocker if real spurious predictions exist.

Inputs:

```text
data/results/main_real_200/kaggle_spurious/pred_qwen2_5_vl_7b_spurious_merged.jsonl
data/results/main_real_200/kaggle_spurious/pred_internvl_8b_spurious_merged.jsonl
data/results/main_real_200/kaggle_spurious/pred_llava_onevision_7b_spurious_merged.jsonl
data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl
```

Inspect CLIs:

```bash
python3 scripts/pilot_report_from_raw.py --help
python3 -m certvic.validation.edit_detectability --help || true
python3 -m certvic.v7.spurious_control_integration --help || true
```

Run per-provider spurious ingestion/report refresh:

```bash
python3 scripts/pilot_report_from_raw.py --provider qwen2_5_vl_7b --model-name Qwen/Qwen2.5-VL-7B-Instruct --run-label qwen2_5_vl_7b --raw-spurious data/results/main_real_200/kaggle_spurious/pred_qwen2_5_vl_7b_spurious_merged.jsonl
python3 scripts/pilot_report_from_raw.py --provider internvl_8b --model-name OpenGVLab/InternVL2-8B --run-label internvl_8b --raw-spurious data/results/main_real_200/kaggle_spurious/pred_internvl_8b_spurious_merged.jsonl
python3 scripts/pilot_report_from_raw.py --provider llava_onevision_7b --model-name llava-hf/llava-onevision-qwen2-7b-ov-hf --run-label llava_onevision_7b --raw-spurious data/results/main_real_200/kaggle_spurious/pred_llava_onevision_7b_spurious_merged.jsonl
```

Run CPU detectability/quality gate using the real CLI. Preferred command if valid:

```bash
python3 -m certvic.validation.edit_detectability --tasks data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl --out-dir data/results/spurious_flip_control/edit_detectability
```

Then run:

```bash
python3 -m certvic.v7.spurious_control_integration
```

Create:

```text
data/results/main_real_200/v8_upgrade/SPURIOUS_SPECIFICITY_CONTROL_REPORT.md
data/results/main_real_200/v8_upgrade/spurious_specificity_control_report.json
```

Report per-provider spurious flip rate, pass/fail against repo gate, detectability/quality status, integration status, missing files, and caveat that this is a control result not main-scale evidence.

Update task ledger entries `V8_03_spurious_ingest_and_detectability` and `V8_04_spurious_control_integration`.
