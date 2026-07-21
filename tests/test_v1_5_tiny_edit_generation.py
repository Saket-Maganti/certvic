from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from certvic.data.materialize_tasks import materialize_tasks
from certvic.data.preview_tasks import build_task_preview
from certvic.edit.generate_edits import EditGenerationError, generate_edits
from certvic.edit.quality_gates import evaluate_edit_quality
from certvic.edit.quality_report import build_quality_report
from certvic.io import read_json, read_jsonl, write_jsonl
from certvic.validation.claims import validate_certified_claim_eligibility


def _fixture_image(tmp_path, name):
    path = tmp_path / f"{name}.png"
    arr = np.zeros((24, 24, 3), dtype="uint8")
    arr[:, :] = [20, 30, 40]
    arr[8:14, 8:14] = [210, 60, 40]
    Image.fromarray(arr).save(path)
    return path


def _fixture_mask(tmp_path, name):
    path = tmp_path / f"{name}.png"
    arr = np.zeros((24, 24), dtype="uint8")
    arr[8:14, 8:14] = 255
    Image.fromarray(arr).save(path)
    return path


def _plan_row(tmp_path, edit_id, edit_type, family, required_change):
    image_path = _fixture_image(tmp_path, f"src_{edit_id}")
    mask_path = _fixture_mask(tmp_path, f"mask_{edit_id}")
    return {
        "edit_id": edit_id,
        "source_id": f"source_{edit_id}",
        "image_path": str(image_path),
        "mask_id": f"mask_{edit_id}",
        "mask_path": str(mask_path),
        "label_id": None,
        "label_name": "fixture",
        "bbox": [8, 8, 14, 14],
        "mask_area_fraction": 36 / 576,
        "task_family": family,
        "domain": "household",
        "split": "pilot",
        "edit_type": edit_type,
        "required_change": required_change,
        "planned_params": {
            "bbox": [8, 8, 14, 14],
            "mask_area_fraction": 36 / 576,
            "offset_xy": [4, 0],
        },
        "expected_effect": "fixture only",
        "single_factor": True,
        "release_mode": "recipe_only",
        "license_posture": {"release_mode": "recipe_only"},
        "planned_edited_image_path": f"planned://pilot/{edit_id}",
        "evidence_status": "PLANNED_ONLY",
        "generation_status": "not_generated",
        "zero_cost": True,
    }


def _plan_fixture(tmp_path):
    rows = [
        _plan_row(tmp_path, "tiny_r", "remove", "affordance_reachability", "change"),
        _plan_row(tmp_path, "tiny_o", "occlude", "occlusion_safety", "no_change"),
        _plan_row(tmp_path, "tiny_d", "displace", "support_stability", "change"),
        _plan_row(tmp_path, "tiny_c", "control_irrelevant", "control_irrelevant", "no_change"),
        {
            **_plan_row(tmp_path, "tiny_bad", "remove", "affordance_reachability", "change"),
            "image_path": str(tmp_path / "missing.png"),
        },
    ]
    path = tmp_path / "pilot_edit_plan.jsonl"
    write_jsonl(path, rows)
    return path


def _generate_fixture(tmp_path):
    plan_path = _plan_fixture(tmp_path)
    out_manifest = tmp_path / "pilot_generated_edits.jsonl"
    rejected = tmp_path / "pilot_generated_edits_rejected.jsonl"
    summary = tmp_path / "tiny_edit_generation_summary.json"
    result = generate_edits(
        str(plan_path),
        str(tmp_path / "edits"),
        str(out_manifest),
        str(rejected),
        str(summary),
        max_items=20,
        mode="simple",
        seed=0,
    )
    return plan_path, out_manifest, rejected, summary, result


def test_v1_5_simple_generation_writes_all_supported_edit_types_and_hashes(tmp_path):
    _, out_manifest, rejected, summary_path, summary = _generate_fixture(tmp_path)
    rows = read_jsonl(out_manifest)
    assert {row["edit_type"] for row in rows} == {
        "control_irrelevant",
        "displace",
        "occlude",
        "remove",
    }
    assert all(row["generation_status"] == "generated" for row in rows)
    assert all(row["evidence_status"] == "GENERATED_EDIT_ONLY" for row in rows)
    assert all(row["edited_sha256"] for row in rows)
    assert all(row["zero_cost"] is True for row in rows)
    assert all(row["quality_gate_status"] == "pass" for row in rows)
    assert all((tmp_path / "edits" / f"{row['edit_id']}.png").exists() for row in rows)
    rejected_rows = read_jsonl(rejected)
    assert len(rejected_rows) == 1
    assert "does not exist" in rejected_rows[0]["rejection_reason"]
    assert summary["generated"] == 4
    assert read_json(summary_path)["rejected"] == 1


