"""Tests for the V3 reviewer simulation / rebuttal kit (prompt 14)."""

from __future__ import annotations

import sys
from pathlib import Path

from certvic.io import write_json
from certvic.review import rebuttal_pack, simulate_reviews


def _paper(tmp_path, placeholders=True):
    paper = tmp_path / "paper"
    (paper / "sections").mkdir(parents=True)
    body = "\\section{Results}\n"
    body += "[RESULT REQUIRED]\n[RESULT REQUIRED]\n" if placeholders else "\\input{tables/main_results_table.tex}\n"
    (paper / "sections" / "05_results.tex").write_text(body, encoding="utf-8")
    return paper


def _reports(tmp_path, certified=False):
    reports = tmp_path / "reports"
    reports.mkdir()
    write_json(reports / "claim_ledger.json", [{
        "claim_id": "c1", "certification_status": "certified" if certified else "not_certified", "safe": certified,
    }])
    return reports


def test_six_profiles_present(tmp_path):
    paper = _paper(tmp_path)
    reports = _reports(tmp_path)
    result = simulate_reviews.simulate_reviews(str(paper), str(reports))
    profiles = {r["profile"] for r in result["reviews"]}
    assert profiles == set(simulate_reviews.REVIEWER_PROFILES)
    assert len(result["reviews"]) == 6


def test_complains_when_no_results_never_hallucinates(tmp_path):
    paper = _paper(tmp_path, placeholders=True)
    reports = _reports(tmp_path, certified=False)
    result = simulate_reviews.simulate_reviews(str(paper), str(reports))
    assert result["state"]["has_results"] is False
    # Every reviewer complains about missing results; none hallucinate.
    assert all(r["complained_about_missing_results"] for r in result["reviews"])
    assert result["any_hallucinated_results"] is False
    assert result["mean_score"] <= simulate_reviews.NO_RESULTS_SCORE


def test_scores_improve_with_results(tmp_path):
    paper = _paper(tmp_path, placeholders=False)
    reports = _reports(tmp_path, certified=True)
    result = simulate_reviews.simulate_reviews(str(paper), str(reports))
    assert result["state"]["has_results"] is True
    assert all(not r["complained_about_missing_results"] for r in result["reviews"])
    assert result["mean_score"] > simulate_reviews.NO_RESULTS_SCORE


def test_write_outputs(tmp_path):
    paper = _paper(tmp_path)
    reports = _reports(tmp_path)
    result = simulate_reviews.simulate_reviews(str(paper), str(reports))
    paths = simulate_reviews.write_outputs(result, str(tmp_path / "out"))
    assert Path(paths["reviews_json"]).exists()
    assert "Simulated CVPR Reviews" in Path(paths["reviews_md"]).read_text(encoding="utf-8")


def test_rebuttal_pack_marks_blocked_on_results(tmp_path):
    paper = _paper(tmp_path, placeholders=True)
    reports = _reports(tmp_path, certified=False)
    result = simulate_reviews.simulate_reviews(str(paper), str(reports))
    pack = rebuttal_pack.build_rebuttal(result)
    assert pack["n_points"] > 0
    assert pack["n_blocked_on_results"] >= 1   # missing-results complaints are honestly blocked
    assert pack["fabricated_results"] is False
    md = rebuttal_pack.render_report(pack)
    assert "Rebuttal Pack" in md
    assert "Blocked-on-results items" in md


def test_rebuttal_maps_stats_defense(tmp_path):
    fake_reviews = {"reviews": [{"profile": "stats_reviewer",
                                 "weaknesses": ["Optional stopping invalidates the statistics."],
                                 "questions": []}], "state": {"has_results": True}}
    pack = rebuttal_pack.build_rebuttal(fake_reviews)
    assert any("anytime-valid" in i["defense"].lower() for i in pack["items"])
    assert all(i["status"] != "blocked_on_results" for i in pack["items"])


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
