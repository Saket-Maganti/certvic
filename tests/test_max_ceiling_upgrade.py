from __future__ import annotations

import csv
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from certvic.cvpr.artifact_registry import add_artifact, verify_registry
from certvic.cvpr.doctor import diagnose
from certvic.cvpr.kaggle_config import generate_config, write_config
from certvic.cvpr.next_action import execute_local_safe, next_action
from certvic.cvpr.notebook_runner import execute_synthetic_suite
from certvic.cvpr.paper_evidence_compiler import compile_evidence
from certvic.cvpr.reproducibility_capsule import REQUIRED_ROLES, create_capsule, verify_capsule
from certvic.cvpr.review_ops import qualification_is_current, reviewer_progress, verify_blind_ids
from certvic.cvpr.run_graph import graph_status, load_graph
from certvic.cvpr.runtime_planner import plan_runtime
from certvic.cvpr.statistics import hardened_specificity_analysis, mcnemar_holm_matrix
from certvic.data.license_registry import load_registry, validate_tasks


ROOT = Path(__file__).resolve().parents[1]


def test_doctor_and_next_action_preserve_external_boundary() -> None:
    report = diagnose(ROOT)
    assert report["local_ready"] is True
    environment = ROOT / "data/runtime/00A_environment.json"
    snapshots = (
        ROOT / "data/runtime/00B_qwen2_5_vl_7b_snapshot.json",
        ROOT / "data/runtime/00B_internvl_8b_snapshot.json",
        ROOT / "data/runtime/00B_llava_onevision_7b_snapshot.json",
    )
    if not environment.is_file():
        expected_state = "READY_FOR_00A"
    elif not all(snapshot.is_file() for snapshot in snapshots):
        expected_state = "READY_FOR_00B"
    else:
        expected_state = "READY_FOR_00C2"
    assert report["state"] == expected_state
    assert report["paper_evidence"] is False
    assert all(
        row["error_code"] != "DOCTOR_REPLACEMENT_SOURCE_UNAVAILABLE"
        for row in report["blockers"]
    )
    assert report["checks"]["active_checkout_authority"]["passed"] is True
    assert report["checks"]["protocol_authority"]["passed"] is True
    action = next_action(ROOT)
    refused = execute_local_safe(action, ROOT)
    assert refused["execution_refused"] is True


def test_run_graph_has_canonical_28_node_order() -> None:
    graph = load_graph(ROOT / "configs/execution/certvic_run_graph.yaml")
    assert len(graph["nodes"]) == 28
    assert graph["nodes"][0]["id"] == "verify_checkout"
    assert graph["nodes"][-1]["id"] == "final_release"
    status = graph_status(graph, ROOT)
    assert status["next"] in {
        "doctor",
        "provision_wheelhouse",
        "run_00a",
        "provision_snapshots",
        "run_00b",
    }


def test_registry_and_complete_capsule_verify_exact_bytes(tmp_path) -> None:
    registry_path = tmp_path / "registry.json"
    bindings = {}
    for role in REQUIRED_ROLES:
        artifact = tmp_path / f"{role}.json"
        artifact.write_text(json.dumps({"role": role}) + "\n", encoding="utf-8")
        row = add_artifact(
            registry_path,
            artifact,
            root=tmp_path,
            role=role,
            schema=f"test.{role}.v1",
            study="test",
            evidence_class="SYNTHETIC_TEST_FIXTURE",
        )
        bindings[role] = row["artifact_id"]
    assert verify_registry(registry_path, root=tmp_path)["passed"] is True
    capsule_path = tmp_path / "capsule.json"
    capsule = create_capsule(
        registry_path, capsule_path, study="test", bindings=bindings
    )
    assert capsule["status"] == "COMPLETE"
    assert verify_capsule(capsule_path, registry_path, root=tmp_path)["passed"] is True
    (tmp_path / "code.json").write_text("tampered\n", encoding="utf-8")
    assert verify_capsule(capsule_path, registry_path, root=tmp_path)["passed"] is False


def test_kaggle_config_is_portable_and_rejects_unknown_provider(tmp_path) -> None:
    payload = generate_config("00C2", provider="qwen2_5_vl_7b", root=ROOT)
    assert payload["expected_output_filename"].endswith(".zip")
    paths = write_config(payload, tmp_path)
    rendered = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert str(Path.home()) not in rendered
    assert "CERTVIC_CONFIG" in rendered
    with pytest.raises(ValueError, match="requires --provider"):
        generate_config("00C2", provider="unknown", root=ROOT)


@pytest.mark.skipif(
    importlib.util.find_spec("nbclient") is None or importlib.util.find_spec("nbformat") is None,
    reason="optional notebook execution dependencies are not installed",
)
def test_actual_synthetic_notebook_matrix_executes_with_nbclient(tmp_path) -> None:
    report = execute_synthetic_suite(tmp_path)
    assert report["status"] == "PASS"
    assert len(report["routes"]) == 8
    assert all(row["status"] == "PASS" for row in report["routes"])


