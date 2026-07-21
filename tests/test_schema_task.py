import pytest
from pydantic import ValidationError

from certvic.schema import RequiredChange, TaskItem


def test_required_change_consistency(smoke_tasks):
    task = smoke_tasks[0]
    assert task.required_change == RequiredChange.CHANGE.value
    data = task.model_dump(mode="json")
    data["answer_edited"] = data["answer_original"]
    with pytest.raises(ValidationError):
        TaskItem.model_validate(data)


def test_task_json_roundtrip(smoke_tasks):
    task = smoke_tasks[0]
    assert TaskItem.model_validate(task.model_dump(mode="json")).item_id == task.item_id
