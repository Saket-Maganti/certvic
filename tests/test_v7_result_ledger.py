"""Integrity tests for the V7 canonical result ledger + audit."""

from __future__ import annotations

import copy

from certvic.v7.result_ledger_audit import audit_ledger, build_ledger


def test_built_ledger_audits_clean():
    ledger = build_ledger(".")
    result = audit_ledger(ledger, ".")
    assert result["passed"] is True, result["failures"]
    assert result["n_rows"] == 6  # 3 models x {presence, absent_control}
    assert result["evidence_claims_made"] is False


def test_ledger_rows_are_pilot_only_and_canonical():
    ledger = build_ledger(".")
    for row in ledger["rows"]:
        assert row["claim_level"] == "pilot_only"
        assert row["canonical"] is True
        assert row["evidence_status"] == "HUMAN_REVIEWED_NON_EVIDENCE"
    assert ledger["paper_evidence"] is False


def test_every_metric_has_a_scoring_artifact_with_hash():
    ledger = build_ledger(".")
    for row in ledger["rows"]:
        scoring = row["artifacts"]["scoring"]
        assert scoring, row["result_id"]
        for art in scoring:
            assert art["exists"] is True
            assert art["sha256"]


def test_gate_artifact_path_missing_fires():
    ledger = build_ledger(".")
    ledger["rows"][0]["artifacts"]["scoring"][0]["path"] = "data/results/main_real_200/does_not_exist.json"
    result = audit_ledger(ledger, ".")
    assert result["passed"] is False
    assert any(f["gate"] == "artifact_path_missing" for f in result["failures"])


def test_gate_hash_mismatch_fires():
    ledger = build_ledger(".")
    ledger["rows"][0]["artifacts"]["scoring"][0]["sha256"] = "0" * 64
    result = audit_ledger(ledger, ".")
    assert result["passed"] is False
    assert any(f["gate"] == "hash_mismatch" for f in result["failures"])


def test_gate_number_without_artifact_fires():
    ledger = build_ledger(".")
    # Strip scoring artifacts but keep the metrics -> untraced number.
    ledger["rows"][0]["artifacts"]["scoring"] = []
    result = audit_ledger(ledger, ".")
    assert result["passed"] is False
    assert any(f["gate"] == "number_without_artifact" for f in result["failures"])


def test_gate_final_report_cited_as_canonical_fires():
    ledger = build_ledger(".")
    row = copy.deepcopy(ledger["rows"][0])
    row["result_id"] = "qwen2_5_vl_7b__presence_BAD"
    row["artifacts"]["scoring"].append(
        {"path": "data/results/main_real_200/final_report_v2/certification.json",
         "sha256": None, "exists": True}
    )
    ledger["rows"].append(row)
    result = audit_ledger(ledger, ".")
    assert result["passed"] is False
    assert any(f["gate"] == "non_canonical_cited" for f in result["failures"])


def test_gate_cross_model_contamination_fires_for_bare_qwen_dir():
    """An InternVL row citing Qwen's *bare* pilot_report/ file must be caught."""
    ledger = build_ledger(".")
    internvl_row = next(r for r in ledger["rows"] if r["provider"] == "internvl_8b"
                        and r["task_set"] == "presence")
    internvl_row["artifacts"]["scoring"][0]["path"] = (
        "data/results/main_real_200/pilot_report/pilot_result.json"  # Qwen's file
    )
    result = audit_ledger(ledger, ".")
    assert result["passed"] is False
    assert any(f["gate"] == "cross_model_contamination" for f in result["failures"])


def test_gate_mock_marked_claim_eligible_fires():
    ledger = build_ledger(".")
    ledger["rows"][0]["artifacts"]["scoring"].append(
        {"path": "data/results/v1_1_smoke_matrix/mock_spurious_flip/summary.json",
         "sha256": None, "exists": True}
    )
    result = audit_ledger(ledger, ".")
    assert result["passed"] is False
    assert any(f["gate"] == "mock_marked_claim_eligible" for f in result["failures"])


def test_internvl_llava_rows_never_reference_qwen_artifacts():
    ledger = build_ledger(".")
    for row in ledger["rows"]:
        if row["provider"] in {"internvl_8b", "llava_onevision_7b"}:
            for kind in ("scoring", "raw_predictions"):
                for art in row["artifacts"].get(kind, []):
                    assert "qwen" not in art["path"].lower()
                    assert "/pilot_report/" not in art["path"]
