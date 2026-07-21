from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from scripts.build_spurious_v2_control import _require_frozen_selection


ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "data/edits/spurious_v2_control"
V1 = ROOT / "data/edits/spurious_flip_control"
BUNDLE = ROOT / "dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip"


@pytest.fixture(scope="module", autouse=True)
def _ensure_spurious_v2_bundle():
    if not BUNDLE.exists():
        subprocess.run(
            [sys.executable, "scripts/build_spurious_v2_control.py"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )


def _rows():
    return [json.loads(line) for line in (V2 / "pilot_eval_tasks_reviewed.jsonl").read_text().splitlines() if line]


def test_output_task_file_exists_and_is_v2_only():
    assert (V2 / "pilot_eval_tasks_reviewed.jsonl").exists()
    assert (V1 / "pilot_eval_tasks_reviewed.jsonl").exists()
    rows = _rows()
    assert len(rows) == 30
    assert all(row["metadata"]["control"] == "spurious_v2_retrospective_stricter_control" for row in rows)
    assert all(row["metadata"]["evidence_status"] == "DIAGNOSTIC_ONLY" for row in rows)
    assert all(row["metadata"]["retrospective_post_selection"] is True for row in rows)
    assert all(isinstance(row["metadata"]["v11_detectability_score"], float) for row in rows)
    assert all(row["metadata"]["v11_detectability_method"].endswith("paired_features_v11") for row in rows)
    assert all("spurious_v2_control" in row["original_image_path"] for row in rows)
    assert all("spurious_v2_control" in row["edited_image_path"] for row in rows)


def test_no_overlap_and_min_distance_enforced():
    rows = _rows()
    assert all(not row["patch_bbox_intersects_object_bbox"] for row in rows)
    assert all(float(row["patch_target_mask_overlap_pixels"]) == 0 for row in rows)
    assert all(float(row["patch_object_bbox_distance_px"]) >= 75 for row in rows)


def test_bundle_contains_images_tasks_manifest_and_no_predictions():
    assert BUNDLE.exists()
    with zipfile.ZipFile(BUNDLE) as zf:
        names = zf.namelist()
    assert "data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl" in names
    assert "data/edits/spurious_v2_control/spurious_v2_manifest.json" in names
    assert any(name.startswith("data/edits/spurious_v2_control/images/orig/") for name in names)
    assert any(name.startswith("data/edits/spurious_v2_control/images/control/") for name in names)
    forbidden = ("pred_", "prediction", "weights", ".pt", ".pth", ".safetensors", "/Users/")
    assert not any(any(token in name for token in forbidden) for name in names)


def test_every_v2_image_is_hash_locked_in_task_and_bundle_manifests():
    rows = _rows()
    bundle_manifest = json.loads((V2 / "bundle_manifest.json").read_text())
    entries = {entry["path"]: entry for entry in bundle_manifest["image_entries"]}
    assert len(entries) == 60
    with zipfile.ZipFile(BUNDLE) as zf:
        for row in rows:
            for variant, path_key, hash_key in (
                ("original", "original_image_path", "original_image_sha256"),
                ("edited", "edited_image_path", "edited_image_sha256"),
            ):
                path = row[path_key]
                expected = row["metadata"][hash_key]
                assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
                assert entries[path]["sha256"] == expected
                assert entries[path]["bytes"] == (ROOT / path).stat().st_size
                assert hashlib.sha256(zf.read(path)).hexdigest() == expected, variant


def test_quality_report_documents_local_candidate_ceiling():
    report = json.loads((ROOT / "data/results/main_real_200/v9_mega_upgrade/spurious_v2_quality_report.json").read_text())
    assert report["n_items"] == 30
    assert report["n_source_items"] == 94
    assert report["target_n_requested"] == "200-300"
    assert report["target_n_local_status"] == "INSUFFICIENT_LOCAL_CANDIDATES_MAX_FEASIBLE_FILTERED_SET"
    assert report["quality_pass"] is True
    assert report["paper_evidence"] is False


def test_spurious_v2_bundle_rebuild_is_byte_deterministic():
    subprocess.run(
        [sys.executable, "scripts/build_spurious_v2_control.py"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    first = hashlib.sha256(BUNDLE.read_bytes()).hexdigest()
    subprocess.run(
        [sys.executable, "scripts/build_spurious_v2_control.py"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    second = hashlib.sha256(BUNDLE.read_bytes()).hexdigest()
    assert second == first
    with zipfile.ZipFile(BUNDLE) as zf:
        assert {info.date_time for info in zf.infolist()} == {(2026, 1, 1, 0, 0, 0)}


def test_empty_selection_fails_before_canonical_artifacts_can_change():
    task = V2 / "pilot_eval_tasks_reviewed.jsonl"
    before = {
        "task": hashlib.sha256(task.read_bytes()).hexdigest(),
        "bundle": hashlib.sha256(BUNDLE.read_bytes()).hexdigest(),
    }
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        _require_frozen_selection([])
    assert hashlib.sha256(task.read_bytes()).hexdigest() == before["task"]
    assert hashlib.sha256(BUNDLE.read_bytes()).hexdigest() == before["bundle"]
