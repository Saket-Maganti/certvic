"""Claim ledger builders."""

from __future__ import annotations

from certvic.schema import ClaimLedgerEntry


def build_claim_ledger(summary: dict, certification: dict, evidence_files: list[str]) -> list[ClaimLedgerEntry]:
    certified = bool(certification.get("certified"))
    text = (
        certification.get("safe_claim")
        if certified
        else "Smoke run completed with MOCK_ONLY synthetic fixtures; no evidence claim is certified."
    )
    return [
        ClaimLedgerEntry(
            claim_id="certvic_v1_smoke_gap",
            claim_text=text,
            evidence_files=evidence_files,
            metric_values=summary,
            certification_status="certified" if certified else "not_certified",
            safe=certified,
            limitations=[
                "Smoke fixtures are synthetic and MOCK_ONLY.",
                "Real pilot evidence is required before paper claims.",
                "Optional confidence sequences may be unavailable without certvic[stats].",
                *certification.get("certification_gate_errors", []),
            ],
        )
    ]
