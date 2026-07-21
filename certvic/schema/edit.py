"""Edit specification schema."""

from __future__ import annotations

from pydantic import Field, model_validator

from certvic.schema.base import CertVICModel, Domain, EditType, TaskFamily


class EditSpec(CertVICModel):
    edit_id: str
    source_id: str
    mask_id: str | None = None
    edit_type: EditType
    task_family: TaskFamily
    domain: Domain
    seed: int = 0
    params: dict = Field(default_factory=dict)
    expected_effect: str
    single_factor: bool = True
    edited_image_path: str | None = None
    edited_sha256: str | None = None

    @model_validator(mode="after")
    def validate_edit_policy(self) -> "EditSpec":
        if self.task_family != TaskFamily.CONTROL_IRRELEVANT and self.edit_type != EditType.NONE:
            if not self.single_factor:
                raise ValueError("non-control edited items must be single_factor")
        if self.edit_type == EditType.NONE and self.task_family != TaskFamily.CONTROL_IRRELEVANT:
            if self.params.get("allow_none_for_smoke") is not True:
                raise ValueError("edit_type=none is only allowed for control or explicit smoke use")
        return self
