from certvic.eval.run_eval import run_eval
from certvic.io import read_jsonl, write_jsonl


def test_runner_writes_and_resumes(smoke_tasks, tmp_path):
    tasks_path = tmp_path / "tasks.jsonl"
    preds_path = tmp_path / "preds.jsonl"
    config_path = tmp_path / "smoke.yaml"
    write_jsonl(tasks_path, smoke_tasks[:2])
    config_path.write_text("paid_services_enabled: false\n", encoding="utf-8")
    first = run_eval(str(config_path), str(tasks_path), str(preds_path), "mock_inconsistent", "run", max_items=2)
    second = run_eval(str(config_path), str(tasks_path), str(preds_path), "mock_inconsistent", "run", max_items=2)
    assert first["written"] == 4
    assert second["skipped"] == 4
    assert len(read_jsonl(preds_path)) == 4


def test_runner_overwrite_replaces_predictions(smoke_tasks, tmp_path):
    tasks_path = tmp_path / "tasks.jsonl"
    preds_path = tmp_path / "preds.jsonl"
    config_path = tmp_path / "smoke.yaml"
    write_jsonl(tasks_path, smoke_tasks[:1])
    config_path.write_text("paid_services_enabled: false\n", encoding="utf-8")
    run_eval(str(config_path), str(tasks_path), str(preds_path), "mock_perfect", "run", max_items=1)
    run_eval(
        str(config_path),
        str(tasks_path),
        str(preds_path),
        "mock_perfect",
        "run",
        max_items=1,
        overwrite=True,
    )
    assert len(read_jsonl(preds_path)) == 2
