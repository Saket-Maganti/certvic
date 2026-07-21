from pathlib import Path


def test_paper_scaffold_has_placeholders_and_no_bad_claims():
    root = Path("paper/sections")
    expected = [
        "01_intro.tex",
        "02_related.tex",
        "03_method.tex",
        "04_experiments.tex",
        "05_results.tex",
        "06_limitations.tex",
        "07_conclusion.tex",
    ]
    for name in expected:
        assert (root / name).exists()
    text = "\n".join((root / name).read_text(encoding="utf-8") for name in expected).lower()
    assert "[result required]" in text
    assert "frontier models fail" not in text
