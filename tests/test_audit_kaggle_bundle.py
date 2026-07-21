"""Tests for the Kaggle bundle security checker."""

from __future__ import annotations

import zipfile
from pathlib import Path

from certvic.security.audit_kaggle_bundle import (
    audit_bundle,
    classify_entry,
    scan_text,
)


def test_scan_catches_user_path():
    findings = scan_text("docs/run.md", "load from /Users/alice/projects/secret/data.bin")
    assert any(f["kind"] == "private_absolute_path" for f in findings)


def test_scan_catches_home_and_other_prefixes():
    for path in ("/home/bob/data", "/mnt/scratch/weights", "/root/.cache/hf"):
        findings = scan_text("x.sh", f"cp {path} .")
        assert any(f["kind"] == "private_absolute_path" for f in findings), path


def test_scan_catches_api_keys():
    samples = [
        "api_key = 'sk-ABCDEFGHIJKLMNOPQRSTUVWX0123'",
        "aws = AKIAIOSFODNN7EXAMPLE",
        "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    ]
    for s in samples:
        findings = scan_text("conf.py", s)
        assert any(f["kind"].startswith("secret:") for f in findings), s


def test_scan_permits_kaggle_input_path():
    findings = scan_text("run.md", "ADE20K_ROOT=/kaggle/input/ade20k/ADEChallengeData2016")
    assert not any(f["kind"] == "private_absolute_path" for f in findings)
    findings2 = scan_text("run.md", "out = /kaggle/working/edits")
    assert not any(f["kind"] == "private_absolute_path" for f in findings2)


def test_scan_ignores_bare_prefix_constant():
    # A bare prefix with no path segment after it (a code constant) is not a private path.
    findings = scan_text("x.py", "PRIVATE_PREFIXES = ('/Users/', '/home/', '/root/')")
    assert not any(f["kind"] == "private_absolute_path" for f in findings)


def test_scan_allowlist_skips_constant_bearing_files():
    findings = scan_text("certvic/storage/path_policy.py", "home = '/Users/realname/x'")
    assert findings == []


def test_classify_flags_forbidden_and_binaries():
    assert any(f["kind"] == "forbidden_dir" for f in classify_entry(".git/config", 20))
    assert any(f["kind"] == "forbidden_dir" for f in classify_entry("pkg/__pycache__/m.pyc", 20))
    assert any(f["kind"] == "model_weight_file" for f in classify_entry("m/model.safetensors", 20))
    assert any(f["kind"] == "raw_image_pixels" for f in classify_entry("imgs/a.jpg", 20))
    assert any(f["kind"] == "dataset_pixels_path" for f in classify_entry("x/ADEChallengeData2016/a.txt", 20))
    assert any(f["kind"] == "secret_file" for f in classify_entry("creds/id_rsa", 20))
    assert any(f["kind"] == "large_file" for f in classify_entry("big.jsonl", 10 * 1024 * 1024))


def _make_zip(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


def test_audit_bundle_clean_passes(tmp_path):
    z = tmp_path / "clean.zip"
    _make_zip(z, {
        "certvic/io.py": b"x = 1\n",
        "docs/run.md": b"set ADE20K_ROOT=/kaggle/input/ade20k/ADEChallengeData2016\n",
        "data/plan.jsonl": b'{"image_path": "__ADE20K_ROOT__/images/a.jpg"}\n',
    })
    result = audit_bundle(str(z))
    assert result["ok"] is True
    assert result["n_findings"] == 0


def test_audit_bundle_dirty_fails(tmp_path):
    z = tmp_path / "dirty.zip"
    _make_zip(z, {
        "docs/run.md": b"path = /Users/realname/Projects/x\n",
        "model.safetensors": b"\x00\x01\x02",
        "creds/.env": b"SECRET=abc\n",
    })
    result = audit_bundle(str(z))
    assert result["ok"] is False
    kinds = set(result["findings_by_kind"])
    assert "private_absolute_path" in kinds
    assert "model_weight_file" in kinds


def test_audit_bundle_missing_file():
    result = audit_bundle("does/not/exist.zip")
    assert result["ok"] is False
    assert result["error"] == "bundle_not_found"
