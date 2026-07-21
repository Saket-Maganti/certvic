from certvic.data.build_tasks import build_smoke_tasks
from certvic.io import read_jsonl


def test_build_smoke_tasks(tmp_path):
    out = tmp_path / "tasks.jsonl"
    summary = build_smoke_tasks(str(out), n_items=10)
    assert summary["n"] == 10
    assert len(read_jsonl(out)) == 10
