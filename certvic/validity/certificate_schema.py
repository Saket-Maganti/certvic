"""Schema for future item validity certificates."""

from __future__ import annotations

from pydantic import Field

from certvic.schema.base import CertVICModel

CERTIFICATE_VERSION = "v5_item_certificate_1"
PASS_VALUES = {"pass", "passed", "ok", "clean", "eligible", "yes", "true"}
BLOCKING_FIELDS = (
    "quality_gate_status",
    "detectability_status",
    "visual_review_status",
    "human_answerability_status",
    "single_factor_status",
    "photorealism_status",
    "leakage_status",
)


class ItemValidityCertificate(CertVICModel):
    item_id: str
    source_id: str | None = None
    edit_id: str | None = None
    mask_id: str | None = None
    task_family: str | None = None
    domain: str | None = None
    label_policy_status: str = "unknown"
    quality_gate_status: str = "unknown"
    detectability_status: str = "unknown"
    visual_review_status: str = "unknown"
    human_answerability_status: str = "unknown"
    control_compatibility_status: str = "unknown"
    single_factor_status: str = "unknown"
    photorealism_status: str = "unknown"
    leakage_status: str = "unknown"
    provenance_status: str = "unknown"
    evidence_eligible_candidate: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    certificate_version: str = CERTIFICATE_VERSION
    input_hashes: dict[str, str] = Field(default_factory=dict)


def status_passes(value: str | None) -> bool:
    return str(value or "").strip().lower() in PASS_VALUES

