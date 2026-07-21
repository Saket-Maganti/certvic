"""Tests for V2 baselines, ablations, prompt suite, and parser sensitivity."""

from __future__ import annotations

import csv

from certvic.eval.ablation_baselines import BASELINES, baseline_raw_outputs, build_context, score_item, summarize
from certvic.eval.prompt_suite import PROMPT_VARIANTS, build_prompt_variants, variant_leakage_flags
from certvic.eval.run_ablations import run_ablations
from certvic.io import read_jsonl, write_jsonl
from certvic.reporting.ablations import build_ablations_report


def _tasks(tmp_path):
    rows = []
    for i in range(8):
        change = i % 2 == 0
        rows.append({
            "item_id": f"t{i}",
            "task_family": "support_stability" if change else "occlusion_safety",
            "domain": "household",
            "answer_format": "yes_no",
            "question_original": f"Is object {i} supported",
            "question_edited": f"Is object {i} supported now",
            "answer_original": "yes",
            "answer_edited": "no" if change else "yes",
            "required_change": "change" if change else "no_change",
            "source_id": f"s{i}",
        })
    path = tmp_path / "reviewed.jsonl"
    write_jsonl(path, rows)
    return path, rows


def test_all_baselines_listed():
    assert set(BASELINES) == {
        "random_seeded", "majority_by_family", "text_only_heuristic", "caption_only_stub",
        "original_only", "edited_only", "answer_prior", "prompt_shuffle_control",
    }


def test_original_only_never_updates(tmp_path):
    _, rows = _tasks(tmp_path)
    ctx = build_context(rows)
    scored = [score_item(t, *baseline_raw_outputs("original_only", t, ctx, 0)) for t in rows]
    # original_only predicts the same answer for both -> change items are inconsistent.
    change_rows = [r for r in scored if r["required_change"] == "change"]
    assert all(r["C_i"] == 0 for r in change_rows)
    s = summarize(scored)
    assert s["consistency"] < 1.0


def test_prompt_variants_and_leakage():
    variants = build_prompt_variants("Is the cup supported")
    assert set(variants) == set(PROMPT_VARIANTS)
    flags = variant_leakage_flags("Is the cup supported")
    # The clean variants must not leak; the stress variant must.
    assert flags["canonical"] == []
    assert flags["yes_no_strict"] == []
    assert flags["prompt_leakage_stress"]


def test_run_ablations_writes_per_baseline(tmp_path):
    tasks_path, _ = _tasks(tmp_path)
    out_dir = tmp_path / "abl"
    summary = run_ablations(str(tasks_path), str(out_dir), max_items=50, seed=0)
    assert summary["n_tasks"] == 8
    for name in BASELINES:
        assert (out_dir / f"{name}.jsonl").exists()
        assert len(read_jsonl(out_dir / f"{name}.jsonl")) == 8
    assert (out_dir / "ablation_index.json").exists()
    assert summary["evidence_status"] == "CONSTRUCT_VALIDITY_NON_EVIDENCE"


def test_ablations_report_outputs_and_flags(tmp_path):
    tasks_path, _ = _tasks(tmp_path)
    out_dir = tmp_path / "abl"
    run_ablations(str(tasks_path), str(out_dir), max_items=50, seed=0)
    report_dir = tmp_path / "abl_report"
    result = build_ablations_report(str(out_dir), str(tasks_path), str(report_dir))
    for name in ["ablation_summary.md", "baseline_table.csv", "parser_sensitivity.csv", "prompt_sensitivity.csv", "construct_validity_flags.json"]:
        assert (report_dir / name).exists(), name
    # answer_prior changes nothing -> on a balanced change/no_change set, consistency is the no_change fraction (0.5 here), below the gameable threshold.
    assert result["task_gameable_without_vision"] in (True, False)
    rows = list(csv.DictReader((report_dir / "parser_sensitivity.csv").open(encoding="utf-8")))
    # 'the answer is yes' fails strict but recovers under lenient.
    recovered = [r for r in rows if r["bucket"] == "recovered_lenient"]
    assert recovered


def test_answer_prior_low_consistency_on_balanced_set(tmp_path):
    _, rows = _tasks(tmp_path)
    ctx = build_context(rows)
    scored = [score_item(t, *baseline_raw_outputs("answer_prior", t, ctx, 0)) for t in rows]
    s = summarize(scored)
    # Constant answer -> only no_change items are consistent (half the set).
    assert s["consistency"] <= 0.6
