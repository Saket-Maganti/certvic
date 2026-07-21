# CertVIC Codex V2 Prompt 02 — Visual Review and Approval Workflow

Do not use paid services. Do not download data. Do not run VLM inference. Do not make evidence claims.

## Goal

Implement the full human/visual review workflow for generated edits and materialized tasks. Human review validates edit/item quality only; it does not create model evidence.

## Tasks

1. Add visual review sheet export:

   `python3 -m certvic.validation.export_visual_review --tasks data/manifests/pilot_eval_tasks_tiny.jsonl --generated-edits data/manifests/pilot_generated_edits.jsonl --out data/annotations/visual_review_sheet.csv --max-items 50 --seed 0`

   Required columns:
   - item_id, edit_id, source_id, task_family, domain, edit_type, required_change
   - original_image_path, edited_image_path, mask_id, bbox
   - quality_gate_status, quality_warnings, neutral_question
   - photorealistic, single_factor, target_object_clear
   - required_change_unambiguous, prompt_answerable, keep_for_eval
   - notes, reviewer_id

   Do not include model outputs or predictions.

2. Add local HTML review gallery:

   `python3 -m certvic.validation.build_review_gallery --review-sheet data/annotations/visual_review_sheet.csv --out-dir data/annotations/visual_review_gallery`

   Rules: local relative links, no pixel copying by default, no external services.

3. Add visual rating aggregation:

   `python3 -m certvic.validation.aggregate_visual_review --ratings data/annotations/visual_review_ratings.csv --out data/annotations/visual_review_summary.json --keep-list data/annotations/visual_keep_items.txt --drop-list data/annotations/visual_drop_items.txt`

4. Drop if majority says no or uncertain-heavy for:
   - photorealistic
   - single_factor
   - target_object_clear
   - required_change_unambiguous
   - prompt_answerable
   - keep_for_eval

5. Strengthen IAA:
   - percent agreement per field
   - Cohen kappa for two raters
   - majority agreement for three or more raters
   - single-rater warning
   - robust yes/no/uncertain handling

6. Add approved task materialization:

   `python3 -m certvic.data.apply_visual_review --tasks data/manifests/pilot_eval_tasks_tiny.jsonl --keep-list data/annotations/visual_keep_items.txt --out data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --summary-out data/manifests/pilot_eval_tasks_tiny_reviewed_summary.json`

   Output tasks get:
   - visual_review_status = approved
   - evidence_status = HUMAN_REVIEWED_NON_EVIDENCE

7. Add visual review report:

   `python3 -m certvic.reporting.visual_review_report --summary data/annotations/visual_review_summary.json --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/results/visual_review_report`

8. Add tests:
   - `tests/test_v2_visual_review.py`

9. Update:
   - `configs/real_pilot_ade20k.yaml`
   - `docs/PILOT_ADE20K.md`
   - `docs/REPRO.md`
   - `docs/DATA_CARD.md`
   - `docs/RISK_REGISTER.md`

10. Create:
   - `docs/V2_VISUAL_REVIEW_WORKFLOW_REPORT.md`

11. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, commands added, whether visual review passed, and next prompt: `03_V2_TASK_FAMILY_LABEL_MAP_UPGRADE.md`.
