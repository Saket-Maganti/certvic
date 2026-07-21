from certvic.edit.build_edits import main
from certvic.io import read_jsonl, write_jsonl


def test_edit_manifest_cli(smoke_tasks, tmp_path):
    tasks = tmp_path / "tasks.jsonl"
    out = tmp_path / "edits.jsonl"
    write_jsonl(tasks, smoke_tasks[:2])
    main(["--tasks", str(tasks), "--out-dir", str(tmp_path), "--out-manifest", str(out), "--mode", "smoke"])
    assert len(read_jsonl(out)) == 2
