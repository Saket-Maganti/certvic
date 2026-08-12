from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from certvic.cvpr.smoke_input_builder import build_smoke_bundle
from certvic.cvpr.task_bundle import verify_bundle
from local_operator.cvpr2027_c12_design import allocation_power
from local_operator.cvpr2027_c12_matching import (
    match_controls,
    prospective_detectability,
    reject_outcome_contamination,
)
from local_operator.pre_smoke_operator import CANONICAL_PROMPT_TEMPLATE_HASH


ROOT = Path(__file__).resolve().parents[1]


def _candidate(identity: str, arm: str, offset: float) -> dict[str, object]:
    row: dict[str, object] = {
        "item_id": identity,
        "source_image_id": identity,
        "endpoint_arm": arm,
        "category": "person",
        "expected_answer_polarity": "yes",
        "target_size_stratum": "medium",
        "target_position_stratum": "center",
        "perturbation_family": "patch",
    }
    features = [
        "difference_area_fraction",
        "mean_absolute_pixel_difference",
        "ssim",
        "psnr",
        "histogram_distance",
        "luminance_change",
        "contrast_change",
        "edge_density_change",
        "spatial_distance_to_target",
        "spatial_distance_to_protected_region",
        "salience",
    ]
    row.update({field: offset + index / 100 for index, field in enumerate(features)})
    return row


def test_c12_amendment_improves_declared_all_three_power_without_threshold_change() -> None:
    old = allocation_power(120, 120, 0.70, 0.03)
    new = allocation_power(120, 240, 0.70, 0.03)
    assert old["critical_semantic_update_successes"] == 74
    assert old["critical_maximum_irrelevant_flips"] == 4
    assert new["critical_semantic_update_successes"] == 74
    assert new["critical_maximum_irrelevant_flips"] == 13
    assert old["claim_regime_a_all_three_six_gate_power"] == pytest.approx(0.3335280212)
    assert new["claim_regime_a_all_three_six_gate_power"] == pytest.approx(0.9010361416)
    assert new["family_alpha"] == old["family_alpha"] == 0.05


def test_protocol_v3_is_an_amendment_not_a_rewrite() -> None:
    old = ROOT / "configs/studies/specificity_confirmatory_cvpr.yaml"
    new = ROOT / "configs/studies/specificity_confirmatory_cvpr_v3.yaml"
    assert old.is_file() and new.is_file()
    text = new.read_text(encoding="utf-8")
    assert "amends_verbatim_authority: configs/studies/specificity_confirmatory_cvpr.yaml" in text
    assert "prospective_provider_outcomes_observed_at_amendment: false" in text
    assert "relevant_intervention: 120, irrelevant_control: 240" in text


def test_matching_is_outcome_blind_and_exact_stratum() -> None:
    rows = [
        _candidate("r1", "relevant_intervention", 0.10),
        _candidate("r2", "relevant_intervention", 0.20),
        *[_candidate(f"c{i}", "irrelevant_control", 0.08 + i / 100) for i in range(6)],
    ]
    matched = match_controls(rows, controls_per_relevant=2)
    assert len(matched["selected"]) == 6
    assert len(matched["trace"]) == 4
    assert matched["provider_outputs_used"] is False
    contaminated = [dict(rows[0], provider="qwen2_5_vl_7b"), *rows[1:]]
    with pytest.raises(ValueError, match="provider outcomes"):
        reject_outcome_contamination(contaminated)


def test_detectability_uses_group_safe_cv_and_fails_distinguishable_arms() -> None:
    rows = [
        _candidate(f"r{i}", "relevant_intervention", 0.8 + i / 1000)
        for i in range(15)
    ] + [
        _candidate(f"c{i}", "irrelevant_control", 0.1 + i / 1000)
        for i in range(30)
    ]
    result = prospective_detectability(
        rows, repeats=2, folds=3, bootstrap_samples=30, permutations=30
    )
    assert result["status"] == "DETECTABILITY_GATE_FAIL"
    assert result["execution_authorization"] == "MODEL_EXECUTION_NOT_AUTHORIZED"
    assert result["provider_outputs_used"] is False
    assert all(
        not fold["source_group_overlap"]
        for model in result["classifiers"].values()
        for fold in model["folds"]
    )


