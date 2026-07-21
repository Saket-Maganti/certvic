"""Tests for the V3 edit detectability probe (prompt 05)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from certvic.io import write_jsonl
from certvic.reporting import edit_detectability_report
from certvic.validation import edit_detectability


def _save(arr, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr.astype("uint8")).save(path)
    return str(path)


def _make_tasks(tmp_path, n=12, *, detectable=True, seed=0):
    """Build n tasks. detectable=True makes edits obviously different (gray blob)."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        base = rng.integers(0, 256, size=(32, 32, 3), dtype=np.int64).astype(np.uint8)
        orig_p = _save(base, tmp_path / f"orig_{i}.png")
        edit = base.copy()
        if detectable:
            # Flat gray rectangle -> low-level features shift a lot.
            edit[8:24, 8:24] = 128
        else:
            # Near-identical edit (tiny perturbation) -> hard to detect.
            edit[0, 0] = (int(edit[0, 0, 0]) + 1) % 256
        edit_p = _save(edit, tmp_path / f"edit_{i}.png")
        rows.append({
            "item_id": f"item_{i}",
            "original_image_path": orig_p,
            "edited_image_path": edit_p,
            "edit": {"edit_type": ["remove", "occlude", "displace", "control_irrelevant"][i % 4]},
        })
    path = tmp_path / "tasks.jsonl"
    write_jsonl(path, rows)
    return path


def test_per_image_and_paired_features(tmp_path):
    base = np.zeros((16, 16, 3), dtype=np.uint8)
    op = _save(base, tmp_path / "o.png")
    ed = base.copy()
    ed[4:12, 4:12] = 200
    ep = _save(ed, tmp_path / "e.png")
    of = edit_detectability.per_image_features(op)
    assert set(edit_detectability.PER_IMAGE_FEATURES).issubset(of)
    pf = edit_detectability.paired_features(op, ep)
    assert pf["mean_abs_diff"] > 0 and pf["hist_distance"] > 0


def test_missing_image_returns_none(tmp_path):
    assert edit_detectability.per_image_features(str(tmp_path / "nope.png")) is None
    assert edit_detectability.paired_features(str(tmp_path / "a.png"), str(tmp_path / "b.png")) is None


def test_detectable_edits_high_auc(tmp_path):
    tasks = _make_tasks(tmp_path, n=16, detectable=True)
    result = edit_detectability.run_detectability(str(tasks))
    assert result["n_items"] == 16
    assert result["classifier"]["auc"] is not None
    assert result["classifier"]["auc"] >= 0.8
    assert result["classifier"]["auc"] >= 0.5
    assert result["classifier"]["cv_grouped_by_item"] is True
    assert result["classifier"]["backend"] == "sklearn_logreg_group_cv"
    assert result["artifact_risk"] is True
    assert result["evidence_status"] == "DIAGNOSTIC_ONLY"
    assert result["evidence_claims_made"] is False


def test_subtle_edits_lower_auc(tmp_path):
    tasks = _make_tasks(tmp_path, n=16, detectable=False, seed=3)
    result = edit_detectability.run_detectability(str(tasks))
    # Near-identical edits should be much harder to separate than the blob case.
    assert result["classifier"]["auc"] < 0.8
    assert result["artifact_risk"] is False


def test_fallback_when_sklearn_disabled(tmp_path):
    tasks = _make_tasks(tmp_path, n=12, detectable=True)
    result = edit_detectability.run_detectability(str(tasks), use_sklearn=False)
    assert result["classifier"]["backend"] == "rank_auc_fallback"
    assert result["classifier"]["auc"] is not None


def test_multivariate_auc_is_symmetric_separability(tmp_path):
    tasks = _make_tasks(tmp_path, n=12, detectable=False, seed=11)
    result = edit_detectability.run_detectability(str(tasks))
    cls = result["classifier"]
    assert cls["cv_grouped_by_item"] is True
    assert cls["auc"] >= 0.5
    assert cls["multivariate_auc"] == round(
        max(cls["raw_multivariate_auc"], 1.0 - cls["raw_multivariate_auc"]), 4
    )


def test_skips_items_with_missing_images(tmp_path):
    tasks = _make_tasks(tmp_path, n=4, detectable=True)
    rows = [json.loads(line) for line in Path(tasks).read_text().splitlines()]
    rows.append({"item_id": "broken", "original_image_path": str(tmp_path / "missing.png"), "edited_image_path": str(tmp_path / "missing2.png"), "edit": {"edit_type": "remove"}})
    write_jsonl(tasks, rows)
    result = edit_detectability.run_detectability(str(tasks))
    assert result["n_skipped"] == 1
    assert result["n_items"] == 4


def test_write_outputs_and_report(tmp_path):
    tasks = _make_tasks(tmp_path, n=10, detectable=True)
    result = edit_detectability.run_detectability(str(tasks))
    paths = edit_detectability.write_outputs(result, str(tmp_path / "out"))
    for p in paths.values():
        assert Path(p).exists()
    report = Path(paths["report"]).read_text(encoding="utf-8")
    assert "Edit Detectability Probe" in report
    assert "never evidence by itself" in report
    # features.csv has a header + 2 rows per item.
    feat_lines = Path(paths["features"]).read_text(encoding="utf-8").strip().splitlines()
    assert feat_lines[0].startswith("item_id,variant,label")
    assert len(feat_lines) == 1 + 2 * 10


def test_highly_detectable_items_flagged(tmp_path):
    tasks = _make_tasks(tmp_path, n=10, detectable=True)
    result = edit_detectability.run_detectability(str(tasks), flag_top_fraction=0.3)
    assert len(result["highly_detectable_items"]) == 3
    assert all("detectability_score" in r for r in result["highly_detectable_items"])


def test_report_renderer_handles_unknown_auc():
    md = edit_detectability_report.render_report({
        "tasks_path": "x", "n_items": 0, "n_skipped": 0,
        "classifier": {"backend": "none", "auc": None, "per_feature_auc": {}},
        "artifact_risk": False, "flag_auc": 0.8, "highly_detectable_items": [],
        "evidence_status": edit_detectability.EVIDENCE_STATUS,
    })
    assert "unknown" in md


def test_no_gpu_or_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
