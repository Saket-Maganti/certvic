"""Tests for the Kaggle main-200 bundle builder."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from scripts.build_kaggle_main200_bundle import (
    REPO,
    SANITIZE_TOKEN,
    build_manifest,
    collect_bundle_files,
)

LOCAL_ROOT = "/Users/tester/ade20k_root/ADEChallengeData2016"


def _make_synthetic_repo(root: Path) -> None:
    (root / "certvic").mkdir(parents=True)
    (root / "certvic" / "io.py").write_text("x = 1\n", encoding="utf-8")
    # forbidden / binary content that must be excluded
    (root / "certvic" / "__pycache__").mkdir()
    (root / "certvic" / "__pycache__" / "io.pyc").write_text("junk", encoding="utf-8")
    (root / "certvic" / "weights.safetensors").write_bytes(b"\x00\x01")
    (root / "certvic" / "preview.png").write_bytes(b"\x89PNG\r\n")
    (root / "configs").mkdir()
    (root / "configs" / "x.yaml").write_text("a: 1\n", encoding="utf-8")

    shards = root / "data" / "results" / "main_real_200" / "gpu_shards"
    shards.mkdir(parents=True)
    for i in (0, 1):
        row = {"edit_id": f"e{i}", "image_path": f"{LOCAL_ROOT}/images/training/x{i}.jpg",
               "mask_path": f"{LOCAL_ROOT}/annotations/training/x{i}.png"}
        (shards / f"pilot_edit_plan_shard{i}_of_2.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    plan = root / "data" / "results" / "main_real_200" / "pilot_edit_plan.jsonl"
    plan.write_text(json.dumps({"edit_id": "e0", "image_path": f"{LOCAL_ROOT}/images/training/x0.jpg"}) + "\n", encoding="utf-8")


def test_excludes_forbidden_dirs_and_binaries(tmp_path):
    _make_synthetic_repo(tmp_path)
    files = collect_bundle_files(tmp_path)
    assert not any("__pycache__" in n or n.endswith(".pyc") for n in files)
    assert not any(n.endswith(".safetensors") for n in files)
    assert not any(n.endswith((".png", ".jpg")) for n in files)


def test_includes_required_shards(tmp_path):
    _make_synthetic_repo(tmp_path)
    files = collect_bundle_files(tmp_path)
    for i in (0, 1):
        assert f"data/results/main_real_200/gpu_shards/pilot_edit_plan_shard{i}_of_2.jsonl" in files


def test_planning_files_sanitized(tmp_path):
    _make_synthetic_repo(tmp_path)
    files = collect_bundle_files(tmp_path)
    shard = files["data/results/main_real_200/gpu_shards/pilot_edit_plan_shard0_of_2.jsonl"].decode()
    assert SANITIZE_TOKEN in shard
    assert "/Users/" not in shard
    assert LOCAL_ROOT not in shard


def test_no_ade20k_pixels(tmp_path):
    _make_synthetic_repo(tmp_path)
    files = collect_bundle_files(tmp_path)
    assert not any(n.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".bmp")) for n in files)
    assert not any("ADEChallengeData2016" in n or "ade20k_root" in n for n in files)


def test_manifest_deterministic(tmp_path):
    _make_synthetic_repo(tmp_path)
    f1 = collect_bundle_files(tmp_path)
    f2 = collect_bundle_files(tmp_path)
    m1 = build_manifest(f1, bundle_name="b.zip")
    m2 = build_manifest(f2, bundle_name="b.zip")
    assert m1["content_digest"] == m2["content_digest"]
    assert m1["entries"] == m2["entries"]


# --- guarded checks against the real built bundle (skip if not present) ------
REAL_BUNDLE = REPO / "dist" / "certvic_kaggle_main200_bundle.zip"


@pytest.mark.skipif(not REAL_BUNDLE.exists(), reason="bundle not built")
def test_real_bundle_clean_and_complete():
    from certvic.security.audit_kaggle_bundle import audit_bundle

    with zipfile.ZipFile(REAL_BUNDLE) as zf:
        names = zf.namelist()
        assert any("gpu_shards/pilot_edit_plan_shard0_of_2.jsonl" in n for n in names)
        assert any("gpu_shards/pilot_edit_plan_shard1_of_2.jsonl" in n for n in names)
        assert not any(n.lower().endswith((".jpg", ".jpeg", ".png")) for n in names)
        assert not any("ADEChallengeData2016" in n for n in names)
        assert not any("__pycache__" in n for n in names)
        # the planning manifests (the ones with baked-in local paths) must be tokenized
        s0 = zf.read("data/results/main_real_200/gpu_shards/pilot_edit_plan_shard0_of_2.jsonl").decode()
        assert "/Users/" not in s0 and SANITIZE_TOKEN in s0
    # and the real security checker (with its constant-file allowlist) must pass
    assert audit_bundle(str(REAL_BUNDLE))["ok"] is True
