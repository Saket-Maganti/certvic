from certvic.providers.mock import MockProvider


def test_mock_provider_inconsistent(smoke_tasks):
    provider = MockProvider("inconsistent")
    provider.set_task_context(smoke_tasks)
    task = smoke_tasks[0]
    assert provider.answer(task.original_image_path, task.question_original) == task.answer_original
    assert provider.answer(task.edited_image_path, task.question_edited) == task.answer_original
