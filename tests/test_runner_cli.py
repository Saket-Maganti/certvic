import subprocess
import sys

from certvic.io import write_jsonl


def test_runner_cli_smoke(smoke_tasks, tmp_path):
    tasks_path = tmp_path / "tasks.jsonl"
    preds_path = tmp_path / "preds.jsonl"
    config_path = tmp_path / "smoke.yaml"
    write_jsonl(tasks_path, smoke_tasks[:1])
    config_path.write_text("paid_services_enabled: false\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "certvic.eval.run_eval",
            "--config",
            str(config_path),
            "--tasks",
            str(tasks_path),
            "--out",
            str(preds_path),
            "--provider",
            "mock_inconsistent",
            "--run-id",
            "cli",
            "--max-items",
            "1",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"written": 2' in result.stdout
