"""Exact pre-outcome allocation optimization for the C12 confirmatory design."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from local_operator.cvpr2027_common import (  # noqa: E402
    REPO,
    artifact_manifest,
    write_csv,
    write_json,
    write_text,
)
from local_operator.cvpr2027_statistics import (  # noqa: E402
    GATE_ALPHA,
    RESPONSIVENESS,
    SPECIFICITY,
    certification_probability,
    critical_count,
)


REPORT_ROOT = REPO / "reports/cvpr2027_c12"
RELEVANT_SIZES = (80, 100, 120, 150, 180, 200, 240)
IRRELEVANT_SIZES = (80, 100, 120, 150, 180, 200, 240, 300, 360)
TOTAL_BUDGETS = (240, 300, 360, 400, 480, 600)
UPDATE_RATES = (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90)
FLIP_RATES = (0.00, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10)
DESIGN_UPDATE_RATE = 0.70
DESIGN_FLIP_RATE = 0.03
OLD_ALLOCATION = {"relevant": 120, "irrelevant": 120, "total": 240}
NEW_ALLOCATION = {"relevant": 120, "irrelevant": 240, "total": 360}


def _allocation_pairs() -> list[tuple[int, int, str]]:
    pairs = {(nr, ni, "required_grid") for nr in RELEVANT_SIZES for ni in IRRELEVANT_SIZES}
    for total in TOTAL_BUDGETS:
        # Ten-item increments expose discrete exact-test effects without creating
        # an artificial continuous optimum.
        for nr in range(60, total - 59, 10):
            pairs.add((nr, total - nr, f"total_budget_{total}"))
    return sorted(pairs)


def allocation_power(
    relevant_n: int,
    irrelevant_n: int,
    update_rate: float,
    flip_rate: float,
) -> dict[str, Any]:
    response = certification_probability(relevant_n, update_rate, RESPONSIVENESS)
    specificity = certification_probability(irrelevant_n, flip_rate, SPECIFICITY)
    model_joint = response * specificity
    all_three = model_joint**3
    any_model = 1 - (1 - model_joint) ** 3
    plus_30 = certification_probability(irrelevant_n + 30, flip_rate, SPECIFICITY)
    plus_60 = certification_probability(irrelevant_n + 60, flip_rate, SPECIFICITY)
    return {
        "relevant_n": relevant_n,
        "irrelevant_n": irrelevant_n,
        "total_n": relevant_n + irrelevant_n,
        "true_update_rate": update_rate,
        "true_flip_rate": flip_rate,
        "critical_semantic_update_successes": critical_count(relevant_n, RESPONSIVENESS),
        "critical_maximum_irrelevant_flips": critical_count(irrelevant_n, SPECIFICITY),
        "per_model_responsiveness_power": response,
        "per_model_specificity_power": specificity,
        "per_model_joint_power": model_joint,
        "claim_regime_a_all_three_six_gate_power": all_three,
        "claim_regime_a_false_negative_probability": 1 - all_three,
        "claim_regime_b_model_level_false_negative_probability": 1 - model_joint,
        "claim_regime_b_at_least_one_model_certificate_probability": any_model,
        "sample_efficiency_all_three_power_per_item": all_three / (relevant_n + irrelevant_n),
        "marginal_all_three_power_plus_30_controls": (response * plus_30) ** 3 - all_three,
        "marginal_all_three_power_plus_60_controls": (response * plus_60) ** 3 - all_three,
        "family_alpha": 0.05,
        "per_gate_alpha": GATE_ALPHA,
        "method": "exact_binomial_under_frozen_one_sided_clopper_pearson_rule",
    }


def _pareto(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in rows
        if row["true_update_rate"] == DESIGN_UPDATE_RATE
        and row["true_flip_rate"] == DESIGN_FLIP_RATE
    ]
    unique: dict[tuple[int, int], dict[str, Any]] = {}
    for row in candidates:
        unique[(row["relevant_n"], row["irrelevant_n"])] = row
    frontier = []
    for row in unique.values():
        dominated = any(
            other["total_n"] <= row["total_n"]
            and other["claim_regime_a_all_three_six_gate_power"]
            >= row["claim_regime_a_all_three_six_gate_power"]
            and (
                other["total_n"] < row["total_n"]
                or other["claim_regime_a_all_three_six_gate_power"]
                > row["claim_regime_a_all_three_six_gate_power"]
            )
            for other in unique.values()
        )
        if not dominated:
            frontier.append(row)
    return sorted(frontier, key=lambda value: (value["total_n"], value["relevant_n"]))


def _decision_markdown(decision: dict[str, Any]) -> str:
    old = decision["operating_characteristics"]["old_120_120"]
    new = decision["operating_characteristics"]["new_120_240"]
    return f"""# C12 confirmatory power decision

Decision: `{decision['decision']}`.

This decision was made before any prospective provider outcome existed. The endpoint definitions,
thresholds, one-sided exact Clopper-Pearson tests, missing-data semantics, and six-gate Bonferroni
family remain unchanged.

## Scientific claim regimes

