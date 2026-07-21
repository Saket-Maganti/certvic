import pytest
import numpy as np
from PIL import Image

from certvic.data.ade20k_adapter import (
    ADE20KLayoutError,
    build_ade20k_manifests,
    inspect_ade20k_layout,
    mask_records_for_annotation,
    pair_images_and_annotations,
    scan_ade20k_sources,
)
from certvic.io import read_jsonl


def test_missing_ade20k_root_fails_clearly(tmp_path):
    with pytest.raises(ADE20KLayoutError, match="will not download"):
        scan_ade20k_sources(str(tmp_path / "missing"))


def _fake_ade20k_root(tmp_path, with_annotations=True, with_images=True):
    root = tmp_path / "ADEChallengeData2016"
    for split in ["training", "validation"]:
        (root / "images" / split).mkdir(parents=True, exist_ok=True)
        (root / "annotations" / split).mkdir(parents=True, exist_ok=True)
    if with_images:
        for name in ["ADE_train_00000001", "ADE_train_00000002"]:
            Image.new("RGB", (4, 4), (10, 20, 30)).save(root / "images" / "training" / f"{name}.jpg")
        Image.new("RGB", (4, 4), (10, 20, 30)).save(root / "images" / "validation" / "ADE_val_00000001.jpg")
    if with_annotations:
        ann1 = np.array(
            [
                [0, 0, 2, 2],
                [0, 1, 1, 2],
                [0, 1, 3, 3],
                [0, 0, 3, 3],
            ],
            dtype="uint8",
        )
        ann2 = np.array(
            [
                [0, 4, 4, 0],
                [0, 4, 4, 0],
                [5, 5, 0, 0],
                [5, 5, 0, 0],
            ],
            dtype="uint8",
        )
        Image.fromarray(ann1, mode="L").save(root / "annotations" / "training" / "ADE_train_00000001.png")
        Image.fromarray(ann2, mode="L").save(root / "annotations" / "validation" / "ADE_val_00000001.png")
    return root


def test_dry_run_detects_fake_ade20k_layout(tmp_path):
    root = _fake_ade20k_root(tmp_path)
    inspection = inspect_ade20k_layout(root)
    assert inspection["layout_status"] == "supported_layout"
    assert inspection["candidate_image_count"] == 3
    assert inspection["candidate_annotation_count"] == 2
    assert inspection["matched_pair_count"] == 2
    assert inspection["candidate_mask_count"] == 5
    assert inspection["train_image_count"] == 2
    assert inspection["val_image_count"] == 1
    assert inspection["unmatched_image_count"] == 1
    assert inspection["downloads_attempted"] is False
    assert inspection["pixels_copied"] is False


def test_missing_images_fails_clearly(tmp_path):
    root = _fake_ade20k_root(tmp_path, with_images=False)
    with pytest.raises(ADE20KLayoutError, match="No candidate ADE20K image files"):
        inspect_ade20k_layout(root)


def test_missing_annotations_is_unsupported_warning(tmp_path):
    root = _fake_ade20k_root(tmp_path, with_annotations=False)
    inspection = inspect_ade20k_layout(root)
    assert inspection["layout_status"] == "unsupported_layout"
    assert inspection["candidate_annotation_count"] == 0
    assert inspection["warnings"]


def test_scan_sources_pointer_only_not_rehostable(tmp_path):
    root = _fake_ade20k_root(tmp_path)
    records = scan_ade20k_sources(str(root), max_items=2)
    assert len(records) == 2
    assert {record.license_category for record in records} == {"pointer_only"}
    assert not any(record.redistribution_allowed for record in records)


def test_pairing_and_mask_candidate_extraction(tmp_path):
    root = _fake_ade20k_root(tmp_path)
    pairs = pair_images_and_annotations(root)
    assert sum(1 for pair in pairs if pair["matched"]) == 2
    matched = next(pair for pair in pairs if pair["matched"] and pair["stem"] == "ADE_train_00000001")
    source = scan_ade20k_sources(str(root), max_items=1)[0]
    records = mask_records_for_annotation(root, source, matched["annotation_path"])
    assert [record.label_id for record in records] == [1, 2, 3]
    label_1 = records[0]
    assert label_1.bbox_xyxy == [1, 1, 3, 3]
    assert label_1.mask_area_fraction == pytest.approx(3 / 16)
    assert label_1.mask_path == str(matched["annotation_path"])
    assert label_1.metadata["binary_mask_exported"] is False


def test_dry_run_does_not_write_final_manifests_by_default(tmp_path):
    root = _fake_ade20k_root(tmp_path)
    sources = tmp_path / "sources.jsonl"
    masks = tmp_path / "masks.jsonl"
    inspection = tmp_path / "inspection.json"
    from certvic.data.ade20k_adapter import main

    main([
        "--ade20k-root",
        str(root),
        "--out-sources",
        str(sources),
        "--out-masks",
        str(masks),
        "--inspection-out",
        str(inspection),
        "--dry-run",
    ])
    assert inspection.exists()
    assert not sources.exists()
    assert not masks.exists()


def test_non_dry_run_writes_source_and_mask_manifests(tmp_path):
    root = _fake_ade20k_root(tmp_path)
    sources = tmp_path / "sources.jsonl"
    masks = tmp_path / "masks.jsonl"
    summary = build_ade20k_manifests(str(root), str(sources), str(masks), max_items=3)
    assert summary["sources"] == 2
    assert summary["masks"] == 5
    source_rows = read_jsonl(sources)
    mask_rows = read_jsonl(masks)
    assert len(source_rows) == 2
    assert len(mask_rows) == 5
    assert all(row["mask_path"].endswith(".png") for row in mask_rows)
    assert all(row["metadata"]["binary_mask_exported"] is False for row in mask_rows)


def test_binary_mask_export_only_when_requested(tmp_path):
    root = _fake_ade20k_root(tmp_path)
    sources = tmp_path / "sources.jsonl"
    masks = tmp_path / "masks.jsonl"
    mask_dir = tmp_path / "binary_masks"
    build_ade20k_manifests(str(root), str(sources), str(masks), max_items=3)
    assert not mask_dir.exists()
    build_ade20k_manifests(
        str(root),
        str(sources),
        str(masks),
        max_items=3,
        export_binary_masks=True,
        mask_out_dir=str(mask_dir),
    )
    rows = read_jsonl(masks)
    assert mask_dir.exists()
    assert len(list(mask_dir.glob("*.png"))) == len(rows)
    assert all(row["metadata"]["binary_mask_exported"] is True for row in rows)


def test_unsupported_layout_manifest_build_fails_clearly(tmp_path):
    root = tmp_path / "not_ade20k"
    root.mkdir()
    Image.new("RGB", (4, 4)).save(root / "loose.jpg")
    with pytest.raises(ADE20KLayoutError, match="Cannot build ADE20K mask manifest"):
        build_ade20k_manifests(str(root), str(tmp_path / "s.jsonl"), str(tmp_path / "m.jsonl"))
