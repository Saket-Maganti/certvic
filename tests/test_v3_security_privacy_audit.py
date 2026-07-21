"""Tests for the V3 security / privacy / path audit (prompt 16)."""

from __future__ import annotations

import sys
from pathlib import Path

from certvic.security import path_audit, release_privacy_audit, secrets_audit


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --- path_audit ------------------------------------------------------------

def test_detects_private_absolute_path(tmp_path):
    _write(tmp_path / "configs" / "x.yaml", "ade20k_root: /Users/alice/ADE20K\n")
    result = path_audit.scan_private_paths(str(tmp_path))
    assert result["ok"] is False
    kinds = {f["kind"] for f in result["findings"]}
    assert "private_absolute_path" in kinds
    assert "local_dataset_root" in kinds


def test_clean_tree_passes(tmp_path):
    _write(tmp_path / "configs" / "x.yaml", "ade20k_root: null\nout: data/manifests/x.jsonl\n")
    result = path_audit.scan_private_paths(str(tmp_path))
    assert result["ok"] is True


def test_allowlist_skips_example_files(tmp_path):
    _write(tmp_path / "docs" / "STORAGE_AND_PATH_POLICY.md", "Example: /Users/alice/data\n")
    result = path_audit.scan_private_paths(str(tmp_path))
    assert result["ok"] is True  # allowlisted doc


def test_generated_dirs_skipped(tmp_path):
    _write(tmp_path / "data" / "results" / "audit.json", '{"repo_root": "/Users/alice/Projects/certVIC"}')
    result = path_audit.scan_private_paths(str(tmp_path))
    assert result["ok"] is True  # generated output dir skipped


# --- secrets_audit ---------------------------------------------------------

def test_detects_openai_and_aws_keys(tmp_path):
    _write(tmp_path / "src" / "leak.py", 'KEY = "sk-abcdefghijklmnopqrstuvwxyz0123"\naws = "AKIAIOSFODNN7EXAMPLE"\n')
    result = secrets_audit.scan_secrets(str(tmp_path))
    kinds = {f["kind"] for f in result["secret_findings"]}
    assert "openai_key" in kinds
    assert "aws_access_key" in kinds
    assert result["ok"] is False


def test_detects_committed_env_and_paid_endpoint(tmp_path):
    _write(tmp_path / ".env", "SECRET=1\n")
    _write(tmp_path / "src" / "client.py", "URL = 'https://api.openai.com/v1/chat'\n")
    result = secrets_audit.scan_secrets(str(tmp_path))
    assert ".env" in result["committed_env_files"]
    assert any(e["host"] == "api.openai.com" for e in result["paid_endpoints"])
    assert result["ok"] is False


def test_secrets_clean_tree(tmp_path):
    _write(tmp_path / "src" / "ok.py", "x = 1\n")
    result = secrets_audit.scan_secrets(str(tmp_path))
    assert result["ok"] is True


# --- release_privacy_audit -------------------------------------------------

def test_release_pixels_detected(tmp_path):
    rel = tmp_path / "release"
    (rel).mkdir()
    (rel / "leak.png").write_text("PNG", encoding="utf-8")
    result = release_privacy_audit.scan_release_pixels(str(rel))
    assert result["ok"] is False
    assert "leak.png" in result["pixels"]


def test_combined_audit_fail_and_report(tmp_path):
    _write(tmp_path / "src" / "leak.py", 'k = "sk-abcdefghijklmnopqrstuvwxyz0123"\n')
    _write(tmp_path / "configs" / "c.yaml", "ade20k_root: /Users/bob/ADE20K\n")
    result = release_privacy_audit.audit(str(tmp_path))
    assert result["passed"] is False
    assert result["n_total_findings"] >= 2
    md = release_privacy_audit.render_report(result)
    assert "Security / Privacy / Path Audit" in md
    assert result["evidence_claims_made"] is False


def test_audit_on_real_repo_passes():
    # The real repo should pass: only allowlisted files contain example markers.
    result = release_privacy_audit.audit(".")
    assert result["passed"] is True, {
        "private": result["private_paths"]["findings"][:5],
        "secrets": result["secrets"]["secret_findings"][:5],
        "env": result["secrets"]["committed_env_files"],
        "paid": result["secrets"]["paid_endpoints"][:5],
    }


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
