"""Guarded post-run analyses for specificity, Main, and second-domain studies."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from certvic.cvpr.statistics import exact_mcnemar, holm_adjust, specificity_decision
from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.primary_endpoint import score_item, summarize_items, two_gate_certificate
from certvic.cvpr.task_schema import require_task_matrix


def _pairs(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        item_id, variant = str(row["item_id"]), str(row["variant"])
        if variant in result[item_id]:
            raise ValueError(f"duplicate row for {item_id}/{variant}")
        result[item_id][variant] = row
    if any(set(pair) != {"original", "edited"} for pair in result.values()):
        raise ValueError("every analysis item must have original and edited rows")
    return dict(result)


def _flip(pair: dict[str, dict[str, Any]], *, missing_as_failure: bool) -> bool | None:
    original, edited = pair["original"], pair["edited"]
    parsed = original.get("parse_status") == edited.get("parse_status") == "PARSE_OK"
    if not parsed:
        return True if missing_as_failure else None
    return original.get("parsed_response") != edited.get("parsed_response")


def specificity_analysis(
    provider_rows: dict[str, list[dict[str, Any]]],
    tasks: list[dict[str, Any]],
    *,
    family_alpha: float = 0.05,
    threshold: float = 0.10,
    valid_item_ids: set[str] | None = None,
) -> dict[str, Any]:
    providers = sorted(provider_rows)
    per_alpha = family_alpha / len(providers)
    task_map = {str(task["item_id"]): task for task in tasks}
    provider_results: dict[str, Any] = {}
    flip_vectors: dict[str, dict[str, bool]] = {}
    for provider in providers:
        pairs = _pairs(provider_rows[provider])
        if set(pairs) != set(task_map):
            raise ValueError(f"{provider}: task identity differs from frozen manifest")
        included = sorted(set(pairs) & valid_item_ids) if valid_item_ids is not None else sorted(pairs)
        raw = [_flip(pairs[item_id], missing_as_failure=False) for item_id in included]
        primary = [_flip(pairs[item_id], missing_as_failure=True) for item_id in included]
        vector = {item_id: bool(value) for item_id, value in zip(included, primary, strict=True)}
        flip_vectors[provider] = vector
        strata: dict[str, Any] = {}
        for field in ("perturbation_family", "category", "target_size_stratum", "target_position_stratum"):
            groups: dict[str, list[bool]] = defaultdict(list)
            for item_id in included:
                groups[str(task_map[item_id].get(field, "unknown"))].append(vector[item_id])
            strata[field] = {name: {"items": len(values), "flips": sum(values),
                                    "rate": sum(values) / len(values)}
                             for name, values in sorted(groups.items())}
        provider_results[provider] = {
            "primary_missing_as_failure": specificity_decision(
                sum(primary), len(primary), alpha=per_alpha, threshold=threshold
            ),
            "raw_observed": {
                "parsed_pairs": sum(value is not None for value in raw),
                "flips": sum(value is True for value in raw),
                "rate": (sum(value is True for value in raw) / sum(value is not None for value in raw)
                         if any(value is not None for value in raw) else None),
            },
            "parse_failure_pairs": sum(value is None for value in raw),
            "strata": strata,
        }
    comparisons: list[dict[str, Any]] = []
    p_values: list[float] = []
    for left_index, left in enumerate(providers):
        for right in providers[left_index + 1:]:
            ids = sorted(flip_vectors[left])
            discordant_left = sum(flip_vectors[left][item] and not flip_vectors[right][item]
                                  for item in ids)
            discordant_right = sum(flip_vectors[right][item] and not flip_vectors[left][item]
                                   for item in ids)
            p_value = exact_mcnemar(discordant_left, discordant_right)
            p_values.append(p_value)
            comparisons.append({
                "left": left,
                "right": right,
                "risk_difference": (sum(flip_vectors[left].values())
                                    - sum(flip_vectors[right].values())) / len(ids),
                "discordant_left_only": discordant_left,
                "discordant_right_only": discordant_right,
                "exact_mcnemar_p": p_value,
            })
    for comparison, adjusted in zip(comparisons, holm_adjust(p_values), strict=True):
        comparison["holm_adjusted_p"] = adjusted
    passes = [value["primary_missing_as_failure"]["pass"] for value in provider_results.values()]
    return {
        "schema": "certvic.cvpr.specificity_analysis.v1",
        "providers": provider_results,
        "pairwise": comparisons,
        "simultaneous_decision": "ALL_MODELS_PASS" if all(passes) else "ONE_OR_MORE_MODELS_FAIL",
        "per_model_alpha": per_alpha,
        "human_validity_filter_applied": valid_item_ids is not None,
        "paper_evidence": False,
    }


def main_study_analysis(
    provider_rows: dict[str, list[dict[str, Any]]],
    tasks: list[dict[str, Any]],
    *,
    policy_path: str | None = None,
) -> dict[str, Any]:
    del policy_path  # V11 gap certification is deprecated for prospective execution.
    tasks = require_task_matrix(tasks)
    task_map = {str(task["task_id"]): task for task in tasks}
    results: dict[str, Any] = {}
    for provider, rows in sorted(provider_rows.items()):
        pairs = _pairs(rows)
        if set(pairs) != set(task_map):
            raise ValueError(f"{provider}: prediction task universe differs from canonical tasks")
        metrics: list[dict[str, Any]] = []
        for item_id, task in task_map.items():
            pair = pairs[item_id]
            original, edited = pair["original"], pair["edited"]
            if any(row.get("task_hash") != task["task_hash"] for row in (original, edited)):
                raise ValueError(f"{provider}/{item_id}: prediction task hash mismatch")
            scored = score_item(
                original_gold=task["original_expected_answer"],
                edited_gold=task["edited_expected_answer"],
                original_prediction=original.get("parsed_response"),
                edited_prediction=edited.get("parsed_response"),
                required_change=task["required_change"] is True,
                original_parse_ok=original["parse_status"] == "PARSE_OK",
                edited_parse_ok=edited["parse_status"] == "PARSE_OK",
            )
            scored["family"] = str(task.get("semantic_edit_family") or task.get(
                "control_edit_family", "unknown"
            ))
            metrics.append(scored)
        summary = summarize_items(metrics)
        summary["n"] = summary["items"]
        summary["original_correct_rate"] = summary["original_accuracy"]
        summary["edited_correct_rate"] = summary["edited_accuracy"]
        summary["spurious_flip_rate"] = summary["irrelevant_flip_rate"]
        summary["parse_failure_rate"] = sum(not row["parse_ok"] for row in metrics) / len(metrics)
        summary["by_task_family"] = {
            family: {"n": count}
            for family, count in Counter(row["family"] for row in metrics).items()
        }
        summary["control_edit"] = {"spurious_flip_rate": summary["irrelevant_flip_rate"]}
        if summary["relevant_items"] and summary["irrelevant_items"]:
            certificate = two_gate_certificate(
                metrics,
                tau_update=0.50,
                tau_spurious=0.10,
                responsiveness_alpha=0.008333333333333333,
                specificity_alpha=0.008333333333333333,
            )
        else:
            certificate = {
                "schema": "certvic.confirmatory.two_gate_certificate.v1",
                "decision": "NOT_EVALUABLE",
                "reason": "TWO_GATE_CERTIFICATION_REQUIRES_RELEVANT_AND_IRRELEVANT_STRATA",
                "relevant_items": summary["relevant_items"],
                "irrelevant_items": summary["irrelevant_items"],
                "paper_evidence": False,
            }
        results[provider] = {
            "summary": summary,
            "primary_two_gate_certificate": certificate,
            "legacy_gap_certification": {
                "status": "DEPRECATED_NOT_FOR_EXECUTION",
                "reason": "The old accuracy-minus-answer-change gap can reward never-updating models.",
            },
        }
    return {"schema": "certvic.cvpr.main_analysis.v2", "providers": results,
            "paper_evidence": False}


def second_domain_decision(
    analysis: dict[str, Any],
    *,
    edit_success: float,
    human_valid: float,
    detectability_auc: float,
) -> dict[str, Any]:
    parse_rates = [1 - value["summary"]["parse_failure_rate"]
                   for value in analysis["providers"].values()]
    gates = {
        "edit_success_gte_0_80": edit_success >= 0.80,
        "human_valid_gte_0_85": human_valid >= 0.85,
        "parse_completeness_gte_0_95": bool(parse_rates) and min(parse_rates) >= 0.95,
        "symmetric_detectability_auc_lte_0_80": detectability_auc <= 0.80,
    }
    return {"gates": gates, "decision": "EXPAND_TO_POWERED_CONFIRMATION" if all(gates.values())
            else "STOP_OR_REVISE", "domain_interaction_status": "REQUIRES_PRIMARY_DOMAIN_COMPARISON",
            "paper_evidence": False}


def human_aware_analysis(
    provider_rows: dict[str, list[dict[str, Any]]],
    tasks: list[dict[str, Any]],
    *,
    final_inclusion: dict[str, Any],
    agreement: dict[str, Any],
    study_kind: str,
) -> dict[str, Any]:
    """Produce raw and adjudicated-filtered analyses with explicit exclusions."""
    if final_inclusion.get("status") != "FINAL_INCLUSION_VALIDATED":
        raise ValueError("analysis requires a validated final inclusion manifest")
    if agreement.get("rater_identities_distinct") is not True:
        raise ValueError("analysis requires agreement from two distinct raters")
    task_ids = {str(task["item_id"]) for task in tasks}
    ledger = final_inclusion.get("ledger")
    if not isinstance(ledger, list) or not ledger:
        raise ValueError("analysis requires the complete final review ledger, not included IDs only")
    if final_inclusion.get("final_ledger_sha256") != sha256_bytes(canonical_json_bytes(ledger)):
        raise ValueError("final review ledger hash mismatch")
    ledger_ids = {str(row.get("item_id", "")) for row in ledger}
    if ledger_ids != task_ids or len(ledger_ids) != len(ledger):
        raise ValueError("final review ledger must contain every task exactly once")
    included = {str(row["item_id"]) for row in ledger if row.get("final_inclusion") is True}
    if not included or not included <= task_ids:
        raise ValueError("final inclusion is empty or references unknown task IDs")
    excluded = sorted(task_ids - included)
    filtered_rows = {
        provider: [row for row in rows if str(row["item_id"]) in included]
        for provider, rows in provider_rows.items()
    }
    filtered_tasks = [task for task in tasks if str(task["item_id"]) in included]
    if study_kind == "specificity_confirmatory_cvpr":
        raw = specificity_analysis(provider_rows, tasks)
        filtered = specificity_analysis(provider_rows, tasks, valid_item_ids=included)
    elif study_kind in {"main_study_cvpr", "second_domain_cvpr"}:
        raw = main_study_analysis(provider_rows, tasks)
        filtered = main_study_analysis(filtered_rows, filtered_tasks)
    else:
        raise ValueError(f"unsupported study kind: {study_kind}")
    return {
        "schema": "certvic.cvpr.human_aware_analysis.v1",
        "study": study_kind,
        "raw_analysis": raw,
        "adjudicated_filtered_analysis": filtered,
        "included_item_ids": sorted(included),
        "excluded_item_ids": excluded,
        "exclusion_reason": "FAILED_OR_EXCLUDED_BY_FINAL_BLINDED_VALIDITY_REVIEW",
        "review_ledger": ledger,
        "exclusion_ledger": [row for row in ledger if row.get("final_inclusion") is not True],
        "human_review": {
            "included": len(included), "excluded": len(excluded),
            "primary_agreement_statistic": agreement.get("primary_statistic"),
            "gwet_ac1": agreement.get("gwet_ac1"),
            "rater_identities_distinct": True,
            "packet_hashes_verified": final_inclusion.get("packet_hashes_verified"),
            "rater_artifact_hashes": final_inclusion.get("raw_rater_sha256"),
        },
        "paper_evidence": False,
        "paper_promotion_status": "REQUIRES_SEPARATE_CLAIM_GATE",
    }


def write_human_aware_artifacts(out_dir: str | Path, result: dict[str, Any]) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "human_aware_analysis.json": json.dumps(result, indent=2, sort_keys=True) + "\n",
        "inclusion_exclusion.json": json.dumps({
            "included_item_ids": result["included_item_ids"],
            "excluded_item_ids": result["excluded_item_ids"],
            "exclusion_reason": result["exclusion_reason"],
        }, indent=2, sort_keys=True) + "\n",
        "agreement_adjudication_summary.json": json.dumps(result["human_review"], indent=2,
                                                            sort_keys=True) + "\n",
    }
    for name, text in artifacts.items():
        (out / name).write_text(text, encoding="utf-8")
    hashes = {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
              for name in sorted(artifacts)}
    lineage = {
        "schema": "certvic.cvpr.analysis_lineage.v1",
        "artifacts": hashes,
        "source_roles": ["canonical_model_outputs", "two_raw_rater_sheets",
                         "agreement_report", "adjudication", "final_inclusion"],
        "paper_evidence": False,
    }
    (out / "analysis_lineage.json").write_text(
        json.dumps(lineage, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"status": "HUMAN_AWARE_ARTIFACTS_WRITTEN", "files": 4,
            "artifact_hashes": hashes, "paper_evidence": False}


def outcome_branch(specificity: dict[str, Any], *, human_invalidation_rate: float) -> dict[str, Any]:
    if human_invalidation_rate > 0.15:
        branch = "HIGH_HUMAN_INVALIDATION"
    else:
        decisions = {provider: value["primary_missing_as_failure"]["pass"]
                     for provider, value in specificity["providers"].items()}
        failures = [provider for provider, passed in decisions.items() if not passed]
        if not failures:
            branch = "ALL_MODELS_PASS"
        elif len(failures) > 1:
            branch = "MULTIPLE_MODELS_FAIL"
        elif failures == ["qwen2_5_vl_7b"]:
            branch = "QWEN_FAILS_AGAIN"
        else:
            branch = "INCONCLUSIVE_OR_OTHER_SINGLE_MODEL"
    return {"active_branch": branch, "activation_requires_validated_import": True,
            "paper_evidence": False}


def write_analysis_artifacts(out_dir: str | Path, result: dict[str, Any]) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "analysis.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    providers = result.get("providers", {})
    rows = []
    for provider, value in providers.items():
        metric = value.get("primary_missing_as_failure", value.get("summary", {}))
        rows.append({"provider": provider, **metric})
    fields = sorted({field for row in rows for field in row}) if rows else ["provider"]
    with (out / "model_comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    latex = ["\\begin{tabular}{lrr}", "\\toprule", "Model & Items & Rate \\\\", "\\midrule"]
    for row in rows:
        items = row.get("total", row.get("n", "--"))
        rate = row.get("observed_rate", row.get("raw_answer_change_rate", "--"))
        rendered = "--" if rate == "--" else f"{float(rate):.3f}"
        latex.append(f"{row['provider']} & {items} & {rendered} \\\\")
    latex.extend(["\\bottomrule", "\\end{tabular}"])
    (out / "model_comparison.tex").write_text("\n".join(latex) + "\n")
    (out / "reviewer_summary.md").write_text(
        "# Guarded analysis summary\n\n"
        "Generated only from contract-validated inputs. Human-review and claim gates remain "
        "independent; `paper_evidence=false` until those gates pass.\n",
        encoding="utf-8",
    )
    return {"status": "ARTIFACTS_WRITTEN", "files": 4, "paper_evidence": False}
