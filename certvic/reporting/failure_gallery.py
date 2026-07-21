"""Failure gallery manifest builder."""

from __future__ import annotations

from certvic.schema import PairScore, PredictionRecord, TaskItem


def build_failure_gallery(
    tasks: dict[str, TaskItem],
    scores: list[PairScore],
    predictions: list[PredictionRecord],
    max_items: int = 50,
) -> list[dict]:
    pred_map = {(p.item_id, p.image_variant): p for p in predictions}
    gallery: list[dict] = []
    for score in scores:
        if not (score.original_correct and not score.consistent and score.parse_ok):
            continue
        task = tasks[score.item_id]
        gallery.append(
            {
                "item_id": score.item_id,
                "task_family": score.task_family,
                "domain": score.domain,
                "edit_type": task.edit.edit_type,
                "original_path_or_pointer": task.original_image_path,
                "edited_path_or_pointer": task.edited_image_path,
                "original_raw_output": pred_map[(score.item_id, "original")].raw_output,
                "edited_raw_output": pred_map[(score.item_id, "edited")].raw_output,
                "notes": "Manifest only; do not copy non-rehostable pixels.",
            }
        )
        if len(gallery) >= max_items:
            break
    return gallery
