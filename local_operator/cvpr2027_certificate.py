"""Machine-readable responsiveness-specificity certificate definitions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from local_operator.cvpr2027_common import REPORT_ROOT, write_csv, write_json  # noqa: E402
from local_operator.cvpr2027_statistics import (  # noqa: E402
    FAMILY_ALPHA,
    FAMILY_SIZE,
    TAU_SPURIOUS,
    TAU_UPDATE,
    cp_lower,
    cp_upper,
)


REGIONS = {
    "RESPONSIVE_AND_SPECIFIC": {
        "responsiveness": f"> {TAU_UPDATE}",
        "spurious": f"<= {TAU_SPURIOUS}",
    },
    "RESPONSIVE_BUT_SPURIOUS": {
        "responsiveness": f"> {TAU_UPDATE}",
        "spurious": f"> {TAU_SPURIOUS}",
    },
    "INERT_BUT_SPECIFIC": {
        "responsiveness": f"<= {TAU_UPDATE}",
        "spurious": f"<= {TAU_SPURIOUS}",
    },
    "INERT_AND_SPURIOUS": {
        "responsiveness": f"<= {TAU_UPDATE}",
        "spurious": f"> {TAU_SPURIOUS}",
    },
}


def coordinate_region(responsiveness: float, spurious: float) -> str:
    responsive = responsiveness > TAU_UPDATE
    specific = spurious <= TAU_SPURIOUS
    if responsive and specific:
        return "RESPONSIVE_AND_SPECIFIC"
    if responsive:
        return "RESPONSIVE_BUT_SPURIOUS"
    if specific:
        return "INERT_BUT_SPECIFIC"
    return "INERT_AND_SPURIOUS"


def compute_certificate(
    *,
    model: str,
    relevant_outcomes: Iterable[bool],
    irrelevant_flip_outcomes: Iterable[bool],
    missing_count: int = 0,
    parse_failure_count: int = 0,
    abstention_count: int = 0,
    evidence_class: str,
    artifact_hashes: dict[str, str],
    genuine_human_review: bool = False,
    prospective: bool = False,
) -> dict[str, Any]:
    relevant = [bool(value) for value in relevant_outcomes]
    irrelevant = [bool(value) for value in irrelevant_flip_outcomes]
    if not relevant or not irrelevant:
        raise ValueError("certificate requires nonempty relevant and irrelevant arms")
    alpha = FAMILY_ALPHA / FAMILY_SIZE
    successes = sum(relevant)
    flips = sum(irrelevant)
    response_rate = successes / len(relevant)
    spurious_rate = flips / len(irrelevant)
    response_lower = float(cp_lower(successes, len(relevant), alpha))
    spurious_upper = float(cp_upper(flips, len(irrelevant), alpha))
    response_gate = response_lower > TAU_UPDATE
    specificity_gate = spurious_upper <= TAU_SPURIOUS
    statistical_joint = response_gate and specificity_gate
    evidence_eligible = genuine_human_review and prospective and not (
        missing_count or parse_failure_count or abstention_count
    )
    return {
        "schema": "certvic.cvpr2027.model_certificate.v1",
        "model": model,
        "n_relevant": len(relevant),
        "n_irrelevant": len(irrelevant),
        "semantic_update_successes": successes,
        "irrelevant_flips": flips,
        "responsiveness_point_estimate": response_rate,
        "specificity_point_estimate": spurious_rate,
        "responsiveness_lower_bound": response_lower,
        "spurious_upper_bound": spurious_upper,
        "responsiveness_gate": response_gate,
        "specificity_gate": specificity_gate,
        "statistical_joint_gate": statistical_joint,
        "joint_certificate": statistical_joint and evidence_eligible,
        "coordinate_region": coordinate_region(response_rate, spurious_rate),
        "multiplicity_family": "three_models_by_two_primary_gates",
        "family_alpha": FAMILY_ALPHA,
        "alpha": alpha,
        "thresholds": {"tau_update": TAU_UPDATE, "tau_spurious": TAU_SPURIOUS},
        "missing_count": missing_count,
        "parse_failure_count": parse_failure_count,
        "abstention_count": abstention_count,
        "evidence_class": evidence_class,
        "genuine_human_review": genuine_human_review,
        "prospective": prospective,
        "evidence_eligible": evidence_eligible,
        "artifact_hashes": dict(sorted(artifact_hashes.items())),
        "paper_evidence": False,
    }


def write_certificate_outputs(certificates: list[dict[str, Any]], output: Path) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    coordinates = [
        {
            "model": row["model"],
            "responsiveness_point_estimate": row["responsiveness_point_estimate"],
            "specificity_point_estimate": row["specificity_point_estimate"],
            "responsiveness_lower_bound": row["responsiveness_lower_bound"],
            "spurious_upper_bound": row["spurious_upper_bound"],
            "coordinate_region": row["coordinate_region"],
            "statistical_joint_gate": row["statistical_joint_gate"],
            "joint_certificate": row["joint_certificate"],
            "evidence_class": row["evidence_class"],
        }
        for row in certificates
    ]
    paths = [
        write_csv(output / "certificate_coordinates.csv", coordinates),
        write_json(
            output / "certificate_regions.json",
            {
                "schema": "certvic.cvpr2027.certificate_regions.v1",
                "definitions": REGIONS,
                "thresholds": {"tau_update": TAU_UPDATE, "tau_spurious": TAU_SPURIOUS},
                "boundary_semantics": {
                    "responsiveness": "strictly greater than threshold",
                    "specificity": "less than or equal to threshold",
                },
                "paper_evidence": False,
            },
        ),
        write_json(
            output / "model_certificates.json",
            {
                "schema": "certvic.cvpr2027.model_certificate_collection.v1",
                "certificates": certificates,
                "paper_evidence": False,
            },
        ),
    ]
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPORT_ROOT / "evidence")
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(
        args.output / "certificate_regions.json",
        {
            "schema": "certvic.cvpr2027.certificate_regions.v1",
            "definitions": REGIONS,
            "status": "API_READY_INPUTS_REQUIRED",
            "paper_evidence": False,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
