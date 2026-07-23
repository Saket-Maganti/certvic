"""Regression tests for the V8 post-newruns upgrade artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from certvic.v7.spurious_control_integration import check_readiness, integrate

ROOT = Path(__file__).resolve().parents[1]
V8 = ROOT / "data/results/main_real_200/v8_upgrade"
NEWRUNS = ROOT / "kaggleoutputs/newruns"
PROVIDERS = {"qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"}
RUNS = {"spurious", "perception_scaled", "polarity", "mechanism"}
RUN_CONFIG = {
    "spurious": (188, "pred_{provider}_spurious_merged.jsonl"),
    "perception_scaled": (738, "pred_{provider}_perception_scaled_merged.jsonl"),
    "polarity": (728, "pred_{provider}_polarity.jsonl"),
    "mechanism": (364, "pred_{provider}_mechanism.jsonl"),
}
HISTORICAL_REASON = (
    "requires genuine historical kaggleoutputs/newruns bytes; not present in this checkout"
)


def _fixture_rows(provider: str, run_tag: str, count: int) -> list[dict]:
    return [
        {
            "prediction_id": f"{provider}::{run_tag}::{index}",
            "item_id": f"{run_tag}-{index}",
            "image_variant": "synthetic",
            "provider_name": provider,
            "parse_ok": True,
            "parsed_answer": "no",
            "synthetic_fixture": True,
            "paper_evidence": False,
        }
        for index in range(count)
    ]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def _build_fixture_newruns(root: Path) -> None:
    root.mkdir(parents=True)
    for provider in sorted(PROVIDERS):
        for run_tag, (count, template) in RUN_CONFIG.items():
            filename = template.format(provider=provider)
            rows = _fixture_rows(provider, run_tag, count)
            if provider == "qwen2_5_vl_7b" and run_tag == "polarity":
                archive_path = root / f"{provider}_{run_tag}_preds.zip"
                payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
                with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr(filename, payload)
            else:
                _write_jsonl(root / filename, rows)


def _run_fixture_builder(tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    newruns = tmp_path / "newruns"
    results = tmp_path / "results"
    output = tmp_path / "v8"
    _build_fixture_newruns(newruns)
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_v8_upgrade.py",
            "--newruns-root",
            str(newruns),
            "--results-root",
            str(results),
            "--output-root",
            str(output),
            "--normalize-only",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc, results, output


def _tree_hashes(*roots: Path) -> dict[str, str]:
    return {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for root in roots
        for path in root.rglob("*")
        if path.is_file()
    }


def _genuine_historical_inputs_present() -> bool:
    if not NEWRUNS.is_dir():
        return False
    manifest_path = V8 / "canonical_prediction_manifest.json"
    if not manifest_path.is_file():
        return False
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest.get("entries", {}).values():
        expected = entry.get("sha256")
        matching_attempts = [
            attempt
            for attempt in entry.get("attempts", [])
            if attempt.get("source_kind") == entry.get("source_kind")
        ]
        if not expected or not matching_attempts:
            return False
        source = matching_attempts[0]["source"]
        if "::" in source:
            archive_name, member = source.split("::", 1)
            archive_path = ROOT / archive_name
            if not archive_path.is_file():
                return False
            with zipfile.ZipFile(archive_path) as archive:
                payload = archive.read(member)
            observed = hashlib.sha256(payload).hexdigest()
        else:
            source_path = ROOT / source
            if not source_path.is_file():
                return False
            observed = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if observed != expected:
            return False
    return True


HAS_GENUINE_HISTORICAL_INPUTS = _genuine_historical_inputs_present()


def test_build_v8_upgrade_is_idempotent_result_nonproducing_and_live_safe(tmp_path: Path):
    live_before = _tree_hashes(
        V8,
        ROOT / "data/results/main_real_200/kaggle_spurious",
        ROOT / "data/results/main_real_200/kaggle_perception_scaled",
        ROOT / "data/results/main_real_200/kaggle_polarity",
        ROOT / "data/results/main_real_200/kaggle_mechanism",
    )
    proc, results, output = _run_fixture_builder(tmp_path)
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    assert summary["status"] == "complete"
    assert summary["produced_model_results_by_this_script"] is False
    assert summary["paper_evidence"] is False

    manifest_path = output / "canonical_prediction_manifest.json"
    first = manifest_path.read_bytes()
    rerun = subprocess.run(proc.args, cwd=ROOT, text=True, capture_output=True, check=False)
    assert rerun.returncode == 0, rerun.stderr
    assert manifest_path.read_bytes() == first
    manifest = json.loads(first)
    assert set(manifest["entries"]) == {f"{p}__{r}" for p in PROVIDERS for r in RUNS}
    assert all(entry["validation"]["synthetic_fixture"] for entry in manifest["entries"].values())
    assert all(entry["validation"]["paper_evidence"] is False for entry in manifest["entries"].values())
    assert manifest["entries"]["qwen2_5_vl_7b__polarity"]["source_kind"] == "zip_member"
    assert len(list(results.rglob("pred_*.jsonl"))) == 12
    assert _tree_hashes(
        V8,
        ROOT / "data/results/main_real_200/kaggle_spurious",
        ROOT / "data/results/main_real_200/kaggle_perception_scaled",
        ROOT / "data/results/main_real_200/kaggle_polarity",
        ROOT / "data/results/main_real_200/kaggle_mechanism",
    ) == live_before


@pytest.mark.parametrize("fault", ["duplicate", "row_count"])
def test_v8_fixture_normalization_fails_closed_on_invalid_rows(
    tmp_path: Path, fault: str
) -> None:
    newruns = tmp_path / "newruns"
    results = tmp_path / "results"
    output = tmp_path / "v8"
    _build_fixture_newruns(newruns)
    target = newruns / "pred_internvl_8b_spurious_merged.jsonl"
    rows = [json.loads(line) for line in target.read_text().splitlines()]
    if fault == "duplicate":
        rows[1]["item_id"] = rows[0]["item_id"]
        rows[1]["image_variant"] = rows[0]["image_variant"]
    else:
        rows.pop()
    _write_jsonl(target, rows)
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_v8_upgrade.py",
            "--newruns-root",
            str(newruns),
            "--results-root",
            str(results),
            "--output-root",
            str(output),
            "--normalize-only",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 2
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    assert summary["status"] == "blocked"
    manifest = json.loads((output / "canonical_prediction_manifest.json").read_text())
    entry = manifest["entries"]["internvl_8b__spurious"]
    assert entry["status"] == "blocked"
    assert entry["attempts"][0]["row_count_ok"] is (fault != "row_count")
    assert entry["attempts"][0]["n_duplicate_ids"] == (1 if fault == "duplicate" else 0)
    assert not (results / "kaggle_spurious/pred_internvl_8b_spurious_merged.jsonl").exists()


def test_v8_missing_external_predictions_are_truthfully_blocked(tmp_path: Path) -> None:
    newruns = tmp_path / "absent-newruns"
    results = tmp_path / "results"
    output = tmp_path / "v8"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_v8_upgrade.py",
            "--newruns-root",
            str(newruns),
            "--results-root",
            str(results),
            "--output-root",
            str(output),
            "--normalize-only",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 2
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    assert summary["status"] == "blocked"
    assert summary["paper_evidence"] is False
    assert summary["produced_model_results_by_this_script"] is False
    assert len(summary["missing_provider_run_files"]) == 12
    assert all(item["accepted_sources"] for item in summary["missing_provider_run_files"])
    assert not list(results.rglob("pred_*.jsonl"))


@pytest.mark.skipif(not HAS_GENUINE_HISTORICAL_INPUTS, reason=HISTORICAL_REASON)
def test_canonical_prediction_manifest_has_all_expected_real_outputs():
    manifest = json.loads((V8 / "canonical_prediction_manifest.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["paper_evidence"] is False
    assert manifest["produced_model_results_by_this_script"] is False
    assert set(manifest["entries"]) == {f"{p}__{r}" for p in PROVIDERS for r in RUNS}
    for entry in manifest["entries"].values():
        assert entry["status"] == "complete"
        assert entry["validation"]["row_count_ok"] is True
        assert entry["validation"]["provider_ok"] is True
        assert entry["validation"]["n_duplicate_ids"] == 0
    qwen_pol = manifest["entries"]["qwen2_5_vl_7b__polarity"]
    assert qwen_pol["source_kind"] == "zip_member"
    assert qwen_pol["validation"]["n_rows"] == 728


@pytest.mark.skipif(not HAS_GENUINE_HISTORICAL_INPUTS, reason=HISTORICAL_REASON)
def test_spurious_gate_is_answered_but_failed_for_qwen_only():
    report = json.loads((V8 / "spurious_specificity_control_report.json").read_text())
    assert report["status"] == "blocked_failed_gate"
    assert report["paper_evidence"] is False
    assert report["all_provider_gate_pass"] is False
    assert report["providers"]["qwen2_5_vl_7b"]["spurious_flip_rate"] == 0.1277
    assert report["providers"]["qwen2_5_vl_7b"]["gate_pass"] is False
    assert report["providers"]["internvl_8b"]["gate_pass"] is True
    assert report["providers"]["llava_onevision_7b"]["gate_pass"] is True
    detect = report["detectability_quality"]["json_reports"][0]["data"]
    assert detect["n_items"] == 94
    assert detect["n_skipped"] == 0
    assert detect["artifact_risk"] is False


@pytest.mark.skipif(not HAS_GENUINE_HISTORICAL_INPUTS, reason=HISTORICAL_REASON)
def test_v7_spurious_integration_uses_real_predictions_without_promoting_evidence():
    readiness = check_readiness(ROOT)
    assert readiness["ready"] is False
    assert readiness["present"]["quality_detectability_report"] is True
    assert all(readiness["present"]["predictions_per_provider"].values())
    assert readiness["present"]["human_visual_review_complete"] is False
    status = integrate(ROOT)
    assert status["status"] == "blocked"
    assert status["specificity_status"] == "blocked"
    assert status["paper_evidence"] is False
    assert any("human visual review" in item for item in status["missing"])


@pytest.mark.skipif(not HAS_GENUINE_HISTORICAL_INPUTS, reason=HISTORICAL_REASON)
def test_scaled_polarity_and_mechanism_reports_are_complete_but_non_evidence():
    scaled = json.loads((V8 / "scaled_perception_control_report.json").read_text())
    polarity = json.loads((V8 / "polarity_ablation_report.json").read_text())
    mechanism = json.loads((V8 / "mechanism_probe_report.json").read_text())
    assert scaled["status"] == "complete"
    assert all(scaled["providers"][p]["n"] == 369 for p in PROVIDERS)
    assert polarity["status"] == "complete"
    assert polarity["schema"] == "certvic.v8.polarity_ablation_report.v2"
    assert polarity["task_manifest_audit"]["valid"] is True
    assert all(polarity["providers"][p]["n_rows"] == 728 for p in PROVIDERS)
    assert all(polarity["providers"][p]["gold_source"] == "current_task_manifest" for p in PROVIDERS)
    assert all(polarity["providers"][p]["n_missing_task_gold"] == 0 for p in PROVIDERS)
    assert all(polarity["providers"][p]["raw_metadata_gold_mismatches"] > 0 for p in PROVIDERS)
    assert polarity["providers"]["qwen2_5_vl_7b"]["families"]["positive"]["row_accuracy"] == 0.6154
    assert polarity["providers"]["qwen2_5_vl_7b"]["families"]["negative"]["row_accuracy"] == 0.544
    assert mechanism["status"] == "complete"
    assert all(mechanism["providers"][p]["n_rows"] == 364 for p in PROVIDERS)
    assert "original_vs_edited" in mechanism["spec_blocked_families_excluded"]
    assert not any(x["paper_evidence"] for x in (scaled, polarity, mechanism))


def test_v8_human_exports_are_blank_and_portable():
    for path in [
        ROOT / "data/annotations/v8_residual_cue_audit/residual_cue_audit_sheet.csv",
        ROOT / "data/annotations/v8_second_rater_iaa/second_rater_review_sheet.csv",
    ]:
        text = path.read_text()
        assert "/Users/" not in text
        rows = list(csv.DictReader(text.splitlines()))
        assert rows
        human_cols = [c for c in rows[0] if c in {"notes", "reviewer_id", "keep_for_eval", "residual_target_visible"}]
        assert human_cols
        assert all(row[col] == "" for row in rows for col in human_cols)


def test_v8_final_policy_and_task_ledger_keep_scale_blocked():
    handoff = json.loads((V8 / "v8_final_handoff.json").read_text())
    scorecard = json.loads((V8 / "CVPR_READINESS_SCORECARD_V8.json").read_text())
    ledger = json.loads((V8 / "v8_task_ledger.json").read_text())
    assert handoff["produced_model_results_by_this_script"] is False
    assert handoff["ingested_existing_kaggle_predictions"] is True
    assert handoff["spurious_control_ready"] is False
    assert scorecard["ready"] is False
    assert "spurious specificity gate failed" in scorecard["blocking_conditions"]
    assert {t["id"] for t in ledger["tasks"]} == {f"V8_{i:02d}" for i in range(23)}
    assert all(t["paper_evidence"] is False for t in ledger["tasks"])
