"""Tests for V7 second-domain readiness: registry + COCO stub."""

from __future__ import annotations

from pathlib import Path

import pytest

from certvic.data.coco_adapter_stub import (
    COCOAdapterNotReady, adapter_summary, coco_category_overlap, load_coco_instances,
)
from certvic.io import read_json

REPO = Path(__file__).resolve().parents[1]


def test_candidates_registry_ranks_coco_first_and_marks_blockers():
    reg = read_json(REPO / "registry/datasets/second_domain_candidates.json")
    assert reg["paper_evidence"] is False
    ranking = reg["ranking"]
    assert ranking[0]["id"] == "coco_2017_instances_panoptic"
    assert ranking[1]["id"] == "lvis_v1"
    assert reg["recommended_next_domain"]["id"] == "coco_2017_instances_panoptic"
    # SA-1B and Cityscapes must be flagged blocked (have blockers).
    blocked = {r["id"] for r in ranking if r["blocked"]}
    assert {"sa_1b", "cityscapes"} <= blocked


def test_no_candidate_claimed_usable_without_license_and_verification():
    reg = read_json(REPO / "registry/datasets/second_domain_candidates.json")
    for cid, c in reg["candidates"].items():
        assert c["license"], cid
        assert "requires_manual_verification" in c
        # blocked candidates must NOT be marked usable_without_blockers
        if c["blockers"]:
            assert c["usable_without_blockers"] is False


def test_coco_stub_is_pointer_only_and_does_not_download():
    s = adapter_summary()
    assert s["downloads_attempted"] is False
    assert s["pointer_only"] is True
    overlap = coco_category_overlap()
    assert overlap["couch"] == "sofa" and overlap["dining table"] == "table"


def test_coco_loader_refuses_without_data(tmp_path):
    with pytest.raises(COCOAdapterNotReady, match="will not download"):
        load_coco_instances(tmp_path / "missing_coco")
