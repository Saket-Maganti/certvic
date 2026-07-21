"""Tests for the V3 storage and path planner (prompt 02)."""

from __future__ import annotations

import sys
from pathlib import Path

from certvic.storage import dataset_roots, path_policy, plan_storage


# --- path_policy -----------------------------------------------------------

def test_private_absolute_detection():
    assert path_policy.is_private_absolute("/Users/alice/data/ade20k") is True
    assert path_policy.is_private_absolute("/home/bob/x") is True
    assert path_policy.is_private_absolute("data/manifests/x.jsonl") is False


def test_kaggle_safe_names():
    assert path_policy.is_kaggle_safe("data/edits/pilot_v1.jsonl") is True
    assert path_policy.is_kaggle_safe("my data/edits.jsonl") is False
    assert "spaces" in path_policy.kaggle_unsafe_reason("a b")
    assert path_policy.kaggle_unsafe_reason("ok_name-1.json") is None


def test_symlink_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    inside = root / "a.txt"
    inside.write_text("x", encoding="utf-8")
    assert path_policy.is_symlink_escape(str(inside), str(root)) is False
    outside = tmp_path / "outside.txt"
    outside.write_text("y", encoding="utf-8")
    link = root / "link.txt"
    link.symlink_to(outside)
    assert path_policy.is_symlink_escape(str(link), str(root)) is True


def test_unsafe_overwrite_root():
    assert path_policy.is_unsafe_overwrite_root("/") is True
    assert path_policy.is_unsafe_overwrite_root(str(Path.home())) is True
    assert path_policy.is_unsafe_overwrite_root("data/results/x") is False


def test_audit_paths_aggregates_problems():
    result = path_policy.audit_paths(
        ["/Users/alice/secret/out", "data/results/ok.jsonl", "bad name.jsonl"],
        expect_kaggle_safe=True,
    )
    assert result["ok"] is False
    assert "/Users/alice/secret/out" in result["private_absolute_paths"]
    assert any("bad name.jsonl" in p for p in result["kaggle_unsafe"])
    assert result["evidence_claims_made"] is False


def test_collect_output_paths_from_config():
    config = {
        "mask_out_dir": "data/masks/ade20k_pilot",
        "outputs": {"a": "data/manifests/a.jsonl", "nested": {"b": "data/results/b.json"}},
        "ignored_scalar": 5,
        "remote": "https://example.com/x",
    }
    paths = path_policy.collect_output_paths(config)
    assert "data/masks/ade20k_pilot" in paths
    assert "data/manifests/a.jsonl" in paths
    assert "data/results/b.json" in paths
    assert "https://example.com/x" not in paths


# --- plan_storage ----------------------------------------------------------

def test_estimate_storage_scales_with_n():
    small = plan_storage.estimate_storage(200)
    big = plan_storage.estimate_storage(2000)
    assert big["working_bytes"] > small["working_bytes"]
    assert big["candidates_generated"] == int(round(2000 * small["overgeneration_factor"]))
    assert small["evidence_claims_made"] is False
    assert small["downloads_attempted"] is False


def test_estimate_storage_large_scale_warns():
    plan = plan_storage.estimate_storage(200_000)
    assert plan["fits_kaggle_working"] is False
    assert any("Kaggle" in w for w in plan["warnings"])


def test_rejected_pixels_warning():
    plan = plan_storage.estimate_storage(1000, config={"tiny_edit_generation": {"overgeneration_factor": 5.0}})
    # rejected = 4000 edits > 1000 kept -> warning.
    assert any("rejected" in w for w in plan["warnings"])


def test_plan_storage_with_real_config_audits_paths():
    cfg = "configs/real_pilot_ade20k.yaml"
    plan = plan_storage.plan_storage(cfg, 200)
    assert plan["scale"] == 200
    assert "path_audit" in plan
    # Config output paths are repo-relative and should be policy-clean.
    assert plan["path_policy_ok"] is True


def test_plan_storage_writes_json(tmp_path):
    out = tmp_path / "plan.json"
    plan_storage.main(["--config", "configs/real_pilot_ade20k.yaml", "--scale", "200", "--out", str(out)])
    assert out.exists()
    import json

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["scale"] == 200 and "category_gb" in data


# --- dataset_roots ---------------------------------------------------------

def test_dataset_root_policy_structure():
    policy = dataset_roots.dataset_root_policy()
    assert "ade20k" in policy["known_datasets"]
    assert any("never hard-coded" in p for p in policy["principles"])
    md = dataset_roots.render_policy(policy)
    assert md.startswith("# Dataset Root Policy")


def test_validate_root_missing(tmp_path):
    result = dataset_roots.validate_root(str(tmp_path / "nope"))
    assert result["exists"] is False
    assert "root_does_not_exist" in result["findings"]
    assert result["scanned_pixels"] is False


def test_validate_root_inside_repo_flagged(tmp_path):
    repo = tmp_path / "repo"
    inside = repo / "data" / "ade20k"
    inside.mkdir(parents=True)
    result = dataset_roots.validate_root(str(inside), repo_root=str(repo))
    assert "root_inside_repo" in result["findings"]


def test_no_heavy_imports():
    # Planning must not pull torch/diffusers.
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
