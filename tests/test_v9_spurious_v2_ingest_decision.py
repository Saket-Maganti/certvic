from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl"
PROVIDERS = ["qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"]
MODEL_REPOS = {
    "qwen2_5_vl_7b": "Qwen/Qwen2.5-VL-7B-Instruct",
    "internvl_8b": "OpenGVLab/InternVL2-8B",
    "llava_onevision_7b": "llava-hf/llava-onevision-qwen2-7b-ov-hf",
}
MODEL_REVISIONS = {provider: f"{index + 1}" * 40 for index, provider in enumerate(PROVIDERS)}
CODE_BUNDLE = ROOT / "dist/certvic_kaggle_main200_bundle.zip"
CONTROL_BUNDLE = ROOT / "dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip"
MANIFEST_SCHEMA = "certvic.v11.spurious_v2.kaggle_output_manifest.v3"


def _task_rows() -> list[dict]:
    return [json.loads(line) for line in TASKS.read_text().splitlines() if line.strip()]


def _prediction_rows(provider: str) -> list[dict]:
    rows = []
    for index, task in enumerate(_task_rows()):
        run_id = f"v9_{provider}_spurious_v2_shard{index % 2}"
        for variant in ("original", "edited"):
            rows.append(
                {
                    "run_id": run_id,
                    "item_id": task["item_id"],
                    "provider_name": provider,
                    "provider_type": "open_local",
                    "model_name": provider,
                    "model_version": MODEL_REVISIONS[provider],
                    "image_variant": variant,
                    "prompt": task[f"question_{variant}"],
                    "raw_output": "yes",
                    "parsed_answer": "yes",
                    "parse_confidence": 1.0,
                    "parse_ok": True,
                    "latency_s": 0.01,
                    "timestamp_utc": "2026-07-11T00:00:00+00:00",
                    "metadata": {"evidence_status": "SYNTHETIC_TEST_FIXTURE"},
                }
            )
    return rows


def _jsonl_bytes(rows: list[dict]) -> bytes:
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode()


def _write_provider_zip(
    input_dir: Path,
    provider: str,
    rows: list[dict],
    *,
    manifest_updates: dict | None = None,
) -> Path:
    input_dir.mkdir(parents=True, exist_ok=True)
    pred_name = f"pred_{provider}_spurious_v2_merged.jsonl"
    manifest_name = f"runtime_manifest_{provider}_spurious_v2.json"
    pred_bytes = _jsonl_bytes(rows)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "provider": provider,
        "run_tag": "spurious_v2",
        "expected_items": len(_task_rows()),
        "expected_prediction_rows": 2 * len(_task_rows()),
        "merged_predictions": pred_name,
        "merged_predictions_sha256": hashlib.sha256(pred_bytes).hexdigest(),
        "task_file_sha256": hashlib.sha256(TASKS.read_bytes()).hexdigest(),
        "model_repo_id": MODEL_REPOS[provider],
        "model_revision": MODEL_REVISIONS[provider],
        "model_revision_marker_verified": True,
        "code_bundle_sha256": hashlib.sha256(CODE_BUNDLE.read_bytes()).hexdigest(),
        "control_bundle_sha256": hashlib.sha256(CONTROL_BUNDLE.read_bytes()).hexdigest(),
        "paper_evidence": False,
        "canonical_results_changed": False,
    }
    manifest.update(manifest_updates or {})
    path = input_dir / f"{provider}_spurious_v2_preds.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(pred_name, pred_bytes)
        zf.writestr(manifest_name, json.dumps(manifest, sort_keys=True))
    return path


def _write_all(
    input_dir: Path,
    *,
    rows_by_provider: dict[str, list[dict]] | None = None,
    manifest_updates: dict[str, dict] | None = None,
) -> None:
    for provider in PROVIDERS:
        _write_provider_zip(
            input_dir,
            provider,
            (rows_by_provider or {}).get(provider, _prediction_rows(provider)),
            manifest_updates=(manifest_updates or {}).get(provider),
        )


