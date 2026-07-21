# CertVIC Codex V2 Prompt 13 — Open-Model Tiny Eval and Scoring Path

Do not use paid APIs. Do not use paid cloud. Do not run heavy model inference in tests. Do not make claims until gates pass.

## Goal

Create a safe command path for tiny reviewed-task VLM evaluation and scoring on free local/Kaggle compute.

## Tasks

1. Add command:

   `python3 -m certvic.pipeline.run_tiny_eval --config configs/tiny_reviewed_eval.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --provider qwen2_5_vl_7b --out-dir data/results/tiny_eval_qwen --max-items 20`

2. Stages:
   - preflight
   - run_eval
   - score_predictions
   - report_metrics
   - build_v2_report
   - audit claims

3. Enforce:
   - tasks must be HUMAN_REVIEWED_NON_EVIDENCE or stronger
   - provider cannot be mock for evidence path
   - paid providers blocked
   - max_items required unless allow_full_run
   - resume enabled
   - raw outputs preserved

4. Add tests:
   - `tests/test_v2_tiny_eval_pipeline.py`

5. Add docs:
   - `docs/TINY_EVAL_RUNBOOK.md`
   - update Kaggle docs

6. Create:
   - `docs/V2_TINY_EVAL_SCORING_REPORT.md`

7. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, command added, whether tiny eval path passed, and next prompt: `14_V2_MAIN_PILOT_200_RUNBOOK.md`.
