"""Score prediction pairs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict

from certvic.io import load_model_jsonl, write_json, write_jsonl
from certvic.metrics.summary import summarize_pair_scores
from certvic.schema import ImageVariant, PairScore, PredictionRecord, RequiredChange, TaskItem


def score_predictions(tasks_path: str, preds_path: str) -> list[PairScore]:
    tasks = {task.item_id: task for task in load_model_jsonl(tasks_path, TaskItem)}
    preds = load_model_jsonl(preds_path, PredictionRecord)
    grouped: dict[tuple[str, str], dict[str, PredictionRecord]] = defaultdict(dict)
    for pred in preds:
        grouped[(pred.run_id, pred.item_id)][pred.image_variant] = pred

    scores: list[PairScore] = []
    for (run_id, item_id), pair in sorted(grouped.items()):
        task = tasks[item_id]
        original = pair.get(ImageVariant.ORIGINAL.value)
        edited = pair.get(ImageVariant.EDITED.value)
        if original is None or edited is None:
            continue
        original_correct = original.parse_ok and original.parsed_answer == task.answer_original
        edited_correct = edited.parse_ok and edited.parsed_answer == task.answer_edited
        parse_ok = bool(original.parse_ok and edited.parse_ok)
        answer_changed = original.parsed_answer != edited.parsed_answer
        gold_answer_changes = task.answer_original != task.answer_edited
        if task.required_change == RequiredChange.CHANGE.value:
            semantic_update_success = bool(
                parse_ok
                and original_correct
                and edited_correct
                and gold_answer_changes
                and answer_changed
                and edited.parsed_answer == task.answer_edited
            )
            irrelevant_flip = False
            irrelevant_flip_primary = False
            consistent = semantic_update_success
        else:
            semantic_update_success = False
            irrelevant_flip = bool(parse_ok and not gold_answer_changes and answer_changed)
            irrelevant_flip_primary = bool(not parse_ok or gold_answer_changes or irrelevant_flip)
            consistent = not irrelevant_flip_primary
        scores.append(
            PairScore(
                run_id=run_id,
                item_id=item_id,
                provider_name=original.provider_name,
                model_name=original.model_name,
                task_family=task.task_family,
                domain=task.domain,
                original_correct=bool(original_correct),
                edited_correct=bool(edited_correct),
                consistent=bool(consistent),
                required_change=task.required_change,
                parse_ok=parse_ok,
                notes=None,
                metadata={
                    "edit_type": task.edit.edit_type,
                    "gold_answer_changes": gold_answer_changes,
                    "model_answer_changes": bool(parse_ok and answer_changed),
                    "model_answer_changes_to_edited_gold": bool(
                        parse_ok and answer_changed and edited.parsed_answer == task.answer_edited
                    ),
                    "semantic_update_success": semantic_update_success,
                    "irrelevant_flip": irrelevant_flip,
                    "irrelevant_flip_primary": irrelevant_flip_primary,
                    "primary_endpoint_schema": "certvic.confirmatory.primary_endpoint.v1",
                    "evidence_status": task.metadata.get("evidence_status", "UNKNOWN"),
                    "provider_type": original.provider_type,
                    "split": task.split,
                    "source_id": task.source.source_id,
                    "source_name": task.source.source_name,
                    "domain": task.domain,
                    "data_origin": "synthetic_smoke"
                    if task.split == "smoke" or task.domain == "synthetic_sanity"
                    else "real_or_recipe",
                    "source_is_synthetic_smoke": (
                        task.split == "smoke"
                        or task.domain == "synthetic_sanity"
                        or "synthetic smoke" in task.source.source_name.lower()
                    ),
                },
            )
        )
    return scores


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--preds", required=True)
    parser.add_argument("--out-scores", required=True)
    parser.add_argument("--out-summary", required=True)
    args = parser.parse_args(argv)
    scores = score_predictions(args.tasks, args.preds)
    summary = summarize_pair_scores(scores)
    write_jsonl(args.out_scores, scores)
    write_json(args.out_summary, summary)
    print(json.dumps({"scores": len(scores), "summary": summary}, sort_keys=True))


if __name__ == "__main__":
    main()
