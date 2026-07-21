import pytest

from certvic.data.select_pilot_items import PilotSelectionError, select_pilot_items
from certvic.io import read_jsonl, write_jsonl


def test_pilot_selection_deterministic(tmp_path):
    sources = [{"source_id": f"s{i}"} for i in range(5)]
    masks = [
        {"source_id": f"s{i}", "mask_id": f"m{i}", "bbox_xyxy": [0, 0, 2, 2]}
        for i in range(5)
    ]
    source_path = tmp_path / "sources.jsonl"
    mask_path = tmp_path / "masks.jsonl"
    out1 = tmp_path / "out1.jsonl"
    out2 = tmp_path / "out2.jsonl"
    write_jsonl(source_path, sources)
    write_jsonl(mask_path, masks)
    select_pilot_items(str(source_path), str(mask_path), str(out1), target=3, seed=1)
    select_pilot_items(str(source_path), str(mask_path), str(out2), target=3, seed=1)
    assert read_jsonl(out1) == read_jsonl(out2)


def test_pilot_selection_balances_and_writes_summary(tmp_path):
    sources = [{"source_id": f"s{i}", "metadata": {"task_family": "fallback"}} for i in range(6)]
    masks = [
        {"source_id": "s0", "mask_id": "m0", "bbox_xyxy": [0, 0, 2, 2], "mask_area_fraction": 0.1, "task_family": "support_stability"},
        {"source_id": "s1", "mask_id": "m1", "bbox_xyxy": [0, 0, 2, 2], "mask_area_fraction": 0.1, "task_family": "support_stability"},
        {"source_id": "s2", "mask_id": "m2", "bbox_xyxy": [0, 0, 2, 2], "mask_area_fraction": 0.1, "task_family": "affordance_reachability"},
        {"source_id": "s3", "mask_id": "m3", "bbox_xyxy": [0, 0, 2, 2], "mask_area_fraction": 0.1, "task_family": "affordance_reachability"},
        {"source_id": "s4", "mask_id": "m4", "bbox_xyxy": [0, 0, 2, 2], "mask_area_fraction": 0.1, "task_family": "control_irrelevant"},
        {"source_id": "s5", "mask_id": "m5", "bbox_xyxy": [0, 0, 2, 2], "mask_area_fraction": 0.1, "task_family": "control_irrelevant"},
    ]
    source_path = tmp_path / "sources.jsonl"
    mask_path = tmp_path / "masks.jsonl"
    out = tmp_path / "selection.jsonl"
    summary_out = tmp_path / "selection_summary.json"
    write_jsonl(source_path, sources)
    write_jsonl(mask_path, masks)
    summary = select_pilot_items(
        str(source_path),
        str(mask_path),
        str(out),
        target=6,
        seed=2,
        min_mask_area_fraction=0.05,
        max_mask_area_fraction=0.2,
        summary_out=str(summary_out),
    )
    assert summary["selected"] == 6
    assert summary["by_task_family"] == {
        "affordance_reachability": 2,
        "control_irrelevant": 2,
        "support_stability": 2,
    }
    assert summary_out.exists()


def test_pilot_selection_fails_when_not_enough_valid_candidates(tmp_path):
    sources = [{"source_id": "s0"}, {"source_id": "s1"}]
    masks = [{"source_id": "s0", "mask_id": "m0", "bbox_xyxy": [0, 0, 2, 2], "mask_area_fraction": 0.9}]
    source_path = tmp_path / "sources.jsonl"
    mask_path = tmp_path / "masks.jsonl"
    write_jsonl(source_path, sources)
    write_jsonl(mask_path, masks)
    with pytest.raises(PilotSelectionError, match="Not enough valid pilot candidates"):
        select_pilot_items(
            str(source_path),
            str(mask_path),
            str(tmp_path / "selection.jsonl"),
            target=1,
            max_mask_area_fraction=0.2,
        )


def test_pilot_selection_rejects_invalid_bbox_and_missing_source(tmp_path):
    sources = [{"source_id": "s0"}, {"source_id": "s1"}]
    masks = [
        {"source_id": "s0", "mask_id": "bad_bbox", "bbox_xyxy": [0, 0, 0, 2], "mask_area_fraction": 0.1},
        {"source_id": "missing", "mask_id": "missing_source", "bbox_xyxy": [0, 0, 2, 2], "mask_area_fraction": 0.1},
        {"source_id": "s1", "mask_id": "good", "bbox_xyxy": [0, 0, 2, 2], "mask_area_fraction": 0.1},
    ]
    source_path = tmp_path / "sources.jsonl"
    mask_path = tmp_path / "masks.jsonl"
    out = tmp_path / "selection.jsonl"
    write_jsonl(source_path, sources)
    write_jsonl(mask_path, masks)
    summary = select_pilot_items(str(source_path), str(mask_path), str(out), target=1)
    assert summary["selected"] == 1
    assert summary["rejected"]["invalid_bbox"] == 1
    assert summary["rejected"]["missing_source"] == 1