def test_v1_5_quality_gates_catch_global_destructive_edits(tmp_path):
    image = _fixture_image(tmp_path, "src")
    mask_path = _fixture_mask(tmp_path, "mask")
    mask = np.asarray(Image.open(mask_path).convert("L")) > 127
    destructive = tmp_path / "destructive.png"
    Image.fromarray(np.ones((24, 24, 3), dtype="uint8") * 255).save(destructive)
    result = evaluate_edit_quality(
        str(image),
        str(destructive),
        mask,
        edit_type="remove",
        planned_params={"bbox": [8, 8, 14, 14]},
        actual_params={"bbox": [8, 8, 14, 14]},
        config={},
    )
    assert result["quality_gate_status"] == "fail"
    assert "outside allowed change too large" in result["warnings"]


def test_v1_5_quality_report_writes_expected_files(tmp_path):
    _, out_manifest, rejected, _, _ = _generate_fixture(tmp_path)
    out_dir = tmp_path / "quality_report"
    summary = build_quality_report(str(out_manifest), str(rejected), str(out_dir))
    for name in [
        "quality_summary.json",
        "quality_by_edit_type.csv",
        "rejected_edits.csv",
        "generated_edit_review.md",
        "review_gallery_manifest.jsonl",
    ]:
        assert (out_dir / name).exists()
    report = (out_dir / "generated_edit_review.md").read_text(encoding="utf-8")
    assert "No VLM inference was run" in report
    assert "No evidence claims are enabled" in report
    assert "Human validity is still required" in report
    assert summary["quality_passed"] == 4


def test_v1_5_materialize_tasks_only_includes_quality_passed_and_leakage_clean(tmp_path):
    plan_path, out_manifest, _, _, _ = _generate_fixture(tmp_path)
    preview_path = tmp_path / "pilot_task_preview.jsonl"
    build_task_preview(str(plan_path), str(preview_path), str(tmp_path / "preview_summary.json"))
    generated_rows = read_jsonl(out_manifest)
    generated_rows[0]["quality_gate_status"] = "fail"
    generated_rows[0]["quality"]["quality_gate_status"] = "fail"
    write_jsonl(out_manifest, generated_rows)
    out = tmp_path / "pilot_eval_tasks_tiny.jsonl"
    summary = materialize_tasks(
        str(preview_path),
        str(out_manifest),
        str(out),
        str(tmp_path / "pilot_eval_tasks_tiny_summary.json"),
    )
    rows = read_jsonl(out)
    assert summary["materialized_tasks"] == 3
    assert all(row["evidence_status"] == "EDIT_READY_NON_EVIDENCE" for row in rows)
    assert all(row["edited_image_status"] == "generated_quality_passed" for row in rows)
    assert all(row["leakage_warnings"] == [] for row in rows)
    assert all(row["runnable_eval_task"] is True for row in rows)


def test_v1_5_non_evidence_statuses_cannot_support_claims():
    certification = {
        "confidence_sequence": {"available": True, "latest": {"lo": 0.10, "hi": 0.20}},
        "lower_bound": 0.10,
    }
    for status in ["GENERATED_EDIT_ONLY", "EDIT_READY_NON_EVIDENCE"]:
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


def test_v1_5_diffusers_mode_is_import_safe_and_fails_clearly(tmp_path):
    plan_path = _plan_fixture(tmp_path)
    with pytest.raises(EditGenerationError, match="diffusers_inpaint|local|dependencies|download"):
        generate_edits(
            str(plan_path),
            str(tmp_path / "edits"),
            str(tmp_path / "generated.jsonl"),
            str(tmp_path / "rejected.jsonl"),
            str(tmp_path / "summary.json"),
            max_items=1,
            mode="diffusers_inpaint",
            seed=0,
        )
