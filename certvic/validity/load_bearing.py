"""Analyze whether item-validity certification changes measured gaps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from certvic.io import read_jsonl
from certvic.validity.certificate_schema import status_passes

NON_EVIDENCE_MARKERS = (
    "mock",
    "smoke",
    "simulated",
    "planned",
    "preview",
    "generated_edit_only",
    "edit_ready_non_evidence",
)


@dataclass(frozen=True)
class GateStage:
    name: str
    description: str
    predicate: Callable[[dict | None], bool]


def _certs_by_item(certificates: list[dict]) -> dict[str, dict]:
    return {str(row.get("item_id")): row for row in certificates if row.get("item_id")}


def _passes(cert: dict | None, *fields: str) -> bool:
    if cert is None:
        return False
    return all(status_passes(str(cert.get(field, "unknown"))) for field in fields)


STAGES = (
    GateStage("naive_all_items", "All scored rows before item-validity filtering.", lambda cert: True),
    GateStage("after_quality_gates", "Rows whose certificate passes edit quality gates.", lambda cert: _passes(cert, "quality_gate_status")),
    GateStage(
        "after_detectability_gate",
        "Rows whose certificate passes quality and edit-detectability gates.",
        lambda cert: _passes(cert, "quality_gate_status", "detectability_status"),
    ),
    GateStage(
        "after_human_realism_single_factor_gate",
        "Rows passing quality, detectability, visual realism, photorealism, and single-factor gates.",
        lambda cert: _passes(
            cert,
            "quality_gate_status",
            "detectability_status",
            "visual_review_status",
            "photorealism_status",
            "single_factor_status",
        ),
    ),
    GateStage(
        "after_answerability_gate",
        "Rows passing all above gates plus human answerability.",
        lambda cert: _passes(
            cert,
            "quality_gate_status",
            "detectability_status",
            "visual_review_status",
            "photorealism_status",
            "single_factor_status",
            "human_answerability_status",
        ),
    ),
    GateStage(
        "final_certificate_eligible",
        "Only rows with evidence_eligible_candidate=true in the certificate.",
        lambda cert: bool(cert and cert.get("evidence_eligible_candidate")),
    ),
)


def score_gap(rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {
            "n": 0,
            "original_accuracy": None,
            "consistency_rate": None,
            "intervention_consistency_gap": None,
            "parse_failure_rate": None,
        }
    original_accuracy = sum(1 for row in rows if bool(row.get("original_correct"))) / n
    consistency_rate = sum(1 for row in rows if bool(row.get("consistent"))) / n
    parse_failure_rate = sum(1 for row in rows if not bool(row.get("parse_ok", True))) / n
    return {
        "n": n,
        "original_accuracy": original_accuracy,
        "consistency_rate": consistency_rate,
        "intervention_consistency_gap": original_accuracy - consistency_rate,
        "parse_failure_rate": parse_failure_rate,
    }


def _is_non_evidence(rows: list[dict]) -> bool:
    if not rows:
        return True
    statuses: list[str] = []
    for row in rows:
        metadata = row.get("metadata") or {}
        statuses.append(str(metadata.get("evidence_status") or metadata.get("claim_status") or "unknown"))
    joined = " ".join(statuses).lower()
    return any(marker in joined for marker in NON_EVIDENCE_MARKERS) or "unknown" in joined


def analyze_load_bearing(
    scores_path: str,
    certificates_path: str,
    *,
    material_gap_shift: float = 0.02,
) -> dict:
    scores = read_jsonl(scores_path)
    certificates = read_jsonl(certificates_path)
    certs = _certs_by_item(certificates)
    stage_rows: list[dict] = []

    for stage in STAGES:
        rows = [
            row
            for row in scores
            if stage.predicate(certs.get(str(row.get("item_id"))))
        ]
        stage_rows.append({"stage": stage.name, "description": stage.description, **score_gap(rows)})

    naive = stage_rows[0]["intervention_consistency_gap"]
    final = stage_rows[-1]["intervention_consistency_gap"]
    gap_shift = None if naive is None or final is None else final - naive
    material = gap_shift is not None and abs(gap_shift) >= material_gap_shift
    missing_certificate_items = sorted(
        str(row.get("item_id")) for row in scores if str(row.get("item_id")) not in certs
    )
    return {
        "analysis": "validity_load_bearing",
        "scores": scores_path,
        "certificates": certificates_path,
        "analysis_status": "NON_EVIDENCE_ANALYSIS_ONLY" if _is_non_evidence(scores) else "REAL_RUN_ANALYSIS_PENDING_CLAIM_GATES",
        "certificate_is_load_bearing": bool(material),
        "certificate_not_yet_load_bearing": not bool(material),
        "gap_shift": gap_shift,
        "material_gap_shift_threshold": material_gap_shift,
        "n_scores": len(scores),
        "n_certificates": len(certificates),
        "missing_certificate_items": missing_certificate_items,
        "stages": stage_rows,
        "claim_status": "NO_CERTIFIED_CLAIMS_EMITTED",
    }
