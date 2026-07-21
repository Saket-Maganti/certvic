import csv

from certvic.io import write_jsonl
from certvic.validation.human_sheet import export_human_sheet


def test_sheet_hides_answers_by_default(smoke_tasks, tmp_path):
    tasks_path = tmp_path / "tasks.jsonl"
    out = tmp_path / "sheet.csv"
    write_jsonl(tasks_path, smoke_tasks[:1])
    export_human_sheet(str(tasks_path), str(out))
    fields = next(csv.DictReader(out.open()))
    assert "answer_original" not in fields
