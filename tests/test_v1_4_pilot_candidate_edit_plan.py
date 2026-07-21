from __future__ import annotations

from collections import Counter

from PIL import Image

from certvic.data.preview_tasks import build_task_preview
from certvic.data.select_pilot_items import select_pilot_items
from certvic.edit.plan_edits import build_edit_plan
from certvic.io import read_json, read_jsonl, write_jsonl
from certvic.reporting.pilot_plan_report import build_pilot_plan_report
from certvic.validation.claims import validate_certified_claim_eligibility


def _image(tmp_path, name):
    path = tmp_path / f"{name}.jpg"
    Image.new("RGB", (8, 8), (20, 30, 40)).save(path)
    return path


def _source(tmp_path, source_id, *, split="train", domain="household"):
    path = _image(tmp_path, source_id)
    return {
        "source_id": source_id,
        "source_name": "ADE20K fixture",
        "source_url_or_pointer": str(path),
        "local_path": str(path),
        "license_category": "pointer_only",
        "redistribution_allowed": False,
        "metadata": {"split": split, "domain": domain},
    }


def _mask(source_id, mask_id, label_id, family, *, area=0.10, bbox=None):
    return {
        "source_id": source_id,
        "mask_id": mask_id,
        "mask_path": f"{source_id}_{mask_id}.png",
        "label_id": label_id,
        "object_label": f"fixture_label_{label_id}",
        "bbox_xyxy": bbox or [1, 1, 5, 5],
        "mask_area_fraction": area,
        "metadata": {"task_family": family, "split": "train", "domain": "household"},
    }


def _selection_inputs(tmp_path):
    sources = [
        _source(tmp_path, "s0"),
        _source(tmp_path, "s1"),
        _source(tmp_path, "s2"),
        _source(tmp_path, "s3"),
        _source(tmp_path, "s4", split="val"),
    ]
    masks = [
        _mask("s0", "m0", 10, "support_stability", area=0.10),
        _mask("s0", "m0_extra", 11, "support_stability", area=0.12),
        _mask("s1", "m1", 20, "affordance_reachability", area=0.09),
        _mask("s2", "m2", 30, "occlusion_safety", area=0.08),
        _mask("s3", "m3", 40, "control_irrelevant", area=0.07),
        _mask("s4", "m4", 50, "support_stability", area=0.50),
    ]
    source_path = tmp_path / "sources.jsonl"
    mask_path = tmp_path / "masks.jsonl"
    write_jsonl(source_path, sources)
    write_jsonl(mask_path, masks)
    return source_path, mask_path


def test_v1_4_candidate_selection_is_deterministic_and_review_ready(tmp_path):
    sources, masks = _selection_inputs(tmp_path)
    out1 = tmp_path / "selection1.jsonl"
    out2 = tmp_path / "selection2.jsonl"
    summary = select_pilot_items(
        str(sources),
        str(masks),
        str(out1),
        target=4,
        seed=7,
        min_mask_area_fraction=0.05,
        max_mask_area_fraction=0.30,
        domains=["household"],
        splits=["train"],
        require_target=True,
    )
    select_pilot_items(
        str(sources),
        str(masks),
        str(out2),
        target=4,
        seed=7,
        min_mask_area_fraction=0.05,
        max_mask_area_fraction=0.30,
        domains=["household"],
        splits=["train"],
    )
    rows = read_jsonl(out1)
    assert rows == read_jsonl(out2)
    assert summary["selected"] == 4
    assert all(row["evidence_status"] == "CANDIDATE_ONLY" for row in rows)
    assert all(row["release_mode"] == "recipe_only" for row in rows)
    assert all("proposed_edit_type" in row for row in rows)
    assert max(Counter(row["source_id"] for row in rows).values()) == 1
    assert {row["proposed_task_family"] for row in rows} == {
        "affordance_reachability",
        "control_irrelevant",
        "occlusion_safety",
        "support_stability",
    }


def test_v1_4_candidate_selection_filters_area_and_labels(tmp_path):
    sources, masks = _selection_inputs(tmp_path)
    out = tmp_path / "selection.jsonl"
    summary = select_pilot_items(
        str(sources),
        str(masks),
        str(out),
        target=2,
        seed=0,
        min_mask_area_fraction=0.08,
        max_mask_area_fraction=0.15,
        label_allowlist=[10, 20, 50],
        label_blocklist=[20],
        require_target=False,
    )
    rows = read_jsonl(out)
    assert {row["label_id"] for row in rows} == {10}
    assert summary["warnings"]
    assert summary["rejected"]["label_blocked"] == 1
    assert summary["rejected"]["label_not_allowed"] >= 1
    assert summary["rejected"]["mask_area_too_large"] == 1


def _valid_candidate(tmp_path, source_id, mask_id, family, edit_type, required_change):
    source = _source(tmp_path, source_id)
    return {
        "candidate_id": f"candidate_{source_id}_{mask_id}",
        "source_id": source_id,
        "image_path": source["local_path"],
        "local_path": source["local_path"],
        "mask_id": mask_id,
        "mask_path": f"{mask_id}.png",
        "label_id": 1,
        "label_name": "fixture",
        "bbox": [1, 1, 5, 5],
        "mask_area_fraction": 0.10,
        "task_family": family,
        "proposed_task_family": family,
        "domain": "household",
        "split": "pilot",
        "proposed_edit_type": edit_type,
        "proposed_required_change": required_change,
        "release_mode": "recipe_only",
        "license_posture": {
            "license_category": "pointer_only",
            "redistribution_allowed": False,
            "release_mode": "recipe_only",
        },
        "evidence_status": "CANDIDATE_ONLY",
    }


