"""Claim ledger schemas."""

from __future__ import annotations

from pydantic import Field

from certvic.schema.base import CertVICModel


class ClaimLedgerEntry(CertVICModel):
    claim_id: str
    claim_text: str
    evidence_files: list[str] = Field(default_factory=list)
    metric_values: dict = Field(default_factory=dict)
    certification_status: str = "not_certified"
    safe: bool = False
    limitations: list[str] = Field(default_factory=list)