def _run_import(tmp_path: Path, input_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/import_v9_spurious_v2_outputs.py",
            "--input-dir",
            str(input_dir),
            "--out-dir",
            str(tmp_path / "ingest"),
            "--canonical-dir",
            str(tmp_path / "canonical"),
            "--report-dir",
            str(tmp_path / "reports"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _assert_invalid_without_canonical(tmp_path: Path, result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 3, result.stderr + result.stdout
    assert not (tmp_path / "canonical").exists()
    status = json.loads((tmp_path / "reports/spurious_v2_ingest_status.json").read_text())
    assert status["status"] == "BLOCKED_INVALID_PREDICTIONS"
    assert status["paper_evidence"] is False
    assert status["canonical_results_changed"] is False
    assert not (tmp_path / "reports/spurious_v2_specificity_results.json").exists()


def test_missing_output_mode_blocks_without_results(tmp_path):
    result = _run_import(tmp_path, tmp_path / "empty")
    assert result.returncode == 2
    status = json.loads((tmp_path / "reports/spurious_v2_ingest_status.json").read_text())
    assert status["status"] == "BLOCKED_MISSING_PREDICTIONS"
    assert set(status["missing_providers"]) == set(PROVIDERS)
    assert status["paper_evidence"] is False
    assert not (tmp_path / "canonical").exists()


def test_valid_archives_import_transactionally_and_idempotently(tmp_path):
    input_dir = tmp_path / "inputs"
    _write_all(input_dir)
    first = _run_import(tmp_path, input_dir)
    assert first.returncode == 0, first.stderr + first.stdout
    decision = json.loads((tmp_path / "reports/spurious_v2_specificity_results.json").read_text())
    assert decision["status"] == "DONE_REAL_IMPORTED_OUTPUTS"
    assert decision["paper_evidence"] is False
    assert decision["canonical_results_changed"] is True
    assert all(info["gate_pass"] for info in decision["providers"].values())
    assert all(info["n_prediction_rows"] == 60 for info in decision["providers"].values())
    canonical = {
        provider: tmp_path / "canonical" / f"pred_{provider}_spurious_v2_merged.jsonl"
        for provider in PROVIDERS
    }
    before = {provider: (path.read_bytes(), path.stat().st_mtime_ns) for provider, path in canonical.items()}

    second = _run_import(tmp_path, input_dir)
    assert second.returncode == 0, second.stderr + second.stdout
    decision = json.loads((tmp_path / "reports/spurious_v2_specificity_results.json").read_text())
    assert decision["canonical_results_changed"] is False
    assert all(
        info["canonical_action"] == "idempotent_existing_identical"
        for info in decision["providers"].values()
    )
    assert before == {
        provider: (path.read_bytes(), path.stat().st_mtime_ns) for provider, path in canonical.items()
    }


@pytest.mark.parametrize(
    "defect",
    [
        "missing_row",
        "duplicate_variant",
        "unexpected_item_id",
        "wrong_provider",
        "wrong_run_id",
        "wrong_variant",
        "parse_failure",
        "stored_parse_mismatch",
        "wrong_model_revision",
    ],
)
def test_prediction_row_defects_fail_closed_before_canonical_write(tmp_path, defect):
    provider = PROVIDERS[0]
    rows = _prediction_rows(provider)
    if defect == "missing_row":
        rows.pop()
    elif defect == "duplicate_variant":
        rows[-1] = dict(rows[0])
    elif defect == "unexpected_item_id":
        rows[0]["item_id"] = "not_in_the_frozen_task_manifest"
    elif defect == "wrong_provider":
        rows[0]["provider_name"] = PROVIDERS[1]
    elif defect == "wrong_run_id":
        rows[0]["run_id"] = f"v9_{provider}_wrong_tag_shard0"
    elif defect == "wrong_variant":
        rows[0]["image_variant"] = "control"
    elif defect == "parse_failure":
        rows[0].update(raw_output="", parsed_answer=None, parse_confidence=0.0, parse_ok=False)
    elif defect == "stored_parse_mismatch":
        rows[0].update(raw_output="no", parsed_answer="yes", parse_confidence=1.0, parse_ok=True)
    elif defect == "wrong_model_revision":
        rows[0]["model_version"] = "f" * 40
    _write_all(tmp_path / "inputs", rows_by_provider={provider: rows})
    _assert_invalid_without_canonical(tmp_path, _run_import(tmp_path, tmp_path / "inputs"))


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("schema", "certvic.legacy"),
        ("provider", "wrong_provider"),
        ("run_tag", "spurious"),
        ("expected_items", 29),
        ("expected_prediction_rows", 59),
        ("task_file_sha256", "0" * 64),
        ("merged_predictions_sha256", "f" * 64),
        ("paper_evidence", True),
        ("canonical_results_changed", True),
        ("model_repo_id", "wrong/repository"),
        ("model_revision", "not-a-commit"),
        ("model_revision_marker_verified", False),
        ("code_bundle_sha256", "a" * 64),
        ("control_bundle_sha256", "b" * 64),
    ],
)
def test_manifest_and_source_hash_defects_fail_closed(tmp_path, field, bad_value):
    provider = PROVIDERS[0]
    _write_all(
        tmp_path / "inputs",
        manifest_updates={provider: {field: bad_value}},
    )
    _assert_invalid_without_canonical(tmp_path, _run_import(tmp_path, tmp_path / "inputs"))


def test_canonical_conflict_never_overwrites_existing_evidence(tmp_path):
    input_dir = tmp_path / "inputs"
    _write_all(input_dir)
    assert _run_import(tmp_path, input_dir).returncode == 0
    canonical = tmp_path / "canonical/pred_qwen2_5_vl_7b_spurious_v2_merged.jsonl"
    before = canonical.read_bytes()

    changed = _prediction_rows(PROVIDERS[0])
    changed[0].update(raw_output="no", parsed_answer="no")
    _write_all(input_dir, rows_by_provider={PROVIDERS[0]: changed})
    result = _run_import(tmp_path, input_dir)
    assert result.returncode == 3
    assert "canonical conflict" in result.stdout
    assert canonical.read_bytes() == before


def test_ambiguous_direct_and_zip_sources_are_rejected(tmp_path):
    input_dir = tmp_path / "inputs"
    _write_all(input_dir)
    provider = PROVIDERS[0]
    (input_dir / f"pred_{provider}_spurious_v2_merged.jsonl").write_bytes(
        _jsonl_bytes(_prediction_rows(provider))
    )
    _assert_invalid_without_canonical(tmp_path, _run_import(tmp_path, input_dir))
