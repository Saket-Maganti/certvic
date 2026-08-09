from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import beta

from local_operator.cvpr2027_candidate_selection import run as run_selection
from local_operator.cvpr2027_common import REPO, resolve_repository_path
from local_operator.cvpr2027_certificate import compute_certificate, coordinate_region
from local_operator.cvpr2027_image_audit import _bbox, _bbox_distance, _bbox_overlap, _ssim_global
from local_operator.cvpr2027_infrastructure import claim_registry, gpu_planning
from local_operator.cvpr2027_leakage_audit import hamming
from local_operator.cvpr2027_statistics import (
    GATE_ALPHA,
    RESPONSIVENESS,
    SPECIFICITY,
    adversarial_ordering_stress,
    certification_probability,
    cp_lower,
    cp_upper,
    critical_count,
    familywise_simulation,
)
from local_operator.human_review_status import (
    FORBIDDEN_BLIND_FIELDS,
    JUDGMENT_FIELDS,
    agreement_report,
    initialize_infrastructure,
)


def test_exact_one_sided_clopper_pearson_matches_scipy() -> None:
    for n in [1, 7, 30, 120]:
        for successes in range(n + 1):
            expected_lower = 0.0 if successes == 0 else beta.ppf(GATE_ALPHA, successes, n - successes + 1)
            expected_upper = 1.0 if successes == n else beta.ppf(1 - GATE_ALPHA, successes + 1, n - successes)
            assert float(cp_lower(successes, n)) == pytest.approx(expected_lower, abs=1e-14)
            assert float(cp_upper(successes, n)) == pytest.approx(expected_upper, abs=1e-14)


def test_exact_bounds_and_power_are_monotone() -> None:
    for n in [20, 60, 120, 240]:
        lowers = [float(cp_lower(value, n)) for value in range(n + 1)]
        uppers = [float(cp_upper(value, n)) for value in range(n + 1)]
        assert all(left <= right for left, right in zip(lowers, lowers[1:]))
        assert all(left <= right for left, right in zip(uppers, uppers[1:]))
    response_power = [certification_probability(120, rate, RESPONSIVENESS) for rate in np.linspace(0, 1, 11)]
    specificity_power = [certification_probability(120, rate, SPECIFICITY) for rate in np.linspace(0, 1, 11)]
    assert response_power == sorted(response_power)
    assert specificity_power == sorted(specificity_power, reverse=True)


def test_frozen_n120_critical_counts() -> None:
    assert critical_count(120, RESPONSIVENESS) == 74
    assert critical_count(120, SPECIFICITY) == 4
    assert float(cp_lower(73, 120)) <= 0.5 < float(cp_lower(74, 120))
    assert float(cp_upper(4, 120)) <= 0.1 < float(cp_upper(5, 120))


def test_familywise_simulation_is_seed_reproducible() -> None:
    first = familywise_simulation(2000)
    second = familywise_simulation(2000)
    assert first == second
    null = next(row for row in first if row["scenario"] == "global_null_boundary")
    assert 0 <= null["familywise_false_certification_rate"] <= 1


def test_adversarial_streams_preserve_counts_and_support() -> None:
    rows = adversarial_ordering_stress()
    assert len(rows) == 15
    assert all(row["bounds_within_support"] for row in rows)
    assert all(row["final_mean"] == pytest.approx(row["successes"] / row["n"]) for row in rows)


def test_certificate_gates_evidence_separately() -> None:
    kwargs = {
        "model": "fixture",
        "relevant_outcomes": [True] * 74 + [False] * 46,
        "irrelevant_flip_outcomes": [True] * 4 + [False] * 116,
        "evidence_class": "PROSPECTIVE_CONFIRMATORY",
        "artifact_hashes": {"tasks": "a" * 64},
    }
    diagnostic = compute_certificate(**kwargs)
    assert diagnostic["statistical_joint_gate"] is True
    assert diagnostic["joint_certificate"] is False
    eligible = compute_certificate(**kwargs, genuine_human_review=True, prospective=True)
    assert eligible["joint_certificate"] is True
    missing = compute_certificate(
        **kwargs, genuine_human_review=True, prospective=True, missing_count=1
    )
    assert missing["statistical_joint_gate"] is True
    assert missing["joint_certificate"] is False


