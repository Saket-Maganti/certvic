
from certvic.reporting.tables import write_group_table, write_main_table


def test_table_generation(tmp_path):
    csv_path = tmp_path / "table.csv"
    tex_path = tmp_path / "table.tex"
    write_group_table({"a": {"n": 1}}, str(csv_path), str(tex_path))
    write_main_table({"n": 1}, {"certified": False, "lower_bound": None}, str(tmp_path / "main.tex"))
    assert csv_path.exists()
    assert tex_path.exists()
