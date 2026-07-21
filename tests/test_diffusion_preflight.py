"""Tests for the V2.2 diffusion/Kaggle edit-generation preflight."""

from __future__ import annotations

from certvic.edit.diffusion_preflight import diffusion_preflight
from certvic.io import write_jsonl


def _plan(tmp_path, n=4):
    src = tmp_path / "src.png"
    src.write_bytes(b"\x89PNG\r\n")  # presence only; preflight does not decode
    rows = [
        {
            "edit_id": f"e{i}",
            "source_id": f"s{i}",
            "image_path": str(src),
            "mask_path": "planned://mask",
            "edit_type": "remove",
        }
        for i in range(n)
    ]
    p = tmp_path / "edit_plan.jsonl"
    write_jsonl(p, rows)
    return p


def test_simple_engine_ready_on_cpu(tmp_path):
    plan = _plan(tmp_path)
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("paid_services_enabled: false\n", encoding="utf-8")
    result = diffusion_preflight(str(plan), engine="simple_fill", config_path=str(cfg))
    assert result["ready"] is True
    assert result["blocking_failures"] == []
    assert result["downloads_attempted"] is False


def test_heavy_engine_blocks_without_weights(tmp_path):
    plan = _plan(tmp_path)
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("paid_services_enabled: false\noptional_diffusers_enabled: true\n", encoding="utf-8")
    result = diffusion_preflight(
        str(plan), engine="diffusers_inpaint_optional", config_path=str(cfg), weights_dir=None
    )
    # diffusers absent and/or no local weights -> not ready, but no download.
    assert result["ready"] is False
    assert "local_weights_present" in result["blocking_failures"]
    assert result["downloads_attempted"] is False
    assert result["paid_services"] is False


def test_paid_services_block(tmp_path):
    plan = _plan(tmp_path)
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("paid_services_enabled: true\n", encoding="utf-8")
    result = diffusion_preflight(str(plan), engine="simple_fill", config_path=str(cfg))
    assert result["ready"] is False
    assert "zero_cost_policy" in result["blocking_failures"]


def test_runtime_estimate_present(tmp_path):
    plan = _plan(tmp_path, n=10)
    result = diffusion_preflight(str(plan), engine="simple_fill")
    runtime = next(c for c in result["checks"] if c["check"] == "runtime_estimate")
    assert runtime["n_planned_edits"] == 10
    assert runtime["estimated_minutes"] >= 0