def test_real_smoke_builder_emits_runtime_compatible_task_bundle(tmp_path: Path) -> None:
    rows = []
    for index in range(2):
        original = tmp_path / f"real-{index}-original.png"
        edited = tmp_path / f"real-{index}-edited.png"
        Image.new("RGB", (80, 80), (20 + index, 30, 40)).save(original)
        Image.new("RGB", (80, 80), (60 + index, 70, 80)).save(edited)
        rows.append({
            "item_id": f"licensed-{index}",
            "original_image_path": str(original),
            "edited_image_path": str(edited),
            "license_eligible": True,
            "license_id": f"USER-OWNED-{index}",
            "prompt_template_hash": CANONICAL_PROMPT_TEMPLATE_HASH,
            "parser_version": "certvic.parse.v2",
            "run_contract_hash": "c" * 64,
            "synthetic_fixture": False,
            "paper_evidence": False,
        })
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    archive = tmp_path / "smoke.zip"
    build_smoke_bundle(tasks, output=archive)
    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(archive) as handle:
        handle.extractall(extracted)
    verified = verify_bundle(
        extracted / "task_bundle", extracted / "task_bundle/task_bundle_manifest.json"
    )
    assert verified["status"] == "TASK_BUNDLE_VALID"
    assert verified["tasks"] == 2


def test_claim_registry_separates_historical_optional_and_primary_evidence() -> None:
    registry = json.loads(
        (ROOT / "reports/cvpr2027_c12/evidence/CLAIM_REGISTRY_V2.json").read_text()
    )
    claims = {row["claim_id"]: row for row in registry["claims"]}
    assert claims["prospective_joint_certificate"]["status"] == "BLOCKED"
    assert claims["secondary_model_expansion"]["required_evidence_class"] == (
        "SECONDARY_MODEL_EXPANSION"
    )
    assert registry["historical_can_satisfy_prospective"] is False
    assert registry["optional_models_enter_primary_family"] is False


def test_main500_cannot_be_authorized_by_manual_go_text() -> None:
    value = json.loads(
        (ROOT / "reports/cvpr2027_c12/main/MAIN500_READINESS.json").read_text()
    )
    assert value["status"] == "CONDITIONAL_NOT_AUTHORIZED"
    assert value["manual_go_text_bypass_allowed"] is False
    assert value["execution_allowed"] is False


def test_all_nine_primary_analysis_golden_cases_are_fail_closed() -> None:
    value = json.loads(
        (ROOT / "reports/cvpr2027_c12/analysis/ANALYSIS_GOLDEN_FIXTURES.json").read_text()
    )
    cases = {row["fixture"]: row for row in value["fixtures"]}
    assert set(cases) == {
        "all_pass",
        "all_fail",
        "one_missing",
        "one_duplicate",
        "parser_failures",
        "boundary_critical_count",
        "one_provider_missing",
        "mixed_task_bundle",
        "wrong_permission",
    }
    assert cases["all_pass"]["result"]["joint_certificate"] is True
    assert cases["all_fail"]["result"]["joint_certificate"] is False
    assert cases["one_missing"]["result"]["joint_certificate"] is False
    assert cases["parser_failures"]["result"]["joint_certificate"] is False
    boundary = cases["boundary_critical_count"]["result"]
    assert boundary["responsiveness_gate"] is True
    assert boundary["specificity_gate"] is True
    for name in (
        "one_duplicate",
        "one_provider_missing",
        "mixed_task_bundle",
        "wrong_permission",
    ):
        assert cases[name]["expected_disposition"].startswith("REJECT")