@pytest.mark.parametrize(
    ("response", "spurious", "region"),
    [
        (0.51, 0.10, "RESPONSIVE_AND_SPECIFIC"),
        (0.51, 0.11, "RESPONSIVE_BUT_SPURIOUS"),
        (0.50, 0.10, "INERT_BUT_SPECIFIC"),
        (0.50, 0.11, "INERT_AND_SPURIOUS"),
    ],
)
def test_coordinate_boundary_semantics(response: float, spurious: float, region: str) -> None:
    assert coordinate_region(response, spurious) == region


def test_candidate_selection_rejects_model_outcome_fields(tmp_path: Path) -> None:
    source = tmp_path / "candidate.jsonl"
    source.write_text(json.dumps({"item_id": "x", "provider": "leak"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="provider outcomes"):
        run_selection(tmp_path / "out", source_manifest=source)


def test_old_absolute_data_paths_rebind_to_active_checkout() -> None:
    target = REPO / "data/results/main_real_200/pilot_eval_tasks_reviewed_v2.jsonl"
    stale = Path("/Users/old-account/old-checkout/data/results/main_real_200/pilot_eval_tasks_reviewed_v2.jsonl")
    assert resolve_repository_path(stale) == target.resolve()


def test_human_packet_template_is_blind_and_agreement_is_exact(tmp_path: Path) -> None:
    paths = initialize_infrastructure(tmp_path)
    template_path = next(path for path in paths if path.name == "review_assignment_template.csv")
    with template_path.open(encoding="utf-8", newline="") as handle:
        fields = set(csv.DictReader(handle).fieldnames or [])
    assert not fields & FORBIDDEN_BLIND_FIELDS
    rows = [
        {"blind_pair_id": f"b{index}", **{field: "ACCEPT" for field in JUDGMENT_FIELDS}}
        for index in range(4)
    ]
    report = agreement_report(rows, rows, draws=100)
    assert report["adjudication_rate"] == 0
    assert all(value["percent_agreement"] == 1 for value in report["per_field"].values())


def test_quality_metric_and_geometry_invariants() -> None:
    image = np.zeros((12, 12, 3), dtype=np.uint8)
    assert _ssim_global(image, image) == pytest.approx(1.0)
    mask = np.zeros((12, 12), dtype=bool)
    mask[2:5, 3:7] = True
    box = _bbox(mask)
    assert box == [3, 2, 7, 5]
    overlap, fraction = _bbox_overlap(box, box)
    assert overlap == 12
    assert fraction == pytest.approx(1.0)
    assert _bbox_distance(box, box) == 0
    assert hamming(0b1010, 0b0011) == 2


def test_claim_registry_never_promotes_prospective_claims(tmp_path: Path) -> None:
    claim_registry(tmp_path)
    status = json.loads((tmp_path / "evidence/CLAIM_STATUS.json").read_text(encoding="utf-8"))
    prospective = {"prospective_joint_certificate", "cross_domain_generalization", "Main500_claim"}
    assert all(
        row["status"] == "BLOCKED"
        for row in status["claims"]
        if row["claim_id"] in prospective
    )
    assert all(row["paper_evidence"] is False for row in status["claims"])


def test_gpu_matrix_primary_notebooks_are_output_free(tmp_path: Path) -> None:
    gpu_planning(tmp_path)
    rows = list(csv.DictReader((tmp_path / "gpu/GPU_EXECUTION_MATRIX.csv").open(encoding="utf-8")))
    primary = [row for row in rows if row["notebook"].endswith(".ipynb")]
    assert primary
    repository = Path(__file__).resolve().parents[1]
    for row in primary:
        notebook = json.loads((repository / "kagglefiles" / row["notebook"]).read_text(encoding="utf-8"))
        for cell in notebook["cells"]:
            assert cell.get("outputs", []) == []
            assert cell.get("execution_count") is None
