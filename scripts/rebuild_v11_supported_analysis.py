"""Rebuild every V11-supported numerical result from canonical real rows.

CPU-only, deterministic, and fail-closed. The command does not import or create
provider outputs. It validates exact item/variant keys and strict raw-answer
parsing before producing pilot, V1 specificity, paired-comparison, forensic, and
prospective power-planning tables. Human validity and independent confirmatory
specificity remain outside this command and ``paper_evidence`` remains false.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
from scipy.stats import beta, binom, norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from certvic.eval.parse import parse_answer  # noqa: E402
from certvic.metrics.certification import certify_gap  # noqa: E402


DEFAULT_OUT = ROOT / "reports/v11_full_ceiling_audit/analysis/supported_results"
PILOT_TASKS = ROOT / "data/results/main_real_200/pilot_eval_taskitems_v2.jsonl"
V1_TASKS = ROOT / "data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl"
PILOT_PREDS = {
    "qwen2_5_vl_7b": ROOT
    / "data/results/main_real_200/raw_predictions/presence__pred_qwen2_5_vl_7b_merged.jsonl",
    "internvl_8b": ROOT
    / "data/results/main_real_200/raw_predictions__internvl_8b/presence__pred_internvl_8b_presence_merged.jsonl",
    "llava_onevision_7b": ROOT
    / "data/results/main_real_200/raw_predictions__llava_onevision_7b/presence__pred_llava_onevision_7b_presence_merged.jsonl",
}
V1_PREDS = {
    provider: ROOT / f"data/results/main_real_200/kaggle_spurious/pred_{provider}_spurious_merged.jsonl"
    for provider in PILOT_PREDS
}
V1_FORENSIC_AUDIT = ROOT / (
    "data/results/main_real_200/v8_1_qwen_spurious_forensics/"
    "qwen_spurious_all_items.jsonl"
)
MODEL_ORDER = tuple(PILOT_PREDS)
V1_THRESHOLD = 0.10
ALPHA = 0.05
BOOTSTRAP_REPS = 10_000
BOOTSTRAP_SEED = 11_011


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _task_image_path(raw: str) -> Path:
    if raw.startswith("__CTRL__/"):
        return ROOT / "data/edits/spurious_flip_control" / raw.removeprefix("__CTRL__/")
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def _write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = fields or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _validate_pairs(tasks: dict[str, dict], pred_path: Path, provider: str) -> dict[str, dict[str, dict]]:
    rows = _jsonl(pred_path)
    expected = {(item_id, variant) for item_id in tasks for variant in ("original", "edited")}
    observed: dict[tuple[str, str], dict] = {}
    errors: list[str] = []
    for index, row in enumerate(rows, 1):
        key = (str(row.get("item_id")), str(row.get("image_variant")))
        if key in observed:
            errors.append(f"row {index}: duplicate key {key}")
        observed[key] = row
        if row.get("provider_name") != provider:
            errors.append(f"row {index}: wrong provider {row.get('provider_name')!r}")
        if row.get("parse_ok") is not True or row.get("parsed_answer") not in {"yes", "no"}:
            errors.append(f"row {index}: non-strict stored parse")
        reparsed = parse_answer(row.get("raw_output"), "yes_no", strict=True)
        if not reparsed.parse_ok or reparsed.parsed_answer != row.get("parsed_answer"):
            errors.append(f"row {index}: raw output does not reproduce stored parse")
    missing = sorted(expected - set(observed))
    extra = sorted(set(observed) - expected)
    if len(rows) != len(expected):
        errors.append(f"row count {len(rows)} != expected {len(expected)}")
    if missing:
        errors.append(f"missing keys {missing[:5]} (n={len(missing)})")
    if extra:
        errors.append(f"extra keys {extra[:5]} (n={len(extra)})")
    if errors:
        raise ValueError(f"{pred_path}: " + "; ".join(errors[:20]))
    return {
        item_id: {variant: observed[(item_id, variant)] for variant in ("original", "edited")}
        for item_id in sorted(tasks)
    }


def _clopper_pearson(x: int, n: int, alpha: float = ALPHA) -> dict[str, float]:
    lower = 0.0 if x == 0 else float(beta.ppf(alpha / 2, x, n - x + 1))
    upper = 1.0 if x == n else float(beta.ppf(1 - alpha / 2, x + 1, n - x))
    one_sided_upper = 1.0 if x == n else float(beta.ppf(1 - alpha, x + 1, n - x))
    return {"two_sided_lower": lower, "two_sided_upper": upper, "one_sided_upper": one_sided_upper}


def _exact_mcnemar(left: np.ndarray, right: np.ndarray) -> tuple[int, int, float]:
    left_only = int(np.sum((left == 1) & (right == 0)))
    right_only = int(np.sum((left == 0) & (right == 1)))
    discordant = left_only + right_only
    p_value = 1.0 if discordant == 0 else min(1.0, 2 * float(binom.cdf(min(left_only, right_only), discordant, 0.5)))
    return left_only, right_only, p_value


def _bootstrap_risk_difference(left: np.ndarray, right: np.ndarray) -> tuple[float, float]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    n = len(left)
    indices = rng.integers(0, n, size=(BOOTSTRAP_REPS, n))
    draws = np.mean(left[indices] - right[indices], axis=1)
    return tuple(float(value) for value in np.quantile(draws, [0.025, 0.975]))


def _holm(rows: list[dict]) -> None:
    ordered = sorted(enumerate(rows), key=lambda pair: pair[1]["mcnemar_exact_p"])
    running = 0.0
    m = len(rows)
    for rank, (index, row) in enumerate(ordered):
        adjusted = min(1.0, (m - rank) * row["mcnemar_exact_p"])
        running = max(running, adjusted)
        rows[index]["holm_adjusted_p"] = running


def _power_rows() -> list[dict]:
    rows: list[dict] = []
    for n in (30, 60, 94, 150, 200, 300, 500):
        passing_x = [x for x in range(n + 1) if _clopper_pearson(x, n)["one_sided_upper"] <= V1_THRESHOLD]
        max_passing = max(passing_x, default=-1)
        for true_rate in (0.01, 0.03, 0.05, 0.08, 0.10, 0.12):
            probability = 0.0 if max_passing < 0 else float(binom.cdf(max_passing, n, true_rate))
            rows.append(
                {
                    "n": n,
                    "true_flip_rate_assumption": true_rate,
                    "max_flips_passing_one_sided_cp_upper_lte_0_10": max_passing,
                    "probability_of_passing": probability,
                    "evidence_class": "PLANNED_NOT_EXECUTED",
                }
            )
    return rows


def _paired_difference_power_rows() -> list[dict]:
    z2 = float((norm.ppf(0.975) + norm.ppf(0.80)) ** 2)
    rows = []
    for discordant_fraction in (0.10, 0.20, 0.30):
        for paired_risk_difference in (0.05, 0.10, 0.15):
            rows.append(
                {
                    "discordant_fraction_assumption": discordant_fraction,
                    "paired_risk_difference_assumption": paired_risk_difference,
                    "two_sided_alpha": 0.05,
                    "target_power": 0.80,
                    "normal_approx_required_pairs": math.ceil(
                        z2 * discordant_fraction / paired_risk_difference**2
                    ),
                    "method": "paired_binary_normal_approximation_verify_with_exact_simulation_before_lock",
                    "evidence_class": "PLANNED_NOT_EXECUTED",
                }
            )
    return rows


def _domain_interaction_power_rows() -> list[dict]:
    z2 = float((norm.ppf(0.975) + norm.ppf(0.80)) ** 2)
    return [
        {
            "domain_interaction_effect_assumption": effect,
            "two_sided_alpha": 0.05,
            "target_power": 0.80,
            "conservative_required_pairs_per_domain": math.ceil(2 * z2 / effect**2),
            "method": "bounded_difference_conservative_normal_approximation",
            "evidence_class": "PLANNED_NOT_EXECUTED",
        }
        for effect in (0.05, 0.10, 0.15, 0.20)
    ]


def _human_review_precision_rows() -> list[dict]:
    z2 = float(norm.ppf(0.975) ** 2)
    rows = []
    for agreement in (0.80, 0.90):
        for half_width in (0.05, 0.075, 0.10):
            rows.append(
                {
                    "agreement_assumption": agreement,
                    "target_95_half_width": half_width,
                    "normal_approx_required_items": math.ceil(
                        z2 * agreement * (1 - agreement) / half_width**2
                    ),
                    "method": "raw_agreement_precision_kappa_requires_prevalence_sensitivity",
                    "evidence_class": "PLANNED_NOT_EXECUTED",
                }
            )
    return rows


def rebuild(out_dir: Path = DEFAULT_OUT) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    pilot_tasks = {row["item_id"]: row for row in _jsonl(PILOT_TASKS)}
    v1_tasks = {row["item_id"]: row for row in _jsonl(V1_TASKS)}
    forensic_audit = {row["item_id"]: row for row in _jsonl(V1_FORENSIC_AUDIT)}
    if len(pilot_tasks) != 91 or len(v1_tasks) != 94:
        raise ValueError("canonical task denominators changed")

    pilot_rows: list[dict] = []
    pilot_pairs: dict[str, dict[str, dict[str, dict]]] = {}
    for provider in MODEL_ORDER:
        pairs = _validate_pairs(pilot_tasks, PILOT_PREDS[provider], provider)
        pilot_pairs[provider] = pairs
        original_correct = [
            int(pair["original"]["parsed_answer"] == pilot_tasks[item_id]["answer_original"])
            for item_id, pair in pairs.items()
        ]
        raw_change = [
            int(pair["original"]["parsed_answer"] != pair["edited"]["parsed_answer"])
            for pair in pairs.values()
        ]
        correct_update = [
            int(
                pair["original"]["parsed_answer"] == pilot_tasks[item_id]["answer_original"]
                and pair["edited"]["parsed_answer"] == pilot_tasks[item_id]["answer_edited"]
            )
            for item_id, pair in pairs.items()
        ]
        certification = certify_gap(original_correct, raw_change, delta_threshold=0.05, alpha=ALPHA, allow_unavailable=True)
        family_counts = Counter(task["task_family"] for task in pilot_tasks.values())
        n = len(pairs)
        pilot_rows.append(
            {
                "provider": provider,
                "n_items": n,
                "n_prediction_rows": 2 * n,
                "original_correct": sum(original_correct),
                "original_accuracy_a": sum(original_correct) / n,
                "raw_answer_changes": sum(raw_change),
                "historical_consistency_p": sum(raw_change) / n,
                "intervention_gap_delta": (sum(original_correct) - sum(raw_change)) / n,
                "correct_semantic_updates": sum(correct_update),
                "correct_semantic_update_rate": sum(correct_update) / n,
                "cs_lower_bound": certification["lower_bound"],
                "cs_upper_bound": certification["upper_bound"],
                "cs_numeric_threshold_crossed": certification["cs_threshold_passed"],
                "full_policy_passed": False,
                "full_policy_block": "n_overall_91_lt_150_and_family_counts_54_31_6_include_below_40",
                "family_counts": json.dumps(dict(sorted(family_counts.items())), sort_keys=True),
                "evidence_class": "DERIVED_FROM_REAL_EVIDENCE",
                "human_reviewed": False,
                "paper_evidence": False,
                "source_sha256": _sha256(PILOT_PREDS[provider]),
            }
        )

    v1_rows: list[dict] = []
    v1_vectors: dict[str, np.ndarray] = {}
    v1_pairs: dict[str, dict[str, dict[str, dict]]] = {}
    for provider in MODEL_ORDER:
        pairs = _validate_pairs(v1_tasks, V1_PREDS[provider], provider)
        v1_pairs[provider] = pairs
        vector = np.asarray(
            [int(pair["original"]["parsed_answer"] != pair["edited"]["parsed_answer"]) for pair in pairs.values()],
            dtype=int,
        )
        v1_vectors[provider] = vector
        flips, n = int(vector.sum()), len(vector)
        interval = _clopper_pearson(flips, n)
        v1_rows.append(
            {
                "provider": provider,
                "n_items": n,
                "n_prediction_rows": 2 * n,
                "flips": flips,
                "observed_flip_rate": flips / n,
                **interval,
                "frozen_v1_threshold": V1_THRESHOLD,
                "frozen_v1_gate": "PASS" if flips / n <= V1_THRESHOLD else "FAIL",
                "evidence_class": "DERIVED_FROM_REAL_EVIDENCE",
                "human_reviewed": False,
                "paper_evidence": False,
                "source_sha256": _sha256(V1_PREDS[provider]),
            }
        )

    paired_rows: list[dict] = []
    for left_index, left_name in enumerate(MODEL_ORDER):
        for right_name in MODEL_ORDER[left_index + 1 :]:
            left, right = v1_vectors[left_name], v1_vectors[right_name]
            left_only, right_only, p_value = _exact_mcnemar(left, right)
            ci_low, ci_high = _bootstrap_risk_difference(left, right)
            paired_rows.append(
                {
                    "left_provider": left_name,
                    "right_provider": right_name,
                    "n_paired_items": len(left),
                    "left_only_flips": left_only,
                    "right_only_flips": right_only,
                    "paired_risk_difference": float(np.mean(left - right)),
                    "bootstrap_95_low": ci_low,
                    "bootstrap_95_high": ci_high,
                    "bootstrap_reps": BOOTSTRAP_REPS,
                    "bootstrap_seed": BOOTSTRAP_SEED,
                    "mcnemar_exact_p": p_value,
                    "holm_adjusted_p": None,
                    "confirmatory": False,
                    "evidence_class": "DERIVED_FROM_REAL_EVIDENCE",
                }
            )
    _holm(paired_rows)

    qwen_failure_rows: list[dict] = []
    qwen_ids = list(v1_pairs["qwen2_5_vl_7b"])
    for index, item_id in enumerate(qwen_ids):
        if not v1_vectors["qwen2_5_vl_7b"][index]:
            continue
        task = v1_tasks[item_id]
        audit = forensic_audit[item_id]
        row = {
            "item_id": item_id,
            "expected_answer_original": task["answer_original"],
            "expected_answer_edited": task["answer_edited"],
            "prompt": task["question_original"],
            "answer_format": task["answer_format"],
            "original_image_path": task["original_image_path"],
            "edited_image_path": task["edited_image_path"],
            "original_image_sha256": _sha256(_task_image_path(task["original_image_path"])),
            "edited_image_sha256": _sha256(_task_image_path(task["edited_image_path"])),
            "parser_or_provenance_defect_found": False,
            "patch_bbox_intersects_target_bbox": audit.get("patch_bbox_intersects_object_bbox"),
            "patch_target_mask_overlap_pixels": audit.get("patch_target_mask_overlap_pixels"),
            "patch_target_bbox_distance_px": audit.get("patch_object_bbox_distance_px"),
            "stored_detectability_score": audit.get("detectability_score"),
            "exclusion_status": "not_excluded_raw_v1_preserved",
            "subjective_visual_validity": "HUMAN_REVIEW_PENDING",
        }
        for provider in MODEL_ORDER:
            pair = v1_pairs[provider][item_id]
            row[f"{provider}_original_raw"] = pair["original"]["raw_output"]
            row[f"{provider}_edited_raw"] = pair["edited"]["raw_output"]
            row[f"{provider}_original_parsed"] = pair["original"]["parsed_answer"]
            row[f"{provider}_edited_parsed"] = pair["edited"]["parsed_answer"]
            row[f"{provider}_parse_ok"] = bool(
                pair["original"]["parse_ok"] and pair["edited"]["parse_ok"]
            )
            row[f"{provider}_flip"] = pair["original"]["parsed_answer"] != pair["edited"]["parsed_answer"]
        qwen_failure_rows.append(row)
    if len(qwen_failure_rows) != 12:
        raise ValueError(f"expected 12 Qwen V1 failures, found {len(qwen_failure_rows)}")

    power_rows = _power_rows()
    paired_power_rows = _paired_difference_power_rows()
    domain_power_rows = _domain_interaction_power_rows()
    human_power_rows = _human_review_precision_rows()
    _write_csv(out_dir / "pilot_results.csv", pilot_rows)
    _write_csv(out_dir / "v1_specificity_results.csv", v1_rows)
    _write_csv(out_dir / "paired_comparisons.csv", paired_rows)
    _write_csv(out_dir / "qwen_12_forensic_table.csv", qwen_failure_rows)
    _write_csv(out_dir / "prospective_power_sensitivity.csv", power_rows)
    _write_csv(out_dir / "paired_difference_power_sensitivity.csv", paired_power_rows)
    _write_csv(out_dir / "domain_interaction_power_sensitivity.csv", domain_power_rows)
    _write_csv(out_dir / "human_review_precision_sensitivity.csv", human_power_rows)

    result = {
        "schema": "certvic.v11.supported_analysis.v1",
        "generated_date": date.today().isoformat(),
        "command": "python3 scripts/rebuild_v11_supported_analysis.py",
        "evidence_class": "DERIVED_FROM_REAL_EVIDENCE",
        "paper_evidence": False,
        "human_reviewed": False,
        "pilot_task_sha256": _sha256(PILOT_TASKS),
        "v1_task_sha256": _sha256(V1_TASKS),
        "pilot": pilot_rows,
        "v1_specificity": v1_rows,
        "paired_comparisons": paired_rows,
        "qwen_failure_count": len(qwen_failure_rows),
        "power_planning_is_observed_evidence": False,
        "limitations": [
            "historical embedded review labels are superseded by V11 MACHINE_ASSISTED_PRELIMINARY classification",
            "model commit revisions were not recorded for historical runs",
            "the 91-item pilot fails the full minimum-n and family-count policy",
            "no independent confirmatory specificity set or real two-rater validity review exists",
        ],
    }
    (out_dir / "supported_analysis.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "README.md").write_text(
        "# V11 Supported Analysis Rebuild\n\n"
        "Run `python3 scripts/rebuild_v11_supported_analysis.py`. The command validates strict raw parsing and exact pair keys, then rebuilds all V11 numerical tables from real canonical rows. It creates no model outputs or human labels. `paper_evidence=false` remains locked.\n",
        encoding="utf-8",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    result = rebuild(args.out_dir)
    try:
        displayed_out = f"<PROJECT_ROOT>/{args.out_dir.resolve().relative_to(ROOT).as_posix()}"
    except ValueError:
        displayed_out = f"<EXTERNAL_OUTPUT>/{args.out_dir.name}"
    print(
        json.dumps(
            {
                "out_dir": displayed_out,
                "pilot_models": len(result["pilot"]),
                "v1_models": len(result["v1_specificity"]),
                "qwen_failures": result["qwen_failure_count"],
                "paper_evidence": result["paper_evidence"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