- Regime A, `ALL_THREE_MODELS_MUST_JOINTLY_CERTIFY`, requires all six gates to pass.
- Regime B, `MODEL_LEVEL_CERTIFICATES_WITH_FAMILYWISE_ERROR_CONTROL`, permits scoped per-model
  certificates while retaining the same familywise correction. Optional models never enter the
  primary family retroactively.

## Design-scenario comparison

At true responsiveness 0.70 and true irrelevant-flip rate 0.03:

| Allocation | Response power | Specificity power | Per-model joint | All-three joint |
| --- | ---: | ---: | ---: | ---: |
| 120 relevant / 120 irrelevant | {old['per_model_responsiveness_power']:.6f} | {old['per_model_specificity_power']:.6f} | {old['per_model_joint_power']:.6f} | {old['claim_regime_a_all_three_six_gate_power']:.6f} |
| 120 relevant / 240 irrelevant | {new['per_model_responsiveness_power']:.6f} | {new['per_model_specificity_power']:.6f} | {new['per_model_joint_power']:.6f} | {new['claim_regime_a_all_three_six_gate_power']:.6f} |

The old allocation over-invested in an already high-powered responsiveness endpoint while leaving
the specificity endpoint as the dominant false-negative risk. Doubling only the controls raises
the declared all-three design-scenario power from {old['claim_regime_a_all_three_six_gate_power']:.3f}
to {new['claim_regime_a_all_three_six_gate_power']:.3f}. It also preserves the original 120-item
responsiveness commitment and avoids changing any scientific threshold.

This is a design calculation, not model evidence. Power remains truth-dependent: the full grid is
recorded in `allocation_power_grid.csv`, including unfavorable rates where neither design is likely
to certify. The amendment does not guarantee a positive result.
"""


def run(output_root: Path = REPORT_ROOT) -> dict[str, Any]:
    design_root = output_root / "design"
    rows: list[dict[str, Any]] = []
    for relevant_n, irrelevant_n, source in _allocation_pairs():
        for update_rate in UPDATE_RATES:
            for flip_rate in FLIP_RATES:
                rows.append(
                    {
                        **allocation_power(relevant_n, irrelevant_n, update_rate, flip_rate),
                        "allocation_source": source,
                    }
                )
    old = allocation_power(120, 120, DESIGN_UPDATE_RATE, DESIGN_FLIP_RATE)
    new = allocation_power(120, 240, DESIGN_UPDATE_RATE, DESIGN_FLIP_RATE)
    decision = {
        "schema": "certvic.cvpr2027.c12.confirmatory_power_decision.v1",
        "decision": "AMEND_BEFORE_OUTCOME_EXECUTION",
        "handoff_label": "AMENDED_BEFORE_PROSPECTIVE_OUTCOMES",
        "claim_regime_a": "ALL_THREE_MODELS_MUST_JOINTLY_CERTIFY",
        "claim_regime_b": "MODEL_LEVEL_CERTIFICATES_WITH_FAMILYWISE_ERROR_CONTROL",
        "primary_claim_regime": "ALL_THREE_MODELS_MUST_JOINTLY_CERTIFY",
        "old_allocation": OLD_ALLOCATION,
        "new_allocation": NEW_ALLOCATION,
        "reserve_allocation": {"relevant": 30, "irrelevant": 60, "total": 90},
        "operating_characteristics": {"old_120_120": old, "new_120_240": new},
        "unchanged": {
            "tau_update": 0.50,
            "tau_spurious": 0.10,
            "family_alpha": 0.05,
            "family_size": 6,
            "per_gate_alpha": GATE_ALPHA,
            "interval": "one_sided_exact_clopper_pearson",
            "missing_unparseable_abstention": "fail_closed",
        },
        "amendment_precondition": {
            "prospective_provider_outcomes_observed": False,
            "prospective_prediction_artifacts_present": False,
            "paper_evidence": False,
        },
        "rationale": (
            "At the declared 0.70/0.03 design scenario, all-three six-gate power rises "
            f"from {old['claim_regime_a_all_three_six_gate_power']:.6f} to "
            f"{new['claim_regime_a_all_three_six_gate_power']:.6f}; controls were the dominant "
            "false-negative bottleneck. Relevant n and every endpoint, threshold, and multiplicity "
            "rule remain unchanged."
        ),
        "evidence_class": "PRE_OUTCOME_DESIGN_VALIDATION_NOT_MODEL_EVIDENCE",
        "paper_evidence": False,
    }
    paths = [
        write_csv(design_root / "allocation_power_grid.csv", rows),
        write_csv(design_root / "allocation_pareto_frontier.csv", _pareto(rows)),
        write_json(design_root / "C12_CONFIRMATORY_POWER_DECISION.json", decision),
        write_text(design_root / "C12_CONFIRMATORY_POWER_DECISION.md", _decision_markdown(decision)),
    ]
    manifest = write_json(design_root / "DESIGN_ARTIFACT_MANIFEST.json", artifact_manifest(paths))
    return {
        **decision,
        "artifacts": [path.resolve().relative_to(REPO).as_posix() for path in [*paths, manifest]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPORT_ROOT)
    args = parser.parse_args(argv)
    result = run(args.output_root)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
