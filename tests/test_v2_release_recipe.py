"""Tests for the V2 recipe-first artifact release."""

from __future__ import annotations

import json
from pathlib import Path

from certvic.io import write_jsonl
from certvic.release.build_artifact import build_artifact, load_release_config
from certvic.release.data_card import build_data_card

REPO_ROOT = Path(__file__).resolve().parents[1]


def _fake_repo(tmp_path):
    md = tmp_path / "data" / "manifests"
    md.mkdir(parents=True)
    sources = [{"source_id": "s0", "license_category": "pointer_only", "local_path": str(tmp_path / "secret" / "img.jpg")}]
    masks = [{"mask_id": "m0", "source_id": "s0", "label_id": 8, "task_family": "support_stability", "mask_path": "/abs/ann.png"}]
    write_jsonl(md / "ade20k_sources.jsonl", sources)
    write_jsonl(md / "ade20k_masks.jsonl", masks)
    return tmp_path


def test_default_config_is_recipe_first():
    cfg = load_release_config(str(REPO_ROOT / "configs" / "release_recipe.yaml"))
    assert cfg["include_cc0_pixels"] is False
    assert cfg["exclude_private_paths"] is True
    assert cfg["anonymize_local_paths"] is True


def test_build_artifact_anonymizes_and_audits(tmp_path):
    repo = _fake_repo(tmp_path)
    out = tmp_path / "artifact"
    manifest = build_artifact(str(REPO_ROOT / "configs" / "release_recipe.yaml"), str(out), repo_root=str(repo))
    assert manifest["release_mode"] == "recipe_first"
    # Packaged manifests must not contain raw private absolute paths.
    packaged = (out / "manifests" / "ade20k_sources.jsonl").read_text()
    assert "/secret/" not in packaged
    assert "<local>" in packaged or "~" in packaged
    audit = json.loads((out / "release_audit.json").read_text())
    assert audit["no_forbidden_pixels"] is True
    assert audit["passed"] is True
    assert (out / "checksums.json").exists()
    assert (out / "README.md").exists()
    assert "zero" in (out / "README.md").read_text().lower()


def test_no_pixels_packaged(tmp_path):
    repo = _fake_repo(tmp_path)
    out = tmp_path / "artifact"
    build_artifact(str(REPO_ROOT / "configs" / "release_recipe.yaml"), str(out), repo_root=str(repo))
    pixels = [p for p in out.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    assert pixels == []


def test_data_card_generation(tmp_path):
    repo = _fake_repo(tmp_path)
    out = tmp_path / "DATA_CARD_GENERATED.md"
    stats = build_data_card(str(repo / "data" / "manifests"), str(out))
    assert stats["sources"] == 1
    assert stats["masks"] == 1
    assert out.exists()
    assert "Recipe-first" in out.read_text()
