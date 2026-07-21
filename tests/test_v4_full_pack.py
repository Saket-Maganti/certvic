"""Integration tests for the V4 full prompt pack."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from certvic.data.fallback_sources import fallback_options
from certvic.data.license_matrix import dataset_license_matrix
from certvic.data.showcase_split import build_showcase_split
from certvic.edit.parameter_sweep import build_sweep_plan
from certvic.eval.merge_predictions import merge_predictions
from certvic.metrics.sensitivity_suite import build_sensitivity_suite
from certvic.models.cache_check import check_cache_manifest
from certvic.models.cache_manifest import build_cache_manifest
from certvic.notebooks.colab_notebook_builder import write_colab_notebook
from certvic.notebooks.kaggle_notebook_builder import write_kaggle_notebook
from certvic.paper.qualitative_figures import build_qualitative_figures
from certvic.paper.supplement_generator import generate_supplement
from certvic.planning.ablation_plan import build_ablation_plan
from certvic.recovery.inspect_run import inspect_run
from certvic.recovery.repair_manifests import repair_manifest
from certvic.release.capsule_validator import validate_capsule
from certvic.release.showcase_package import package_showcase
from certvic.reporting.model_comparison import build_model_comparison
from certvic.results.compare_lockfile import compare_lockfile
from certvic.results.freeze_results import freeze_results
from certvic.review_app.build_static_app import build_static_app
from certvic.submission.deadline_plan import build_deadline_plan
from certvic.submission.internal_review_packet import build_internal_review_packet
from certvic.troubleshoot.diagnose_logs import diagnose_log
from certvic.validation.reviewer_quality import analyze_reviewer_quality
from certvic.v4.final_all_system_audit import run_final_audit


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def test_v4_notebook_builders_emit_safe_valid_json(tmp_path):
    kaggle = tmp_path / "kaggle.ipynb"
    colab = tmp_path / "colab.ipynb"
    write_kaggle_notebook("diffusion_tiny", str(kaggle))
    write_colab_notebook("vlm_tiny", str(colab))
    k = json.loads(kaggle.read_text(encoding="utf-8"))
    c = json.loads(colab.read_text(encoding="utf-8"))
    assert k["nbformat"] == 4 and c["nbformat"] == 4
    all_text = json.dumps(k) + json.dumps(c)
    assert "zero-cost policy" in all_text
    assert "OPENAI_API_KEY" not in all_text
    assert "--resume" in all_text or "Resume-safe" in all_text
    assert "Drive mount disabled by default" in all_text


def test_v4_model_cache_manifest_and_check_are_no_download(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "weights.bin").write_text("tiny", encoding="utf-8")
    manifest = build_cache_manifest("qwen2_5_vl_7b", str(cache), hash_files=True)
    assert manifest["downloads_attempted"] is False
    assert manifest["n_files"] == 1
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert check_cache_manifest(str(manifest_path))["passed"] is True
    missing = build_cache_manifest("qwen2_5_vl_7b", str(tmp_path / "missing"))
    assert missing["missing"] == ["cache_root_missing"]


def test_v4_fallback_and_license_reports_are_pointer_first():
    options = fallback_options()
    matrix = dataset_license_matrix()
    assert options[0]["dataset"] == "ADE20K"
    assert options[0]["role"] == "primary"
    assert all(option.get("downloads_attempted") is False for option in options)
    assert any(row["figure_safe"] for row in matrix)
    assert all(row["legal_overclaim"] is False for row in matrix)


def test_v4_showcase_split_allows_only_cc0_pd_and_no_pixel_copy(tmp_path):
    sources = tmp_path / "sources.jsonl"
    split = tmp_path / "showcase.jsonl"
    _jsonl(
        sources,
        [
            {"source_id": "ok", "license": "cc0", "redistributable": True},
            {"source_id": "bad", "license": "cc-by", "redistributable": True},
        ],
    )
    summary = build_showcase_split(str(sources), str(split))
    package = package_showcase(str(split), str(tmp_path / "release"))
    assert summary["accepted"] == 1
    assert summary["pixels_copied"] is False
    assert package["pixels_copied"] is False


def test_v4_edit_sweep_review_app_and_recovery_tools(tmp_path):
    edit_plan = tmp_path / "edit_plan.jsonl"
    _jsonl(edit_plan, [{"edit_id": "e1", "edit_type": "remove"}, {"edit_id": "e2", "edit_type": "occlude"}])
    summary = build_sweep_plan(str(edit_plan), str(tmp_path / "sweep.jsonl"), max_combinations=3)
    assert summary["n_combinations"] == 3
    assert summary["executed"] is False

    sheet = tmp_path / "review.csv"
    with sheet.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_id", "original_image_path", "edited_image_path", "task_family", "edit_type", "required_change"])
        writer.writeheader()
        writer.writerow({"item_id": "i1", "original_image_path": "orig.png", "edited_image_path": "edit.png", "task_family": "support", "edit_type": "remove", "required_change": "change"})
    app = build_static_app(str(sheet), str(tmp_path / "app"))
    assert app["external_services"] is False
    assert app["pixels_copied"] is False
    assert app["ground_truth_hidden"] is True

    broken = tmp_path / "run" / "broken.jsonl"
    _jsonl(broken, [{"item_id": "i1"}, {"item_id": "i1"}])
    inspected = inspect_run(str(broken.parent))
    repair = repair_manifest(str(broken), str(tmp_path / "repaired.jsonl"), dry_run=True)
    assert inspected["duplicates"]
    assert repair["dry_run"] is True
    assert repair["hash_mismatches_fixed"] is False


def test_v4_prediction_merge_model_comparison_and_sensitivity(tmp_path):
    preds_dir = tmp_path / "preds"
    _jsonl(
        preds_dir / "a.jsonl",
        [
            {"run_id": "r", "item_id": "i1", "image_variant": "original", "provider_name": "qwen", "raw_output": "yes", "parsed_answer": "yes", "parse_ok": True},
            {"run_id": "r", "item_id": "i1", "image_variant": "original", "provider_name": "qwen", "raw_output": "no", "parsed_answer": "no", "parse_ok": True},
        ],
    )
    tasks = tmp_path / "tasks.jsonl"
    _jsonl(tasks, [{"item_id": "i1"}, {"item_id": "i2"}])
    merge = merge_predictions([str(preds_dir)], str(tmp_path / "merged.jsonl"), str(tmp_path / "merge.json"), tasks=str(tasks))
    assert merge["duplicates"] == 1
    assert merge["conflicts"] == 1
    assert merge["missing_items"] == 1

    scores = tmp_path / "scores.jsonl"
    _jsonl(
        scores,
        [
            {"provider_name": "qwen", "model_name": "qwen", "consistent": True, "parse_ok": True, "metadata": {"evidence_status": "MOCK_ONLY"}},
            {"provider_name": "qwen", "model_name": "qwen", "consistent": False, "parse_ok": False, "metadata": {"evidence_status": "MOCK_ONLY"}},
        ],
    )
    comparison = build_model_comparison(str(scores), str(tmp_path / "comparison"))
    sensitivity = build_sensitivity_suite(str(scores), str(tmp_path / "sensitivity"))
    assert comparison["significance_claims_made"] is False
    assert comparison["parse_failures_included"] is True
    assert sensitivity["bootstrap_never_certification"] is True
    assert sensitivity["non_evidence_blocked"] is True


def test_v4_paper_release_results_and_submission_helpers(tmp_path):
    gallery = tmp_path / "gallery.jsonl"
    _jsonl(gallery, [{"item_id": "i1", "license": "cc0", "original_image_path": "o.png", "edited_image_path": "e.png"}])
    figures = build_qualitative_figures(str(gallery), str(tmp_path / "figs"))
    assert figures["pixels_copied"] is False
    assert figures["fake_captions"] is False

    report_root = tmp_path / "reports"
    report_root.mkdir()
    (report_root / "report.md").write_text("MOCK_ONLY placeholder", encoding="utf-8")
    supp = generate_supplement(str(report_root), str(tmp_path / "supp.tex"))
    assert supp["non_evidence_refused"] is True

    release = tmp_path / "release"
    release.mkdir()
    (release / "commands.sh").write_text("python3 -m certvic.audit\n", encoding="utf-8")
    capsule = validate_capsule(str(release))
    assert capsule["commands_present"] is True
    assert capsule["path_leaks"] == []

    results = tmp_path / "results"
    results.mkdir()
    result_file = results / "summary.json"
    result_file.write_text('{"evidence_status":"REAL_EVIDENCE"}', encoding="utf-8")
    lock = freeze_results(str(results), str(tmp_path / "lock.json"))
    assert lock["git_required"] is False
    result_file.write_text('{"evidence_status":"REAL_EVIDENCE","changed":true}', encoding="utf-8")
    assert compare_lockfile(str(tmp_path / "lock.json"))["changed"] == ["summary.json"]

    plan = build_deadline_plan("2026-11-15")
    packet = build_internal_review_packet("paper", str(report_root), str(tmp_path / "packet"))
    assert plan["wall_clock_estimates_included"] is True
    assert packet["fake_results_added"] is False


def test_v4_troubleshooting_reviewer_quality_ablation_and_final_audit(tmp_path):
    diagnosis = diagnose_log("CUDA out of memory while loading model")
    assert diagnosis["external_llm_used"] is False
    assert diagnosis["destructive_advice"] is False

    ratings = tmp_path / "ratings.csv"
    with ratings.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_id", "reviewer_id", "single_factor_valid", "is_sentinel", "sentinel_pass"])
        writer.writeheader()
        writer.writerow({"item_id": "i1", "reviewer_id": "alice", "single_factor_valid": "yes", "is_sentinel": "true", "sentinel_pass": "true"})
        writer.writerow({"item_id": "i1", "reviewer_id": "bob", "single_factor_valid": "no", "is_sentinel": "false", "sentinel_pass": ""})
    quality = analyze_reviewer_quality(str(ratings), str(tmp_path / "quality"))
    assert quality["reviewers_anonymized"] is True
    assert quality["disagreements"] == ["i1"]

    ablation = build_ablation_plan(200, ["qwen2_5_vl_7b"])
    assert ablation["required_ablations"]
    assert ablation["free_compute_budget_respected"] is True

    final_audit = run_final_audit()
    assert final_audit["downloads_attempted"] is False
    assert final_audit["gpu_required"] is False


def test_v4_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
