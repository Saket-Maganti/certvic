"""Reviewer batching for scaled visual review (V3 prompt 07).

Splits review tasks into balanced per-reviewer batches and assigns an overlap
subset to every reviewer so inter-annotator agreement can be measured. Batches
are balanced across (task_family, edit_type) strata. Estimates reviewer workload
and wall-clock time. No paid annotation services; sheets contain no model outputs.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from certvic.io import read_jsonl
from certvic.validation.export_visual_review import REVIEW_COLUMNS

# Conservative wall-clock per item for a careful single-factor judgement.
DEFAULT_SECONDS_PER_ITEM = 30.0


def _review_row(task: dict, edit: dict, reviewer_id: str) -> dict:
    quality = edit.get("quality") or {}
    warnings = quality.get("warnings") or []
    row = {col: "" for col in REVIEW_COLUMNS}
    row.update({
        "item_id": task.get("item_id") or task.get("edit_id"),
        "edit_id": task.get("edit_id") or edit.get("edit_id"),
        "source_id": task.get("source_id") or edit.get("source_id"),
        "task_family": task.get("task_family") or edit.get("task_family"),
        "domain": task.get("domain") or edit.get("domain"),
        "edit_type": task.get("edit_type") or edit.get("edit_type"),
        "required_change": task.get("required_change") or edit.get("required_change"),
        "original_image_path": task.get("original_image_path") or edit.get("original_image_path"),
        "edited_image_path": task.get("edited_image_path") or edit.get("edited_image_path"),
        "mask_id": task.get("mask_id") or edit.get("mask_id"),
        "quality_gate_status": edit.get("quality_gate_status") or task.get("quality_gate_status"),
        "quality_warnings": "; ".join(str(w) for w in warnings),
        "neutral_question": task.get("question_original") or task.get("neutral_question") or "",
        "reviewer_id": reviewer_id,
    })
    return row


def _stratum(task: dict) -> str:
    return f"{task.get('task_family')}|{task.get('edit_type')}"


def assign_batches(tasks: list[dict], reviewers: list[str], overlap_rate: float, seed: int) -> dict:
    if len(reviewers) < 1:
        raise ValueError("at least one reviewer is required")
    if not 0.0 <= overlap_rate <= 1.0:
        raise ValueError("overlap_rate must be in [0, 1]")
    rng = random.Random(seed)

    by_stratum: dict[str, list[dict]] = defaultdict(list)
    for t in tasks:
        by_stratum[_stratum(t)].append(t)
    for items in by_stratum.values():
        items.sort(key=lambda r: str(r.get("item_id") or r.get("edit_id")))
        rng.shuffle(items)

    overlap_ids: set[str] = set()
    assignments: dict[str, list[str]] = {r: [] for r in reviewers}

    # Per stratum: pick overlap items (seen by all reviewers), round-robin the rest.
    rr = 0
    for stratum in sorted(by_stratum):
        items = by_stratum[stratum]
        n_overlap = int(round(len(items) * overlap_rate)) if len(reviewers) > 1 else 0
        for t in items[:n_overlap]:
            iid = str(t.get("item_id") or t.get("edit_id"))
            overlap_ids.add(iid)
            for r in reviewers:
                assignments[r].append(iid)
        for t in items[n_overlap:]:
            iid = str(t.get("item_id") or t.get("edit_id"))
            assignments[reviewers[rr % len(reviewers)]].append(iid)
            rr += 1
    return {"assignments": assignments, "overlap_ids": sorted(overlap_ids)}


def build_review_batches(
    tasks_path: str,
    out_dir: str,
    reviewers: list[str],
    *,
    overlap_rate: float = 0.2,
    seed: int = 0,
    generated_edits_path: str | None = None,
    seconds_per_item: float = DEFAULT_SECONDS_PER_ITEM,
) -> dict:
    tasks = read_jsonl(tasks_path)
    tasks_by_id = {str(t.get("item_id") or t.get("edit_id")): t for t in tasks}
    edits_by_id: dict[str, dict] = {}
    if generated_edits_path and Path(generated_edits_path).exists():
        for e in read_jsonl(generated_edits_path):
            edits_by_id[str(e.get("edit_id") or e.get("item_id"))] = e

    plan = assign_batches(tasks, reviewers, overlap_rate, seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    batch_files: dict[str, str] = {}
    per_reviewer_counts: dict[str, int] = {}
    per_reviewer_strata: dict[str, dict] = {}
    for reviewer, item_ids in plan["assignments"].items():
        path = out / f"review_batch_{reviewer}.csv"
        with path.open("w", encoding="utf-8", newline="") as h:
            writer = csv.DictWriter(h, fieldnames=REVIEW_COLUMNS)
            writer.writeheader()
            strat_counter: Counter = Counter()
            for iid in item_ids:
                task = tasks_by_id.get(iid, {"item_id": iid})
                writer.writerow(_review_row(task, edits_by_id.get(iid, {}), reviewer))
                strat_counter[_stratum(task)] += 1
        batch_files[reviewer] = str(path)
        per_reviewer_counts[reviewer] = len(item_ids)
        per_reviewer_strata[reviewer] = dict(sorted(strat_counter.items()))

    total_ratings = sum(per_reviewer_counts.values())
    max_per_reviewer = max(per_reviewer_counts.values()) if per_reviewer_counts else 0
    workload = {
        "seconds_per_item": seconds_per_item,
        "total_ratings": total_ratings,
        "total_reviewer_minutes": round(total_ratings * seconds_per_item / 60.0, 1),
        # Reviewers work in parallel, so wall-clock is the busiest reviewer.
        "parallel_wall_clock_minutes": round(max_per_reviewer * seconds_per_item / 60.0, 1),
    }

    manifest = {
        "task": "visual_review_batches",
        "tasks_path": tasks_path,
        "n_tasks": len(tasks),
        "reviewers": reviewers,
        "overlap_rate": overlap_rate,
        "n_overlap_items": len(plan["overlap_ids"]),
        "overlap_ids": plan["overlap_ids"],
        "per_reviewer_counts": per_reviewer_counts,
        "per_reviewer_strata": per_reviewer_strata,
        "batch_files": batch_files,
        "workload_estimate": workload,
        "paid_annotation_services": False,
        "contains_model_outputs": False,
        "evidence_claims_made": False,
    }
    (out / "assignment_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC visual-review batching (balanced + overlap for IAA)")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--reviewers", nargs="+", required=True)
    parser.add_argument("--generated-edits")
    parser.add_argument("--overlap-rate", type=float, default=0.2)
    parser.add_argument("--seconds-per-item", type=float, default=DEFAULT_SECONDS_PER_ITEM)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    manifest = build_review_batches(
        args.tasks,
        args.out_dir,
        args.reviewers,
        overlap_rate=args.overlap_rate,
        seed=args.seed,
        generated_edits_path=args.generated_edits,
        seconds_per_item=args.seconds_per_item,
    )
    print(json.dumps({
        "reviewers": manifest["reviewers"],
        "per_reviewer_counts": manifest["per_reviewer_counts"],
        "n_overlap_items": manifest["n_overlap_items"],
        "workload_estimate": manifest["workload_estimate"],
        "out_dir": args.out_dir,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
