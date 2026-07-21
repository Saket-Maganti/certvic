from __future__ import annotations

import numpy as np
from PIL import Image

from certvic.data.pilot_readiness import build_pilot_readiness_report
from certvic.io import read_json


def _fake_root(tmp_path):
    root = tmp_path / "ADEChallengeData2016"
    for split in ["training", "validation"]:
        (root / "images" / split).mkdir(parents=True, exist_ok=True)
        (root / "annotations" / split).mkdir(parents=True, exist_ok=True)
    for name in ["ADE_train_00000001", "ADE_train_00000002"]:
        Image.new("RGB", (4, 4)).save(root / "images" / "training" / f"{name}.jpg")
        Image.fromarray(np.array([[0, 1], [2, 2]], dtype="uint8"), mode="L").save(
            root / "annotations" / "training" / f"{name}.png"
        )
    Image.new("RGB", (4, 4)).save(root / "images" / "validation" / "ADE_val_00000001.jpg")
    Image.fromarray(np.array([[0, 3], [3, 3]], dtype="uint8"), mode="L").save(
        root / "annotations" / "validation" / "ADE_val_00000001.png"
    )
    return root


def test_pilot_readiness_outputs_dry_run_reports(tmp_path):
    root = _fake_root(tmp_path)
    config = tmp_path / "config.yaml"
    out_dir = tmp_path / "readiness"
    config.write_text("target_items: 2\npaid_services_enabled: false\n", encoding="utf-8")
    result = build_pilot_readiness_report(str(config), str(root), str(out_dir), dry_run=True)
    assert result["passed"] is True
    assert result["ready_for_mask_manifest"] is True
    assert result["ready_for_pilot_selection"] is True
    for name in [
        "dataset_inspection.json",
        "candidate_summary.json",
        "license_summary.json",
        "readiness_report.md",
    ]:
        assert (out_dir / name).exists()
    license_summary = read_json(out_dir / "license_summary.json")
    assert license_summary["default_release_mode"] == "recipe_only"
    assert license_summary["pixels_rehostable_by_default"] is False
    candidate_summary = read_json(out_dir / "candidate_summary.json")
    assert candidate_summary["candidate_mask_count"] == 5
    assert candidate_summary["mask_area_statistics"]["n"] == 5
    report = (out_dir / "readiness_report.md").read_text(encoding="utf-8")
    assert "No edits generated yet" in report
    assert "No model inference run yet" in report
    assert "No evidence claims" in report
    assert "Zero paid services" in report
