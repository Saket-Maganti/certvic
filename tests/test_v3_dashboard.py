"""Tests for the V3 static local run dashboard (prompt 11)."""

from __future__ import annotations

import sys

from certvic.dashboard import build_dashboard
from certvic.io import write_json, write_jsonl


def _seed_project(tmp_path, *, with_runs=False, with_claim=False, paid=False, certified=False):
    results = tmp_path / "data" / "results"
    preds = tmp_path / "data" / "predictions"
    prov = tmp_path / "data" / "provenance"
    annot = tmp_path / "data" / "annotations"
    for d in (results, preds, prov, annot):
        d.mkdir(parents=True, exist_ok=True)

    write_json(results / "tiny_summary.json", {
        "by_required_change": {"change": {"intervention_consistency_gap": 0.3, "n": 10}},
        "overall": {"intervention_consistency_gap": 0.3, "original_accuracy": 0.9, "consistency_rate": 0.6},
        "certified": certified,
    })
    if with_runs:
        write_json(preds / "run.jsonl.run_manifest.json", {
            "run_id": "qwen_run", "provider": "qwen2_5_vl_7b",
            "paid_services_used": paid, "zero_cost_policy_ack": True,
            "timestamp_utc": "2026-06-22T00:00:00+00:00",
        })
    if with_claim:
        write_json(results / "claim_ledger.json", [{
            "claim_id": "c1", "certification_status": "certified" if certified else "not_certified", "safe": certified,
        }])
    return {"results": results, "preds": preds, "prov": prov, "annot": annot}


def test_empty_project_builds_with_missing_gates(tmp_path):
    results = tmp_path / "data" / "results"
    results.mkdir(parents=True)
    out = tmp_path / "dash"
    data = build_dashboard.build_dashboard(str(results), str(out))
    assert (out / "index.html").exists()
    for p in build_dashboard.PAGES:
        assert (out / f"{p}.html").exists()
    assert (out / "dashboard_data.json").exists()
    assert data["any_certified_claim"] is False
    assert "no real prediction runs recorded" in data["missing_gates"]
    assert data["external_services_used"] is False
    assert data["pixels_copied"] is False


def test_runs_and_metrics_collected(tmp_path):
    p = _seed_project(tmp_path, with_runs=True)
    out = tmp_path / "dash"
    data = build_dashboard.build_dashboard(str(p["results"]), str(out),
                                           predictions_root=str(p["preds"]),
                                           provenance_dir=str(p["prov"]),
                                           annotations_dir=str(p["annot"]))
    assert data["sections"]["runs"]["status"] == "ok"
    assert data["sections"]["runs"]["items"][0]["run_id"] == "qwen_run"
    assert data["sections"]["metrics"]["status"] == "ok"
    assert any(i["gap"] == 0.3 for i in data["sections"]["metrics"]["items"])


def test_paid_services_flagged(tmp_path):
    p = _seed_project(tmp_path, with_runs=True, paid=True)
    out = tmp_path / "dash"
    data = build_dashboard.build_dashboard(str(p["results"]), str(out),
                                           predictions_root=str(p["preds"]),
                                           provenance_dir=str(p["prov"]),
                                           annotations_dir=str(p["annot"]))
    assert any("paid_services_used=true" in f for f in data["non_evidence_flags"])


def test_certified_claim_recognized(tmp_path):
    p = _seed_project(tmp_path, with_runs=True, with_claim=True, certified=True)
    out = tmp_path / "dash"
    data = build_dashboard.build_dashboard(str(p["results"]), str(out),
                                           predictions_root=str(p["preds"]),
                                           provenance_dir=str(p["prov"]),
                                           annotations_dir=str(p["annot"]))
    assert data["any_certified_claim"] is True
    assert "no certified claim (expected until real evidence exists)" not in data["missing_gates"]


def test_artifacts_section_reads_ledger(tmp_path):
    p = _seed_project(tmp_path)
    write_jsonl(p["prov"] / "run_ledger.jsonl", [{
        "run_id": "r1", "stage": "scoring", "timestamp_utc": "2026-06-22T00:00:00+00:00",
        "input_hashes": {}, "output_hashes": {}, "evidence_status": "REAL_EVIDENCE",
        "zero_cost": True, "paid_services_used": False, "environment": {}, "user_notes": "",
        "schema_version": "certvic.provenance.v1",
    }])
    out = tmp_path / "dash"
    data = build_dashboard.build_dashboard(str(p["results"]), str(out),
                                           predictions_root=str(p["preds"]),
                                           provenance_dir=str(p["prov"]),
                                           annotations_dir=str(p["annot"]))
    assert data["sections"]["artifacts"]["status"] == "ok"
    assert any(i.get("kind") == "run_ledger" for i in data["sections"]["artifacts"]["items"])


def test_html_is_self_contained_no_external(tmp_path):
    results = tmp_path / "data" / "results"
    results.mkdir(parents=True)
    out = tmp_path / "dash"
    build_dashboard.build_dashboard(str(results), str(out))
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "<style>" in index  # inline CSS
    assert "http://" not in index and "https://" not in index  # no external resources
    assert "<script src=" not in index  # no JS framework


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
