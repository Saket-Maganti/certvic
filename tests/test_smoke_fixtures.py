from pathlib import Path


def test_smoke_task_generation(smoke_tasks):
    assert len(smoke_tasks) == 12
    assert Path(smoke_tasks[0].original_image_path).exists()
    assert smoke_tasks[0].metadata["evidence_status"] == "MOCK_ONLY"
