# CertVIC Codex V2 Prompt 09 — Failure Taxonomy and Gallery

Do not make deployment claims. Do not claim causal-understanding failure. Do not copy non-rehostable pixels by default.

## Goal

Build a failure taxonomy and gallery system for qualitative paper analysis once eligible real runs exist.

## Tasks

1. Add module:
   - `certvic/reporting/failure_taxonomy.py`

2. Taxonomy:
   - missed_required_change
   - spurious_flip_on_control
   - original_recognition_failure
   - edited_recognition_failure
   - parse_failure
   - answer_inertia
   - overreaction_to_irrelevant_edit
   - safety_prompt_bias
   - caption_like_behavior
   - ambiguous_item

3. Add deterministic classifier:
   - rule-based from PairScore + predictions + metadata
   - no LLM calls
   - support manual override file

4. Add gallery builder:

   `python3 -m certvic.reporting.failure_gallery_v2 --tasks data/manifests/tasks.jsonl --preds data/predictions/run.jsonl --scores data/results/pair_scores.jsonl --out-dir data/results/failure_gallery_v2`

   Outputs:
   - failure_gallery.jsonl
   - failure_taxonomy_summary.csv
   - failure_gallery.md
   - local_gallery.html
   - paper_candidate_failures.jsonl

5. Rules:
   - no pixel copy by default
   - local links only
   - include license/release mode
   - include claim eligibility
   - include prompts/raw outputs/parsed answers
   - include safe paper caption text

6. Add tests:
   - `tests/test_v2_failure_taxonomy_gallery.py`

7. Update docs:
   - `docs/CLAIM_LEDGER.md`
   - `docs/PAPER_PLAN.md`
   - `docs/REPRO.md`

8. Create:
   - `docs/V2_FAILURE_TAXONOMY_GALLERY_REPORT.md`

9. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, commands added, whether taxonomy/gallery passed, and next prompt: `10_V2_ARTIFACT_RELEASE_RECIPE_FIRST.md`.
