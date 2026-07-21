from certvic.data.manifest_checks import check_task_manifest
from certvic.io import write_jsonl


def test_manifest_check_passes(smoke_tasks, tmp_path):
    path = tmp_path / "tasks.jsonl"
    write_jsonl(path, smoke_tasks)
    assert check_task_manifest(str(path), strict=True)["passed"]


def test_manifest_check_duplicate_fails(smoke_tasks, tmp_path):
    path = tmp_path / "tasks.jsonl"
    write_jsonl(path, [smoke_tasks[0], smoke_tasks[0]])
    assert not check_task_manifest(str(path), strict=True)["passed"]
