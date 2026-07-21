"""Tests for V7 release-candidate auditor."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from certvic.io import read_json

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "audit_release_candidate", REPO / "scripts/audit_release_candidate.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def test_manifest_excludes_pixels_and_weights():
    m = mod.build()
    assert m["paper_evidence"] is False
    # ADE20K pixels must be in cannot_release, never release_safe.
    assert m["cannot_release"]["n_pixel_files"] > 0
    safe_paths = {e["path"] for e in m["release_safe"]["entries"]}
    assert not any(p.endswith(".jpg") for p in safe_paths)
    assert "never" in m["model_weight_policy"].lower() and "packaged" in m["model_weight_policy"].lower()


def test_privacy_audit_passes_and_no_local_paths_in_release_safe():
    m = mod.build()
    assert m["privacy_audit"]["passed"] is True
    assert m["privacy_audit"]["secrets_ok"] is True


def test_release_not_ready_flags_path_relativization_blocker():
    m = mod.build()
    # Task/sheet files embed absolute paths -> high-severity blocker -> not release_ready.
    assert m["needs_path_relativization"]["n"] > 0
    assert any(b["blocker"] == "absolute_paths" and b["severity"] == "high" for b in m["blockers"])
    assert m["release_ready"] is False


def test_release_safe_entries_have_hashes():
    m = mod.build()
    assert m["release_safe"]["n"] > 0
    for e in m["release_safe"]["entries"]:
        assert e["sha256"]


def test_license_blocker_is_ade20k_pixels():
    m = mod.build()
    joined = " ".join(m["license_provenance_blockers"]).lower()
    assert "ade20k" in joined and "pixel" in joined


def test_manifest_written_to_canonical_path():
    mod.build()
    manifest = read_json(REPO / "data/results/release_candidate_manifest.json")
    assert manifest["schema"] == "certvic.release_candidate.v1"
