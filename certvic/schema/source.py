"""Source and mask schemas."""

from __future__ import annotations

from pydantic import Field, field_validator

from certvic.schema.base import CertVICModel, LicenseCategory


class SourceImageRecord(CertVICModel):
    source_id: str
    source_name: str
    source_url_or_pointer: str | None = None
    local_path: str | None = None
    sha256: str | None = None
    license_category: LicenseCategory
    license_text: str | None = None
    redistribution_allowed: bool = False
    notes: str | None = None


class MaskRecord(CertVICModel):
    mask_id: str
    source_id: str
    mask_path: str
    object_label: str
    bbox_xyxy: list[int] = Field(min_length=4, max_length=4)
    mask_sha256: str | None = None
    method: str
    quality_notes: str | None = None
    label_id: int | None = None
    annotation_path: str | None = None
    mask_area_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)

    @field_validator("bbox_xyxy")
    @classmethod
    def bbox_must_be_nonnegative(cls, value: list[int]) -> list[int]:
        if any(coord < 0 for coord in value):
            raise ValueError("bbox coordinates must be nonnegative")
        x1, y1, x2, y2 = value
        if x2 <= x1 or y2 <= y1:
            raise ValueError("bbox must have positive width and height")
        return value
