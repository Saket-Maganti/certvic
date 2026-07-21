"""Tests for the V3 dockerless reproduction scripts + audit (prompt 15)."""

from __future__ import annotations

import stat
import sys
from pathlib import Path

from certvic.release import reproduction_audit

EXPECTED_SCRIPTS = [
    "reproduce_smoke.sh",
    "reproduce_simulation.sh",
    "reproduce_tiny_pilot_dry_run.sh",
    "reproduce_reports.sh",
]


def test_all_scripts_exist_and_executable():
    for name in EXPECTED_SCRIPTS:
        p = Path("scripts") / name
        assert p.exists(), name
        mode = p.stat().st_mode
        assert mode & stat.S_IXUSR  # owner-executable


def test_scripts_have_strict_mode_and_shebang():
    for name in EXPECTED_SCRIPTS:
        text = (Path("scripts") / name).read_text(encoding="utf-8")
        assert text.startswith("#!")
        assert "set -euo pipefail" in text


def test_audit_passes_on_real_scripts():
    result = reproduction_audit.audit_scripts("scripts")
    assert result["n_scripts"] == 4
    assert result["passed"] is True, result["scripts"]
    assert result["no_paid_markers"] is True
    assert result["no_destructive"] is True
    assert result["dockerless"] is True
    assert result["evidence_claims_made"] is False


def test_dataset_root_script_documents_user_path():
    result = reproduction_audit.audit_scripts("scripts")
    pilot = next(a for a in result["scripts"] if a["script"] == "reproduce_tiny_pilot_dry_run.sh")
    assert pilot["documents_user_path"] is True
    assert pilot["ok"] is True


def test_audit_flags_destructive(tmp_path):
    bad = tmp_path / "reproduce_bad.sh"
    bad.write_text("#!/usr/bin/env bash\nset -euo pipefail\nrm -rf /\n", encoding="utf-8")
    result = reproduction_audit.audit_scripts(str(tmp_path))
    a = result["scripts"][0]
    assert a["destructive"]
    assert a["ok"] is False
    assert result["passed"] is False


def test_audit_flags_paid_marker(tmp_path):
    bad = tmp_path / "reproduce_paid.sh"
    bad.write_text("#!/usr/bin/env bash\nset -euo pipefail\nexport OPENAI_API_KEY=sk-xxx\n", encoding="utf-8")
    result = reproduction_audit.audit_scripts(str(tmp_path))
    assert result["no_paid_markers"] is False
    assert result["passed"] is False


def test_audit_flags_docker(tmp_path):
    bad = tmp_path / "reproduce_docker.sh"
    bad.write_text("#!/usr/bin/env bash\nset -euo pipefail\ndocker run foo\n", encoding="utf-8")
    result = reproduction_audit.audit_scripts(str(tmp_path))
    assert result["dockerless"] is False


def test_dataset_root_without_doc_flagged(tmp_path):
    bad = tmp_path / "reproduce_root.sh"
    bad.write_text("#!/usr/bin/env bash\nset -euo pipefail\npython3 -m certvic.x --ade20k-root /tmp/x\n", encoding="utf-8")
    result = reproduction_audit.audit_scripts(str(tmp_path))
    a = result["scripts"][0]
    # Uses a dataset root but no <PLACEHOLDER>/${...ROOT} documentation.
    assert any("user-provided path" in f for f in a["findings"])


def test_report_renders():
    result = reproduction_audit.audit_scripts("scripts")
    md = reproduction_audit.render_report(result)
    assert "Reproduction Scripts Audit" in md


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
