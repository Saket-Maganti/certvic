"""Evaluation task item schema."""

from __future__ import annotations

from pydantic import Field, model_validator

from certvic.schema.base import AnswerFormat, CertVICModel, Domain, RequiredChange, TaskFamily
from certvic.schema.edit import EditSpec
from certvic.schema.source import MaskRecord, SourceImageRecord


class TaskItem(CertVICModel):
    item_id: str
    source: SourceImageRecord
    mask: MaskRecord | None = None
    edit: EditSpec
    original_image_path: str
    edited_image_path: str
    question_original: str
    question_edited: str
    answer_original: str
    answer_edited: str
    required_change: RequiredChange
    answer_format: AnswerFormat
    task_family: TaskFamily
    domain: Domain
    split: str
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_change_semantics(self) -> "TaskItem":
        if self.required_change == RequiredChange.CHANGE:
            if self.answer_original == self.answer_edited:
                raise ValueError("required_change=change requires different expected answers")
        if self.required_change == RequiredChange.NO_CHANGE:
            if self.answer_original != self.answer_edited and not self.metadata.get(
                "safety_invariant_allows_answer_difference"
            ):
                raise ValueError("required_change=no_change requires same expected answers")
        if self.task_family != self.edit.task_family:
            raise ValueError("task_family must match edit.task_family")
        if self.domain != self.edit.domain:
            raise ValueError("domain must match edit.domain")
        return self
