"""Prospective analysis-plan definitions."""

from __future__ import annotations

from certvic.providers.registry import OPEN_LOCAL_PROVIDERS


def default_analysis_plan(policy: dict) -> dict:
    return {
        "primary_estimand": "Delta = E[a_i] - E[C_i]",
        "primary_population": "human-reviewed real-image intervention pairs",
        "primary_model_set": sorted(OPEN_LOCAL_PROVIDERS),
        "primary_item_inclusion_rules": [
            "item validity certificate candidate eligible",
            "open-local provider predictions only",
            "one confirmatory item per source unless predeclared",
        ],
        "primary_stopping_rule": "anytime-valid CS may stop at compute exhaustion or crossing",
        "alpha": policy.get("alpha"),
        "gap_threshold": policy.get("gap_threshold"),
        "parse_failure_threshold": policy.get("parse_failure_max"),
        "control_spurious_flip_threshold": policy.get("control_spurious_flip_max"),
        "allowed_exploratory_analyses": [
            "by task family",
            "by domain",
            "by edit type",
            "failure gallery",
            "ablation summaries",
        ],
        "multiplicity_statement": "one primary endpoint; exploratory subgroups require correction for claims",
        "cluster_dependence_statement": "primary analysis caps confirmatory items per source and reports cluster diagnostics",
        "frozen_before_results": True,
        "post_result_modification": False,
        "evidence_status": "ANALYSIS_PLAN_LOCK_ONLY",
    }


def validate_analysis_plan(plan: dict) -> list[str]:
    errors: list[str] = []
    for key in ("primary_estimand", "primary_population", "primary_model_set", "alpha", "gap_threshold"):
        if not plan.get(key):
            errors.append(f"missing primary field: {key}")
    if not plan.get("frozen_before_results"):
        errors.append("analysis plan is not frozen before results")
    if plan.get("post_result_modification"):
        errors.append("post-result modification flagged")
    if "exploratory" in str(plan.get("primary_estimand", "")).lower():
        errors.append("exploratory-only analysis cannot be primary")
    return errors

