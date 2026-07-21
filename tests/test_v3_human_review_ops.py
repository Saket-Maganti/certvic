"""Tests for the V3 human review operations (prompt 07)."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

from certvic.io import write_jsonl
from certvic.validation import adjudicate_review, review_batches, review_progress
from certvic.validation.aggregate_visual_review import DECISION_FIELDS


def _tasks(tmp_path, n=20):
    families = ["support_stability", "occlusion_safety", "affordance_reachability", "control_irrelevant"]
    types = ["remove", "occlude", "displace", "control_irrelevant"]
    rows = []
    for i in range(n):
        rows.append({
            "item_id": f"item_{i:03d}",
            "edit_id": f"item_{i:03d}",
            "source_id": f"src_{i % 5}",
            "task_family": families[i % 4],
            "edit_type": types[i % 4],
            "domain": "household",
            "required_change": "change",
            "original_image_path": f"data/o_{i}.png",
            "edited_image_path": f"data/e_{i}.png",
            "question_original": "Is it stable?",
        })
    path = tmp_path / "tasks.jsonl"
    write_jsonl(path, rows)
    return path


# --- review_batches --------------------------------------------------------

def test_build_batches_balanced_with_overlap(tmp_path):
    tasks = _tasks(tmp_path, n=20)
    out = tmp_path / "batches"
    manifest = review_batches.build_review_batches(str(tasks), str(out), ["rev_a", "rev_b"], overlap_rate=0.2, seed=0)
    assert manifest["reviewers"] == ["rev_a", "rev_b"]
    # Overlap items appear in both reviewers' batches.
    assert manifest["n_overlap_items"] >= 1
    total_unique = 20
    # Each non-overlap item assigned once; overlap items assigned to both.
    assigned = sum(manifest["per_reviewer_counts"].values())
    assert assigned == total_unique + manifest["n_overlap_items"]
    # CSV files exist with the review columns.
    for f in manifest["batch_files"].values():
        assert Path(f).exists()
        header = Path(f).read_text(encoding="utf-8").splitlines()[0]
        assert "keep_for_eval" in header and "reviewer_id" in header
    assert manifest["paid_annotation_services"] is False
    assert manifest["workload_estimate"]["parallel_wall_clock_minutes"] > 0


def test_overlap_zero_for_single_reviewer(tmp_path):
    tasks = _tasks(tmp_path, n=12)
    out = tmp_path / "b1"
    manifest = review_batches.build_review_batches(str(tasks), str(out), ["solo"], overlap_rate=0.3, seed=0)
    assert manifest["n_overlap_items"] == 0
    assert manifest["per_reviewer_counts"]["solo"] == 12


def test_invalid_overlap_rate_rejected(tmp_path):
    tasks = _tasks(tmp_path, n=4)
    with pytest.raises(ValueError):
        review_batches.build_review_batches(str(tasks), str(tmp_path / "x"), ["a", "b"], overlap_rate=1.5)


def test_batches_balanced_across_reviewers(tmp_path):
    tasks = _tasks(tmp_path, n=40)
    out = tmp_path / "b3"
    manifest = review_batches.build_review_batches(str(tasks), str(out), ["a", "b", "c"], overlap_rate=0.0, seed=1)
    counts = list(manifest["per_reviewer_counts"].values())
    # Round-robin within strata keeps per-reviewer loads within 1 of each other.
    assert max(counts) - min(counts) <= 1


# --- review_progress -------------------------------------------------------

def _fill_csv(path: Path, fill: dict):
    """Fill decision fields in a batch CSV. fill maps item_id -> {field: value}."""
    rows = list(csv.DictReader(path.open("r", encoding="utf-8")))
    fieldnames = rows[0].keys() if rows else []
    for row in rows:
        overrides = fill.get(row["item_id"])
        if overrides:
            row.update(overrides)
    with path.open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def test_progress_tracks_completion_and_missing(tmp_path):
    tasks = _tasks(tmp_path, n=8)
    out = tmp_path / "batches"
    manifest = review_batches.build_review_batches(str(tasks), str(out), ["rev_a", "rev_b"], overlap_rate=0.0, seed=0)
    # Fill rev_a fully, leave rev_b blank.
    a_path = Path(manifest["batch_files"]["rev_a"])
    a_rows = list(csv.DictReader(a_path.open("r", encoding="utf-8")))
    fill = {r["item_id"]: {f: "yes" for f in DECISION_FIELDS} for r in a_rows}
    _fill_csv(a_path, fill)

    prog = review_progress.review_progress(str(out))
    assert prog["per_reviewer"]["rev_a"]["rated"] == len(a_rows)
    assert prog["per_reviewer"]["rev_b"]["missing"] > 0
    assert prog["all_complete"] is False
    assert prog["completion_fraction"] < 1.0


def test_progress_detects_overlap_disagreement_and_iaa(tmp_path):
    tasks = _tasks(tmp_path, n=10)
    out = tmp_path / "batches"
    manifest = review_batches.build_review_batches(str(tasks), str(out), ["rev_a", "rev_b"], overlap_rate=1.0, seed=0)
    # All items overlap. Fill both reviewers but disagree on keep_for_eval for one item.
    overlap_ids = manifest["overlap_ids"]
    for reviewer in ("rev_a", "rev_b"):
        path = Path(manifest["batch_files"][reviewer])
        fill = {}
        for iid in overlap_ids:
            vals = {f: "yes" for f in DECISION_FIELDS}
            if iid == overlap_ids[0] and reviewer == "rev_b":
                vals["keep_for_eval"] = "no"
            fill[iid] = vals
        _fill_csv(path, fill)

    prog = review_progress.review_progress(str(out))
    assert prog["n_overlap_items"] == len(overlap_ids)
    assert prog["n_disagreements"] >= 1
    assert "keep_for_eval" in prog["iaa"]


# --- adjudicate_review -----------------------------------------------------

def _ratings_csv(tmp_path):
    path = tmp_path / "ratings.csv"
    fields = ["item_id", "reviewer_id", *DECISION_FIELDS]
    rows = [
        # item_1: unanimous yes
        {"item_id": "item_1", "reviewer_id": "a", **{f: "yes" for f in DECISION_FIELDS}},
        {"item_id": "item_1", "reviewer_id": "b", **{f: "yes" for f in DECISION_FIELDS}},
        # item_2: majority (2 yes, 1 no on photorealistic)
        {"item_id": "item_2", "reviewer_id": "a", **{f: "yes" for f in DECISION_FIELDS}},
        {"item_id": "item_2", "reviewer_id": "b", **{f: "yes" for f in DECISION_FIELDS}},
        {"item_id": "item_2", "reviewer_id": "c", **{**{f: "yes" for f in DECISION_FIELDS}, "photorealistic": "no"}},
        # item_3: tie (1 yes, 1 no on keep_for_eval)
        {"item_id": "item_3", "reviewer_id": "a", **{**{f: "yes" for f in DECISION_FIELDS}, "keep_for_eval": "yes"}},
        {"item_id": "item_3", "reviewer_id": "b", **{**{f: "yes" for f in DECISION_FIELDS}, "keep_for_eval": "no"}},
    ]
    with path.open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_adjudicate_majority_and_ties(tmp_path):
    ratings = _ratings_csv(tmp_path)
    out = tmp_path / "adjudicated.csv"
    result = adjudicate_review.adjudicate_review(str(ratings), str(out))
    assert result["n_items"] == 3
    by_item = {r["item_id"]: r for r in result["rows"]}
    assert by_item["item_1"]["adjudication_status"] == "unanimous"
    assert by_item["item_2"]["adjudication_status"] == "majority"
    assert by_item["item_2"]["photorealistic"] == "yes"  # majority wins
    assert by_item["item_3"]["adjudication_status"] == "tie_needs_human"
    assert by_item["item_3"]["keep_for_eval"] == "uncertain"
    assert result["n_tie_items"] == 1
    # Output CSV written with the adjudicated columns.
    out_rows = list(csv.DictReader(out.open("r", encoding="utf-8")))
    assert len(out_rows) == 3
    assert "adjudication_status" in out_rows[0]


def test_no_paid_or_heavy_imports():
    tasks_data = json.dumps({"x": 1})  # touch json to keep import used
    assert tasks_data
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
