"""Prediction and pair-score schemas."""

from __future__ import annotations

from pydantic import Field

from certvic.schema.base import CertVICModel, ImageVariant, ProviderType, RequiredChange


class PredictionRecord(CertVICModel):
    run_id: str
    item_id: str
    provider_name: str
    provider_type: ProviderType
    model_name: str
    model_version: str
    image_variant: ImageVariant
    prompt: str
    raw_output: str
    parsed_answer: str | None
    parse_confidence: float = Field(ge=0.0, le=1.0)
    parse_ok: bool = True
    latency_s: float | None = None
    timestamp_utc: str
    metadata: dict = Field(default_factory=dict)


class PairScore(CertVICModel):
    run_id: str
    item_id: str
    provider_name: str
    model_name: str
    task_family: str
    domain: str
    original_correct: bool
    edited_correct: bool
    consistent: bool
    required_change: RequiredChange
    parse_ok: bool
    notes: str | None = None
    metadata: dict = Field(default_factory=dict)