def _plan_fixture(tmp_path):
    selection = [
        _valid_candidate(tmp_path, "p0", "m0", "support_stability", "displace", "change"),
        _valid_candidate(tmp_path, "p1", "m1", "affordance_reachability", "remove", "change"),
        _valid_candidate(tmp_path, "p2", "m2", "occlusion_safety", "occlude", "no_change"),
        _valid_candidate(tmp_path, "p3", "m3", "control_irrelevant", "control_irrelevant", "no_change"),
        _valid_candidate(tmp_path, "p4", "m4", "support_stability", "occlude", "change"),
        _valid_candidate(tmp_path, "p0", "m0", "support_stability", "displace", "change"),
    ]
    selection[-2]["image_path"] = str(tmp_path / "missing.jpg")
    selection[-2]["mask_area_fraction"] = 0.001
    selection_path = tmp_path / "pilot_selection.jsonl"
    write_jsonl(selection_path, selection)
    plan_path = tmp_path / "pilot_edit_plan.jsonl"
    summary_path = tmp_path / "pilot_edit_plan_summary.json"
    summary = build_edit_plan(
        str(selection_path),
        str(plan_path),
        str(summary_path),
        seed=0,
    )
    return selection_path, plan_path, summary_path, summary


def test_v1_4_edit_plan_creates_types_and_rejects_infeasible(tmp_path):
    _, plan_path, summary_path, summary = _plan_fixture(tmp_path)
    rows = read_jsonl(plan_path)
    rejected = read_jsonl(tmp_path / "pilot_edit_plan_rejected.jsonl")
    assert {row["edit_type"] for row in rows} == {
        "control_irrelevant",
        "displace",
        "occlude",
        "remove",
    }
    assert all(row["evidence_status"] == "PLANNED_ONLY" for row in rows)
    assert all(row["generation_status"] == "not_generated" for row in rows)
    assert all(row["zero_cost"] is True for row in rows)
    assert len({row["edit_id"] for row in rows}) == len(rows)
    assert summary["planned"] == 4
    assert summary["rejected"] == 2
    assert read_json(summary_path)["rejection_reasons"]
    assert any("duplicate edit_id" in row["rejection_reasons"] for row in rejected)
    assert any("mask area below minimum" in row["rejection_reasons"] for row in rejected)


def test_v1_4_task_preview_is_non_runnable_and_leakage_clean(tmp_path):
    _, plan_path, _, _ = _plan_fixture(tmp_path)
    preview_path = tmp_path / "pilot_task_preview.jsonl"
    summary_path = tmp_path / "pilot_task_preview_summary.json"
    summary = build_task_preview(str(plan_path), str(preview_path), str(summary_path))
    rows = read_jsonl(preview_path)
    assert summary["edited_images_required"] is False
    assert summary["leakage_warning_count"] == 0
    assert all(row["evidence_status"] == "PREVIEW_ONLY" for row in rows)
    assert all(row["edited_image_status"] == "planned_unavailable" for row in rows)
    assert all(row["runnable_eval_task"] is False for row in rows)


def test_v1_4_pilot_plan_report_writes_expected_files(tmp_path):
    selection_path, plan_path, _, _ = _plan_fixture(tmp_path)
    preview_path = tmp_path / "pilot_task_preview.jsonl"
    build_task_preview(
        str(plan_path),
        str(preview_path),
        str(tmp_path / "pilot_task_preview_summary.json"),
    )
    out_dir = tmp_path / "pilot_plan_review"
    summary = build_pilot_plan_report(
        str(selection_path),
        str(plan_path),
        str(preview_path),
        str(out_dir),
    )
    for name in [
        "pilot_plan_report.md",
        "selection_by_family.csv",
        "selection_by_label.csv",
        "edit_plan_by_type.csv",
        "rejected_candidates.csv",
        "leakage_check_summary.json",
        "feasibility_summary.json",
    ]:
        assert (out_dir / name).exists()
    report = (out_dir / "pilot_plan_report.md").read_text(encoding="utf-8")
    assert "No edits generated" in report
    assert "No VLM inference" in report
    assert "No evidence claims" in report
    assert summary["evidence_status"] == "NON_EVIDENCE_REVIEW_ONLY"


def test_v1_4_non_evidence_statuses_cannot_support_claims():
    certification = {
        "confidence_sequence": {"available": True, "latest": {"lo": 0.10, "hi": 0.20}},
        "lower_bound": 0.10,
    }
    for status in ["CANDIDATE_ONLY", "PLANNED_ONLY", "PREVIEW_ONLY"]:
        errors = validate_certified_claim_eligibility(
            certification,
            claim_text="A narrow certified gap claim.",
            evidence_context={
                "splits": ["pilot"],
                "evidence_statuses": [status],
                "provider_types": ["open_local"],
                "has_synthetic_smoke_fixtures": False,
            },
            threshold=0.05,
        )
        assert any(status in error for error in errors)
