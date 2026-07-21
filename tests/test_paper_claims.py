from certvic.validation.paper_claims import scan_paper


def test_paper_scanner_catches_bad_phrase(tmp_path):
    paper = tmp_path / "paper.tex"
    paper.write_text("\\section{Limitations} safe for autonomous driving", encoding="utf-8")
    assert not scan_paper(str(paper))["passed"]
