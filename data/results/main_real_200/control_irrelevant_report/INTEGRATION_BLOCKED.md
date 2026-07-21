# Spurious-Flip / control_irrelevant Integration — BLOCKED

**specificity_status: blocked** · `evidence_status=SPECIFICITY_CONTROL_BLOCKED_NON_EVIDENCE`

Integration refused: required control artifacts are missing. Spurious-flip numbers are NOT fabricated.

## Missing
- explicit human visual review approvals (0/94 approved)

## Present
- control_task_manifest: True
- control_images: True
- quality_detectability_report: True
- human_visual_review_complete: False
- predictions_per_provider: {'qwen2_5_vl_7b': True, 'internvl_8b': True, 'llava_onevision_7b': True}

Interpretation: Until the control predictions + quality/detectability exist, the objection 'models are sticky under any perturbation' is UNANSWERED.

## Next command

```bash
Run the Kaggle VLM notebook on data/edits/spurious_flip_control/ for each provider, then: python3 scripts/pilot_report_from_raw.py --provider <id> --model-name <hf-id> --run-label <id> --raw-presence ... --raw-control ... --raw-spurious <control_preds>.jsonl ; then re-run python3 -m certvic.v7.spurious_control_integration
```
