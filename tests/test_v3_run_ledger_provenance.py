"""Tests for the V3 run ledger / provenance system (prompt 01)."""

from __future__ import annotations

import json
import sys

import pytest

from certvic.io import write_json
from certvic.provenance import artifact_graph, run_ledger, trace_claim


def _seed_artifact(path, text="hello"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


# --- run_ledger ------------------------------------------------------------

def test_init_and_add_positive_path(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    run_ledger.init_ledger(ledger)
    assert ledger.exists()

    inp = _seed_artifact(tmp_path / "in.txt", "input")
    out = _seed_artifact(tmp_path / "out.txt", "output")
    cfg = _seed_artifact(tmp_path / "cfg.yaml", "k: v")

    entry = run_ledger.add_entry(
        ledger_path=ledger,
        run_id="r1",
        stage="edit_generation",
        command="python3 -m certvic.edit.build_edits",
        config=cfg,
        inputs=[inp],
        outputs=[out],
        evidence_status="real_evidence",
        user_notes="first run",
    )
    assert entry.evidence_status == "REAL_EVIDENCE"  # normalized to upper
    assert entry.zero_cost is True and entry.paid_services_used is False
    assert entry.input_hashes[inp] is not None
    assert entry.output_hashes[out] is not None
    assert entry.config_hash is not None

    loaded = run_ledger.load_ledger(ledger)
    assert len(loaded) == 1 and loaded[0].run_id == "r1"


def test_missing_artifact_hashes_to_none(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    entry = run_ledger.add_entry(
        ledger_path=ledger,
        run_id="r2",
        stage="scoring",
        inputs=[str(tmp_path / "does_not_exist.jsonl")],
        outputs=["planned://future_output"],
    )
    # Missing local file -> None; remote/planned pointer -> None (never fetched).
    assert entry.input_hashes[str(tmp_path / "does_not_exist.jsonl")] is None
    assert entry.output_hashes["planned://future_output"] is None


def test_directory_hash_is_stable_and_content_sensitive(tmp_path):
    d = tmp_path / "dir"
    _seed_artifact(d / "a.txt", "a")
    h1 = run_ledger.hash_path(d)
    h2 = run_ledger.hash_path(d)
    assert h1 == h2 and h1 is not None
    _seed_artifact(d / "b.txt", "b")
    assert run_ledger.hash_path(d) != h1


def test_paid_services_flag_sets_zero_cost_false(tmp_path):
    entry = run_ledger.add_entry(
        ledger_path=tmp_path / "l.jsonl",
        run_id="r3",
        stage="vlm_inference",
        paid_services_used=True,
    )
    assert entry.paid_services_used is True and entry.zero_cost is False


def test_environment_summary_is_import_safe():
    env = run_ledger.environment_summary()
    assert "python_version" in env and "torch_available" in env
    # No heavy module should have been imported as a side effect.
    assert "torch" not in sys.modules


def test_load_ledger_rejects_malformed(tmp_path):
    ledger = tmp_path / "bad.jsonl"
    ledger.write_text(json.dumps({"run_id": "x"}) + "\n", encoding="utf-8")  # missing required fields
    with pytest.raises(Exception):
        run_ledger.load_ledger(ledger)


# --- artifact_graph --------------------------------------------------------

def test_artifact_graph_healthy(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    out = _seed_artifact(tmp_path / "out.txt", "v1")
    run_ledger.add_entry(ledger_path=ledger, run_id="r1", stage="scoring", outputs=[out])
    graph = artifact_graph.build_artifact_graph(ledger)
    assert graph["healthy"] is True
    assert graph["n_runs"] == 1 and graph["n_artifacts"] == 1
    assert graph["evidence_claims_made"] is False


def test_artifact_graph_detects_missing_and_mismatch(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    out = _seed_artifact(tmp_path / "out.txt", "v1")
    gone = str(tmp_path / "gone.txt")
    _seed_artifact(tmp_path / "gone.txt", "temp")
    run_ledger.add_entry(ledger_path=ledger, run_id="r1", stage="scoring", outputs=[out, gone])
    # Mutate one output, delete another -> mismatch + missing.
    (tmp_path / "out.txt").write_text("v2", encoding="utf-8")
    (tmp_path / "gone.txt").unlink()

    graph = artifact_graph.build_artifact_graph(ledger)
    assert out in graph["hash_mismatches"]
    assert gone in graph["missing_artifacts"]
    assert graph["healthy"] is False

    dot = artifact_graph.render_dot(graph)
    assert "digraph" in dot
    paths = artifact_graph.write_graph(graph, tmp_path / "g")
    assert all(__import__("pathlib").Path(p).exists() for p in paths.values())


def test_artifact_graph_flags_orphan_inputs(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    orphan = _seed_artifact(tmp_path / "orphan.txt", "x")
    run_ledger.add_entry(ledger_path=ledger, run_id="r1", stage="scoring", inputs=[orphan])
    graph = artifact_graph.build_artifact_graph(ledger)
    assert orphan in graph["orphan_inputs"]


# --- trace_claim -----------------------------------------------------------

def _claim_ledger(tmp_path, evidence_files, status="certified", claim_id="c1"):
    path = tmp_path / "claim_ledger.json"
    write_json(path, [{
        "claim_id": claim_id,
        "claim_text": "delta is certified positive",
        "evidence_files": [str(f) for f in evidence_files],
        "certification_status": status,
        "safe": status == "certified",
    }])
    return path


def test_trace_complete_for_evidence_run(tmp_path):
    ledger = tmp_path / "run.jsonl"
    out = _seed_artifact(tmp_path / "scores.jsonl", "scores")
    run_ledger.add_entry(ledger_path=ledger, run_id="r1", stage="scoring", outputs=[out], evidence_status="REAL_EVIDENCE")
    claims = _claim_ledger(tmp_path, [out])
    result = trace_claim.trace_claims(claims, ledger)
    assert result["ok"] is True
    assert result["claims"][0]["status"] == trace_claim.TRACE_COMPLETE
    assert result["n_integrity_violations"] == 0


def test_trace_flags_ineligible_evidence(tmp_path):
    ledger = tmp_path / "run.jsonl"
    out = _seed_artifact(tmp_path / "scores.jsonl", "scores")
    run_ledger.add_entry(ledger_path=ledger, run_id="r1", stage="scoring", outputs=[out], evidence_status="SIMULATED_ONLY")
    claims = _claim_ledger(tmp_path, [out])
    result = trace_claim.trace_claims(claims, ledger)
    assert result["claims"][0]["status"] == trace_claim.INELIGIBLE_EVIDENCE
    assert result["claims"][0]["integrity_violation"] is True
    assert result["ok"] is False


def test_trace_flags_missing_and_mismatch(tmp_path):
    ledger = tmp_path / "run.jsonl"
    out = _seed_artifact(tmp_path / "scores.jsonl", "scores")
    run_ledger.add_entry(ledger_path=ledger, run_id="r1", stage="scoring", outputs=[out], evidence_status="REAL_EVIDENCE")
    claims = _claim_ledger(tmp_path, [out])
    (tmp_path / "scores.jsonl").write_text("mutated", encoding="utf-8")
    result = trace_claim.trace_claims(claims, ledger)
    assert result["claims"][0]["status"] == trace_claim.HASH_MISMATCH

    (tmp_path / "scores.jsonl").unlink()
    result2 = trace_claim.trace_claims(claims, ledger)
    assert result2["claims"][0]["status"] == trace_claim.MISSING_ARTIFACT


def test_trace_unknown_when_no_producer(tmp_path):
    ledger = tmp_path / "run.jsonl"
    run_ledger.init_ledger(ledger)
    out = _seed_artifact(tmp_path / "scores.jsonl", "scores")
    claims = _claim_ledger(tmp_path, [out], status="not_certified")
    result = trace_claim.trace_claims(claims, ledger)
    assert result["claims"][0]["status"] == trace_claim.UNKNOWN
    # Not certified, so untraceable status is not an integrity violation.
    assert result["claims"][0]["integrity_violation"] is False


def test_report_renderers_produce_markdown(tmp_path):
    ledger = tmp_path / "run.jsonl"
    out = _seed_artifact(tmp_path / "scores.jsonl", "scores")
    run_ledger.add_entry(ledger_path=ledger, run_id="r1", stage="scoring", outputs=[out], evidence_status="REAL_EVIDENCE")
    graph = artifact_graph.build_artifact_graph(ledger)
    assert artifact_graph.render_report(graph).startswith("# Artifact Provenance Graph")
    claims = _claim_ledger(tmp_path, [out])
    result = trace_claim.trace_claims(claims, ledger)
    assert "Claim Provenance Trace Report" in trace_claim.render_report(result)
