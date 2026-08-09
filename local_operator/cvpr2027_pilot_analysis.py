"""C11 deterministic baselines, ablations, paired tests, and heterogeneity analyses."""

from __future__ import annotations

import argparse
import itertools
import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.stats import beta, binomtest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from certvic.metrics.anytime_cs import hoeffding_mixture_cs_01  # noqa: E402
from local_operator.cvpr2027_certificate import (  # noqa: E402
    compute_certificate,
    write_certificate_outputs,
)
from local_operator.cvpr2027_common import (  # noqa: E402
    REPO,
    REPORT_ROOT,
    artifact_manifest,
    read_jsonl,
    sha256_file,
    write_csv,
    write_json,
)
from local_operator.cvpr2027_statistics import (  # noqa: E402
    GATE_ALPHA,
    TAU_SPURIOUS,
    TAU_UPDATE,
    cp_lower,
    cp_upper,
)


PROVIDER_FILES = {
    "qwen2_5_vl_7b": {
        "relevant": REPO
        / "data/results/main_real_200/raw_predictions/presence__pred_qwen2_5_vl_7b_merged.jsonl",
        "irrelevant": REPO
        / "data/results/main_real_200/kaggle_spurious/pred_qwen2_5_vl_7b_spurious_merged.jsonl",
    },
    "internvl_8b": {
        "relevant": REPO
        / "data/results/main_real_200/raw_predictions__internvl_8b/"
        "presence__pred_internvl_8b_presence_merged.jsonl",
        "irrelevant": REPO
        / "data/results/main_real_200/kaggle_spurious/pred_internvl_8b_spurious_merged.jsonl",
    },
    "llava_onevision_7b": {
        "relevant": REPO
        / "data/results/main_real_200/raw_predictions__llava_onevision_7b/"
        "presence__pred_llava_onevision_7b_presence_merged.jsonl",
        "irrelevant": REPO
        / "data/results/main_real_200/kaggle_spurious/pred_llava_onevision_7b_spurious_merged.jsonl",
    },
}
# The presence outputs were run against the V2 task encoding.  It preserves the same
# 91 image pairs while fixing the questions/gold transitions to the actual presence task.
RELEVANT_TASKS = REPO / "data/results/main_real_200/pilot_eval_tasks_reviewed_v2.jsonl"
IRRELEVANT_TASKS = REPO / "data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl"


def normalize_answer(value: Any) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).casefold().strip().split())
    return normalized if normalized in {"yes", "no"} else None