def test_runtime_planner_recalibrates_only_from_non_evidence_smoke(tmp_path) -> None:
    safe = tmp_path / "safe.json"
    safe.write_text(json.dumps({
        "paper_evidence": False,
        "runtime_class": "REAL_MODEL_SMOKE",
        "provider": "qwen2_5_vl_7b",
        "elapsed_seconds": 20,
        "images_processed": 2,
    }), encoding="utf-8")
    unsafe = tmp_path / "unsafe.json"
    unsafe.write_text(json.dumps({
        "paper_evidence": True,
        "runtime_class": "SCIENTIFIC",
        "provider": "qwen2_5_vl_7b",
        "elapsed_seconds": 1,
        "images_processed": 100,
    }), encoding="utf-8")
    report = plan_runtime(
        provider="qwen2_5_vl_7b", items=240, runtime_manifests=[safe, unsafe]
    )
    assert report["seconds_per_image"] == 10
    assert report["estimate_status"] == "RECALIBRATED_FROM_NON_EVIDENCE_SMOKE"
    assert str(unsafe) in report["rejected_calibration_manifests"]


def test_license_registry_fails_closed_for_unverified_ade20k() -> None:
    registry = load_registry(ROOT / "configs/data/source_license_registry.yaml")
    synthetic = [{
        "item_id": "s1", "source_dataset": "CERTVIC_SYNTHETIC_SMOKE",
        "source_split": "synthetic", "license_eligible": True,
    }]
    assert validate_tasks(synthetic, registry)["passed"] is True
    ade = [{
        "item_id": "a1", "source_dataset": "ADE20K", "source_split": "validation",
        "license_eligible": True,
    }]
    result = validate_tasks(ade, registry)
    assert result["passed"] is False
    assert result["errors"][0]["error_code"] == "LICENSE_SOURCE_UNVERIFIED"


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_review_progress_blinding_and_expiry(tmp_path) -> None:
    template = tmp_path / "template.csv"
    complete = tmp_path / "complete.csv"
    key = tmp_path / "key.csv"
    base = [
        {"blind_pair_id": "B1", "retain": ""},
        {"blind_pair_id": "B2", "retain": ""},
    ]
    _write_csv(template, base)
    _write_csv(complete, [
        {"blind_pair_id": "B1", "retain": "yes"},
        {"blind_pair_id": "B2", "retain": "no"},
    ])
    _write_csv(key, [
        {"blind_pair_id": "B1", "item_id": "I1"},
        {"blind_pair_id": "B2", "item_id": "I2"},
    ])
    assert reviewer_progress(template, complete, ("retain",))["passed"] is True
    assert verify_blind_ids(key, [complete])["passed"] is True
    current = {"expires_at_utc": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}
    expired = {"expires_at_utc": "2000-01-01T00:00:00+00:00"}
    assert qualification_is_current(current) is True
    assert qualification_is_current(expired) is False


def test_hardened_statistics_match_tiny_hand_fixture() -> None:
    rows = [
        {"item_id": "1", "flip": False, "valid": True, "provider": "p", "family": "a", "category": "x", "stratum": "s"},
        {"item_id": "2", "flip": True, "valid": True, "provider": "p", "family": "a", "category": "x", "stratum": "s"},
        {"item_id": "3", "flip": None, "valid": False, "provider": "p", "family": "b", "category": "y", "stratum": "t", "exclusion_reason": "missing"},
    ]
    result = hardened_specificity_analysis(rows, alpha=0.05, family_size=1)
    assert result["raw_primary"]["flips"] == 2
    assert result["raw_primary"]["denominator"] == 3
    assert result["validity_filtered"]["filtered_flips"] == 1
    assert result["validity_filtered"]["denominator"] == 2
    matrix = mcnemar_holm_matrix({"a": {"1": True, "2": False}, "b": {"1": False, "2": False}})
    assert matrix["pairs"][0]["left_flip_right_no_flip"] == 1
    assert matrix["pairs"][0]["exact_p"] == 1.0


def test_paper_compiler_refuses_synthetic_and_accepts_hash_verified_real(tmp_path) -> None:
    registry_path = tmp_path / "registry.json"
    analysis = tmp_path / "analysis.json"
    analysis.write_text(json.dumps({"paper_evidence": False, "synthetic": True}) + "\n", encoding="utf-8")
    add_artifact(
        registry_path, analysis, root=tmp_path, role="analysis", schema="test.analysis.v1",
        study="test", evidence_class="SYNTHETIC_TEST_FIXTURE",
    )
    blocked = compile_evidence(registry_path, tmp_path / "blocked", root=tmp_path)
    assert blocked["status"] == "PAPER_EVIDENCE_BLOCKED"

    real_registry = tmp_path / "real_registry.json"
    real_analysis = tmp_path / "real_analysis.json"
    review = tmp_path / "review.json"
    real_analysis.write_text(json.dumps({"paper_evidence": True, "status": "PASS"}) + "\n", encoding="utf-8")
    review.write_text(json.dumps({"paper_evidence": True, "status": "FINAL_INCLUSION_VALIDATED"}) + "\n", encoding="utf-8")
    add_artifact(
        real_registry, review, root=tmp_path, role="human_review", schema="test.review.v1",
        study="test", evidence_class="REAL_OBSERVED_EVIDENCE",
    )
    add_artifact(
        real_registry, real_analysis, root=tmp_path, role="analysis", schema="test.analysis.v1",
        study="test", evidence_class="DERIVED_FROM_REAL_EVIDENCE",
    )
    ready = compile_evidence(real_registry, tmp_path / "ready", root=tmp_path)
    assert ready["status"] == "PAPER_EVIDENCE_READY"
    assert ready["paper_evidence"] is True