def _prediction_pairs(path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in read_jsonl(path):
        item_id = str(row.get("item_id", ""))
        variant = str(row.get("image_variant", ""))
        if not item_id or variant not in {"original", "edited"}:
            raise ValueError(f"invalid prediction key in {path}")
        if variant in result[item_id]:
            raise ValueError(f"duplicate prediction key {item_id}/{variant} in {path}")
        result[item_id][variant] = row
    return dict(result)


def _category(task: dict[str, Any]) -> str:
    metadata = task.get("metadata") or {}
    if metadata.get("object"):
        return str(metadata["object"])
    question = str(task.get("question_original", ""))
    match = re.search(r"visible\s+([a-z][a-z_-]*)", question.casefold())
    return match.group(1) if match else str(task.get("task_family", "UNSPECIFIED"))


def _source_id(task: dict[str, Any]) -> str:
    source = task.get("source") or {}
    return str(task.get("source_id") or source.get("source_id") or task.get("item_id"))


def build_item_outcomes(
    tasks_path: Path,
    predictions_path: Path,
    *,
    endpoint: str,
) -> list[dict[str, Any]]:
    tasks = read_jsonl(tasks_path)
    predictions = _prediction_pairs(predictions_path)
    task_ids = {str(task["item_id"]) for task in tasks}
    extra = set(predictions) - task_ids
    if extra:
        raise ValueError(f"provider output has {len(extra)} extra task IDs")
    rows = []
    for task in tasks:
        item_id = str(task["item_id"])
        pair = predictions.get(item_id, {})
        original_row = pair.get("original")
        edited_row = pair.get("edited")
        original = normalize_answer(original_row.get("parsed_answer")) if original_row else None
        edited = normalize_answer(edited_row.get("parsed_answer")) if edited_row else None
        parse_ok = bool(
            original_row
            and edited_row
            and original_row.get("parse_ok") is True
            and edited_row.get("parse_ok") is True
            and original is not None
            and edited is not None
        )
        gold_original = normalize_answer(task.get("answer_original"))
        gold_edited = normalize_answer(task.get("answer_edited"))
        original_correct = parse_ok and original == gold_original
        edited_correct = parse_ok and edited == gold_edited
        raw_change = parse_ok and original != edited
        relevant = str(task.get("required_change")) == "change"
        semantic_success = (
            relevant
            and original_correct
            and edited_correct
            and gold_original != gold_edited
            and raw_change
        )
        irrelevant_flip = (
            (not parse_ok) or raw_change
            if endpoint == "irrelevant"
            else (not parse_ok) or (not semantic_success)
        )
        quality = task.get("quality") or {}
        rows.append(
            {
                "item_id": item_id,
                "source_id": _source_id(task),
                "category": _category(task),
                "task_family": str(task.get("task_family", "UNSPECIFIED")),
                "perturbation_family": str(
                    task.get("edit_type")
                    or (task.get("edit") or {}).get("edit_type")
                    or "UNSPECIFIED"
                ),
                "answer_polarity": gold_original,
                "required_change": str(task.get("required_change")),
                "parse_ok": parse_ok,
                "missing": original_row is None or edited_row is None,
                "original_answer": original,
                "edited_answer": edited,
                "original_correct": original_correct,
                "edited_correct": edited_correct,
                "raw_change": raw_change,
                "semantic_update_success": semantic_success,
                "irrelevant_flip": irrelevant_flip,
                "edit_area_fraction": quality.get("total_changed_fraction"),
                "mask_area_fraction": quality.get("mask_area_fraction"),
            }
        )
    return rows


def _bootstrap_bound(
    values: list[bool], *, quantile: float, seed: int, draws: int = 10_000
) -> float:
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(array, size=(draws, len(array)), replace=True).mean(axis=1)
    return float(np.quantile(samples, quantile, method="lower" if quantile < 0.5 else "higher"))


def _metric_row(
    provider: str,
    relevant_all: list[dict[str, Any]],
    irrelevant: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    relevant = [row for row in relevant_all if row["required_change"] == "change"]
    semantic = [bool(row["semantic_update_success"]) for row in relevant]
    flips = [bool(row["irrelevant_flip"]) for row in irrelevant]
    full_raw_changes = [bool(row["raw_change"]) for row in relevant_all]
    full_original_correct = [bool(row["original_correct"]) for row in relevant_all]
    response = sum(semantic) / len(semantic)
    spurious = sum(flips) / len(flips)
    exact_response_05 = float(cp_lower(sum(semantic), len(semantic), 0.05))
    exact_spurious_05 = float(cp_upper(sum(flips), len(flips), 0.05))
    exact_response_multiplicity = float(cp_lower(sum(semantic), len(semantic), GATE_ALPHA))
    exact_spurious_multiplicity = float(cp_upper(sum(flips), len(flips), GATE_ALPHA))
    response_cs = hoeffding_mixture_cs_01(semantic, alpha=GATE_ALPHA, t_opt=len(semantic))
    spurious_cs = hoeffding_mixture_cs_01(flips, alpha=GATE_ALPHA, t_opt=len(flips))
    conditioned = [row for row in relevant if row["original_correct"]]
    bootstrap_response_lower = _bootstrap_bound(
        semantic, quantile=0.025, seed=12013 + len(provider)
    )
    bootstrap_spurious_upper = _bootstrap_bound(
        flips, quantile=0.975, seed=13013 + len(provider)
    )
    point_joint = response > TAU_UPDATE and spurious <= TAU_SPURIOUS
    exact_joint_05 = exact_response_05 > TAU_UPDATE and exact_spurious_05 <= TAU_SPURIOUS
    exact_joint_multiplicity = (
        exact_response_multiplicity > TAU_UPDATE
        and exact_spurious_multiplicity <= TAU_SPURIOUS
    )
    bootstrap_joint = (
        bootstrap_response_lower > TAU_UPDATE and bootstrap_spurious_upper <= TAU_SPURIOUS
    )
    cs_joint = (
        float(response_cs["latest"]["lo"]) > TAU_UPDATE
        and float(spurious_cs["latest"]["hi"]) <= TAU_SPURIOUS
    )
    metrics = {
        "model": provider,
        "evidence_class": "RETROSPECTIVE_DIAGNOSTIC",
        "paper_evidence": False,
        "n_frozen_intervention_items": len(relevant_all),
        "n_relevant_endpoint_items": len(relevant),
        "n_specificity_items": len(irrelevant),
        "original_image_accuracy_all_frozen": sum(full_original_correct) / len(relevant_all),
        "edited_image_accuracy_all_frozen": sum(bool(row["edited_correct"]) for row in relevant_all)
        / len(relevant_all),
        "raw_answer_change_rate_all_frozen": sum(full_raw_changes) / len(relevant_all),
        "raw_consistency_all_frozen": 1 - sum(full_raw_changes) / len(relevant_all),
        "semantic_update_successes": sum(semantic),
        "semantic_update_success_rate": response,
        "conditional_semantic_update_rate_given_original_correct": (
            sum(bool(row["semantic_update_success"]) for row in conditioned) / len(conditioned)
            if conditioned
            else None
        ),
        "original_correct_subset_n": len(conditioned),
        "irrelevant_flips": sum(flips),
        "irrelevant_flip_rate": spurious,
        "specificity_rate": 1 - spurious,
        "point_estimate_joint_decision": point_joint,
        "standard_exact_ci_response_lower": exact_response_05,
        "standard_exact_ci_spurious_upper": exact_spurious_05,
        "standard_exact_ci_joint_decision": exact_joint_05,
        "bootstrap_response_lower_95": bootstrap_response_lower,
        "bootstrap_spurious_upper_95": bootstrap_spurious_upper,
        "bootstrap_joint_decision": bootstrap_joint,
        "cs_response_lower": response_cs["latest"]["lo"],
        "cs_spurious_upper": spurious_cs["latest"]["hi"],
        "confidence_sequence_joint_decision": cs_joint,
        "multiplicity_corrected_response_lower": exact_response_multiplicity,
        "multiplicity_corrected_spurious_upper": exact_spurious_multiplicity,
        "multiplicity_corrected_joint_decision": exact_joint_multiplicity,
        "joint_balance_score": min(response, 1 - spurious),
    }
    ablations = {
        "no_specificity_gate": response > TAU_UPDATE,
        "no_responsiveness_gate": spurious <= TAU_SPURIOUS,
        "no_multiplicity_correction": exact_joint_05,
        "no_human_validity_filter": exact_joint_multiplicity,
        "with_genuine_human_validity_filter": None,
        "complete_case_parser_handling": exact_joint_multiplicity,
        "fail_closed_parser_handling": exact_joint_multiplicity,
        "point_estimate_only": point_joint,
        "exact_ci_only": exact_joint_multiplicity,
        "confidence_sequence_only": cs_joint,
        "joint_gate": exact_joint_multiplicity,
    }
    return metrics, ablations


def _rankings(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    definitions: dict[str, tuple[Callable[[dict[str, Any]], float], bool]] = {
        "original_image_accuracy": (lambda row: row["original_image_accuracy_all_frozen"], True),
        "raw_answer_change_rate": (lambda row: row["raw_answer_change_rate_all_frozen"], True),
        "semantic_update_success": (lambda row: row["semantic_update_success_rate"], True),
        "specificity": (lambda row: row["specificity_rate"], True),
        "joint_balance": (lambda row: row["joint_balance_score"], True),
        "irrelevant_flip": (lambda row: row["irrelevant_flip_rate"], False),
    }
    rows = []
    for metric, (getter, descending) in definitions.items():
        ordered = sorted(metrics, key=getter, reverse=descending)
        for rank, row in enumerate(ordered, start=1):
            rows.append(
                {
                    "metric": metric,
                    "rank": rank,
                    "model": row["model"],
                    "value": getter(row),
                    "higher_is_better": descending,
                    "evidence_class": "RETROSPECTIVE_DIAGNOSTIC",
                }
            )
    return rows


def _holm(p_values: list[float]) -> list[float]:
    order = np.argsort(p_values)
    adjusted = np.zeros(len(p_values), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (len(p_values) - rank) * p_values[index])
        adjusted[index] = min(1.0, running)
    return adjusted.tolist()


def pairwise_comparisons(
    outcomes: dict[str, dict[str, list[dict[str, Any]]]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows = []
    disagreement = []
    providers = sorted(outcomes)
    for endpoint, field in [
        ("responsiveness", "semantic_update_success"),
        ("specificity_failure", "irrelevant_flip"),
    ]:
        p_values = []
        endpoint_rows = []
        for left, right in itertools.combinations(providers, 2):
            left_items = {
                row["item_id"]: bool(row[field])
                for row in outcomes[left]["relevant" if endpoint == "responsiveness" else "irrelevant"]
                if endpoint != "responsiveness" or row["required_change"] == "change"
            }
            right_items = {
                row["item_id"]: bool(row[field])
                for row in outcomes[right]["relevant" if endpoint == "responsiveness" else "irrelevant"]
                if endpoint != "responsiveness" or row["required_change"] == "change"
            }
            common = sorted(set(left_items) & set(right_items))
            left_vector = np.asarray([left_items[item] for item in common], dtype=int)
            right_vector = np.asarray([right_items[item] for item in common], dtype=int)
            left_only = int(((left_vector == 1) & (right_vector == 0)).sum())
            right_only = int(((left_vector == 0) & (right_vector == 1)).sum())
            discordant = left_only + right_only
            p_value = (
                float(binomtest(min(left_only, right_only), discordant, 0.5).pvalue)
                if discordant
                else 1.0
            )
            differences = left_vector - right_vector
            rng = np.random.default_rng(12013 + len(rows))
            bootstrap = rng.choice(differences, size=(10_000, len(differences)), replace=True).mean(axis=1)
            row = {
                "endpoint": endpoint,
                "left_model": left,
                "right_model": right,
                "paired_n": len(common),
                "left_rate": float(left_vector.mean()),
                "right_rate": float(right_vector.mean()),
                "risk_difference_left_minus_right": float(differences.mean()),
                "risk_difference_bootstrap_95_lower": float(np.quantile(bootstrap, 0.025)),
                "risk_difference_bootstrap_95_upper": float(np.quantile(bootstrap, 0.975)),
                "left_only": left_only,
                "right_only": right_only,
                "exact_mcnemar_p": p_value,
                "evidence_class": "RETROSPECTIVE_DIAGNOSTIC",
            }
            endpoint_rows.append(row)
            p_values.append(p_value)
            disagreement.append(
                {
                    "endpoint": endpoint,
                    "left_model": left,
                    "right_model": right,
                    "paired_n": len(common),
                    "disagreement_count": discordant,
                    "disagreement_rate": discordant / len(common),
                }
            )
        for row, adjusted in zip(endpoint_rows, _holm(p_values), strict=True):
            row["holm_adjusted_p"] = adjusted
        rows.extend(endpoint_rows)
    intersection: dict[str, Any] = {}
    for endpoint, field, arm in [
        ("responsiveness", "semantic_update_success", "relevant"),
        ("specificity_failure", "irrelevant_flip", "irrelevant"),
    ]:
        maps = {
            provider: {
                row["item_id"]: bool(row[field])
                for row in outcomes[provider][arm]
                if endpoint != "responsiveness" or row["required_change"] == "change"
            }
            for provider in providers
        }
        common = sorted(set.intersection(*(set(value) for value in maps.values())))
        patterns = Counter(
            "|".join(f"{provider}={int(maps[provider][item])}" for provider in providers)
            for item in common
        )
        intersection[endpoint] = {
            "providers": providers,
            "paired_n": len(common),
            "patterns": dict(sorted(patterns.items())),
            "all_three_positive": sum(all(maps[p][item] for p in providers) for item in common),
            "all_three_negative": sum(not any(maps[p][item] for p in providers) for item in common),
        }
    return rows, disagreement, intersection


def _two_sided_interval(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    lower = 0.0 if successes == 0 else float(beta.ppf(alpha / 2, successes, n - successes + 1))
    upper = 1.0 if successes == n else float(beta.ppf(1 - alpha / 2, successes + 1, n - successes))
    return lower, upper


def heterogeneity_analysis(
    outcomes: dict[str, dict[str, list[dict[str, Any]]]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    summary = []
    leave_out = []
    influence = []
    failure_counts: Counter[str] = Counter()
    for provider, arms in outcomes.items():
        for endpoint, arm, field in [
            ("responsiveness", "relevant", "semantic_update_success"),
            ("specificity_failure", "irrelevant", "irrelevant_flip"),
        ]:
            base = [
                row
                for row in arms[arm]
                if endpoint != "responsiveness" or row["required_change"] == "change"
            ]
            for group_field in [
                "category",
                "task_family",
                "perturbation_family",
                "answer_polarity",
            ]:
                groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for row in base:
                    groups[str(row.get(group_field, "UNSPECIFIED"))].append(row)
                for group, rows in sorted(groups.items()):
                    successes = sum(bool(row[field]) for row in rows)
                    lower, upper = _two_sided_interval(successes, len(rows))
                    summary.append(
                        {
                            "model": provider,
                            "endpoint": endpoint,
                            "stratum_field": group_field,
                            "stratum": group,
                            "n": len(rows),
                            "events": successes,
                            "rate": successes / len(rows),
                            "exact_95_lower": lower,
                            "exact_95_upper": upper,
                            "analysis_class": "EXPLORATORY_NOT_PRIMARY",
                        }
                    )
                    retained = [row for row in base if str(row.get(group_field)) != group]
                    if retained:
                        leave_out.append(
                            {
                                "model": provider,
                                "endpoint": endpoint,
                                "group_field": group_field,
                                "left_out_group": group,
                                "retained_n": len(retained),
                                "retained_rate": sum(bool(row[field]) for row in retained)
                                / len(retained),
                                "full_rate": sum(bool(row[field]) for row in base) / len(base),
                            }
                        )
            total_events = sum(bool(row[field]) for row in base)
            full_rate = total_events / len(base)
            for row in base:
                without = (total_events - int(bool(row[field]))) / (len(base) - 1)
                influence.append(
                    {
                        "model": provider,
                        "endpoint": endpoint,
                        "item_id": row["item_id"],
                        "source_id": row["source_id"],
                        "event": bool(row[field]),
                        "leave_one_out_rate": without,
                        "absolute_influence": abs(without - full_rate),
                    }
                )
                failure = (not bool(row[field])) if endpoint == "responsiveness" else bool(row[field])
                if failure:
                    failure_counts[row["item_id"]] += 1
    values = np.asarray(sorted(failure_counts.values()), dtype=float)
    if values.size and values.sum():
        ordered = np.sort(values)
        gini = float(
            np.sum((2 * np.arange(1, len(ordered) + 1) - len(ordered) - 1) * ordered)
            / (len(ordered) * ordered.sum())
        )
        top_count = max(1, math.ceil(0.10 * len(ordered)))
        top_share = float(ordered[-top_count:].sum() / ordered.sum())
        herfindahl = float(np.square(ordered / ordered.sum()).sum())
    else:
        gini = top_share = herfindahl = 0.0
    concentration = {
        "schema": "certvic.cvpr2027.failure_concentration.v1",
        "items_with_at_least_one_model_failure": len(values),
        "total_model_item_failures": int(values.sum()) if values.size else 0,
        "gini": gini,
        "top_10_percent_item_failure_share": top_share,
        "herfindahl_index": herfindahl,
        "analysis_class": "EXPLORATORY_NOT_PRIMARY",
        "paper_evidence": False,
    }
    influence.sort(key=lambda row: row["absolute_influence"], reverse=True)
    return summary, leave_out, influence, concentration


def run(output_root: Path = REPORT_ROOT) -> dict[str, Any]:
    started = time.perf_counter()
    analysis = output_root / "analysis"
    tables = output_root / "tables"
    evidence = output_root / "evidence"
    output_paths: list[Path] = []
    relevant_tasks = read_jsonl(RELEVANT_TASKS)
    irrelevant_tasks = read_jsonl(IRRELEVANT_TASKS)
    if len(relevant_tasks) != 91 or len(irrelevant_tasks) != 94:
        raise ValueError("genuine pilot task cardinalities no longer match 91/94")
    outcomes: dict[str, dict[str, list[dict[str, Any]]]] = {}
    metrics = []
    ablation_rows = []
    certificates = []
    for provider, paths in PROVIDER_FILES.items():
        relevant = build_item_outcomes(RELEVANT_TASKS, paths["relevant"], endpoint="relevant")
        irrelevant = build_item_outcomes(
            IRRELEVANT_TASKS, paths["irrelevant"], endpoint="irrelevant"
        )
        outcomes[provider] = {"relevant": relevant, "irrelevant": irrelevant}
        metric, ablations = _metric_row(provider, relevant, irrelevant)
        metrics.append(metric)
        for name, decision in ablations.items():
            ablation_rows.append(
                {
                    "model": provider,
                    "ablation": name,
                    "decision": decision,
                    "status": (
                        "BLOCKED_NO_GENUINE_HUMAN_FILTER"
                        if name == "with_genuine_human_validity_filter"
                        else "COMPUTED"
                    ),
                    "analysis_class": "RETROSPECTIVE_DIAGNOSTIC",
                }
            )
        relevant_endpoint = [
            bool(row["semantic_update_success"])
            for row in relevant
            if row["required_change"] == "change"
        ]
        irrelevant_endpoint = [bool(row["irrelevant_flip"]) for row in irrelevant]
        certificates.append(
            compute_certificate(
                model=provider,
                relevant_outcomes=relevant_endpoint,
                irrelevant_flip_outcomes=irrelevant_endpoint,
                missing_count=sum(bool(row["missing"]) for row in relevant + irrelevant),
                parse_failure_count=sum(not bool(row["parse_ok"]) for row in relevant + irrelevant),
                evidence_class="HISTORICAL_PILOT_RETROSPECTIVE_DIAGNOSTIC",
                artifact_hashes={
                    "relevant_tasks": sha256_file(RELEVANT_TASKS),
                    "irrelevant_tasks": sha256_file(IRRELEVANT_TASKS),
                    "relevant_predictions": sha256_file(PROVIDER_FILES[provider]["relevant"]),
                    "irrelevant_predictions": sha256_file(PROVIDER_FILES[provider]["irrelevant"]),
                },
                genuine_human_review=False,
                prospective=False,
            )
        )
    rankings = _rankings(metrics)
    ranking_orders = {
        metric: [
            row["model"]
            for row in sorted(
                (item for item in rankings if item["metric"] == metric),
                key=lambda item: item["rank"],
            )
        ]
        for metric in sorted({row["metric"] for row in rankings})
    }
    unique_orders = {tuple(value) for value in ranking_orders.values()}
    decision_vectors = {
        row["model"]: {
            key: row[key]
            for key in [
                "point_estimate_joint_decision",
                "standard_exact_ci_joint_decision",
                "bootstrap_joint_decision",
                "confidence_sequence_joint_decision",
                "multiplicity_corrected_joint_decision",
            ]
        }
        for row in metrics
    }
    reversals = {
        "schema": "certvic.cvpr2027.pilot_decision_reversals.v1",
        "ranking_reversal_found": len(unique_orders) > 1,
        "ranking_orders": ranking_orders,
        "decision_vectors": decision_vectors,
        "pass_fail_reversal_found": any(
            len(set(vector.values())) > 1 for vector in decision_vectors.values()
        ),
        "analysis_class": "RETROSPECTIVE_DIAGNOSTIC",
        "paper_evidence": False,
    }
    pairwise, disagreement, intersection = pairwise_comparisons(outcomes)
    heterogeneity, leave_out, influence, concentration = heterogeneity_analysis(outcomes)
    output_paths.extend(
        [
            write_csv(analysis / "pilot_baseline_metrics.csv", metrics),
            write_csv(analysis / "pilot_model_rankings.csv", rankings),
            write_json(analysis / "pilot_decision_reversals.json", reversals),
            write_csv(analysis / "pilot_component_ablations.csv", ablation_rows),
            write_csv(analysis / "pilot_pairwise_comparisons.csv", pairwise),
            write_csv(analysis / "pairwise_disagreement_matrix.csv", disagreement),
            write_json(analysis / "three_way_intersection_counts.json", intersection),
            write_csv(analysis / "heterogeneity_summary.csv", heterogeneity),
            write_csv(analysis / "leave_one_group_out.csv", leave_out),
            write_csv(analysis / "influence_items.csv", influence),
            write_json(analysis / "failure_concentration.json", concentration),
            write_csv(tables / "baseline_ablation_table.csv", metrics),
            write_csv(tables / "model_pairwise_table.csv", pairwise),
            write_csv(tables / "heterogeneity_table.csv", heterogeneity),
        ]
    )
    output_paths.extend(write_certificate_outputs(certificates, evidence))
    manifest = artifact_manifest(output_paths)
    output_paths.append(write_json(analysis / "PILOT_ANALYSIS_ARTIFACT_MANIFEST.json", manifest))
    return {
        "status": "COMPLETE",
        "runtime_seconds": time.perf_counter() - started,
        "inputs": {
            "intervention_items": len(relevant_tasks),
            "specificity_items": len(irrelevant_tasks),
            "models": sorted(PROVIDER_FILES),
        },
        "metrics": metrics,
        "ranking_reversal_found": reversals["ranking_reversal_found"],
        "pass_fail_reversal_found": reversals["pass_fail_reversal_found"],
        "outputs": [path.relative_to(REPO).as_posix() for path in output_paths],
        "evidence_class": "RETROSPECTIVE_DIAGNOSTIC",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPORT_ROOT)
    args = parser.parse_args(argv)
    print(run(args.output_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
