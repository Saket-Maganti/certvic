"""Certification policy gate.

A claim is certification-eligible only if the policy passes AND an anytime-valid
CS lower bound exceeds the gap threshold. CS unavailable => not certified. A
bootstrap CI is never certification.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from certvic.validation.claims import NON_EVIDENCE_STATUSES

DEFAULT_POLICY = {
    "alpha": 0.05,
    "gap_threshold": 0.05,
    "min_n_overall": 150,
    "min_n_by_family": 40,
    "parse_failure_max": 0.10,
    "control_spurious_flip_max": 0.10,
    "require_control_spurious_gate": True,
    "evidence_status_required": "HUMAN_REVIEWED_NON_EVIDENCE",
    "provider_type_disallowed": ["mock", "baseline"],
}

# Statuses that are at least as strong as HUMAN_REVIEWED_NON_EVIDENCE for gating.
_REVIEWED_OR_STRONGER = {"HUMAN_REVIEWED_NON_EVIDENCE", "EVIDENCE", "CERTIFIED"}


def load_certification_policy(path: str | None) -> dict:
    if not path or not Path(path).exists():
        return dict(DEFAULT_POLICY)
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {**DEFAULT_POLICY, **data}


def evaluate_certification_policy(summary: dict, certification: dict, policy: dict, evidence_context: dict | None = None) -> dict:
    """Return a structured pass/fail decision against the certification policy."""
    errors: list[str] = []
    context = evidence_context or {}

    n = int(summary.get("n") or 0)
    if n < int(policy["min_n_overall"]):
        errors.append(f"n_overall {n} < min_n_overall {policy['min_n_overall']}")

    by_family = summary.get("by_task_family") or {}
    for family, fam_summary in by_family.items():
        fam_n = int(fam_summary.get("n") or 0)
        if 0 < fam_n < int(policy["min_n_by_family"]):
            errors.append(f"family {family} n {fam_n} < min_n_by_family {policy['min_n_by_family']}")

    parse_fail = summary.get("parse_failure_rate")
    if parse_fail is not None and parse_fail > float(policy["parse_failure_max"]):
        errors.append(f"parse_failure_rate {parse_fail:.3f} > max {policy['parse_failure_max']}")

    control = summary.get("control_edit") or {}
    flip = control.get("spurious_flip_rate")
    if flip is None and bool(policy.get("require_control_spurious_gate", True)):
        errors.append("control_spurious_flip_rate missing; specificity gate is required")
    elif flip is not None and flip > float(policy["control_spurious_flip_max"]):
        errors.append(f"control_spurious_flip_rate {flip:.3f} > max {policy['control_spurious_flip_max']}")

    statuses = {str(s).upper() for s in context.get("evidence_statuses") or []}
    required = str(policy["evidence_status_required"]).upper()
    # Build the accepted-status set *locally*. Never mutate the module-level
    # _REVIEWED_OR_STRONGER: a single call with a custom evidence_status_required
    # would otherwise permanently widen the global allowlist, so a later call with
    # the default policy would accept a status it must reject (claim-gate leak).
    accepted = _REVIEWED_OR_STRONGER | {required}
    if not statuses:
        errors.append(f"missing evidence_status; required {required}")
    elif not (statuses & accepted):
        errors.append(f"no evidence_status meets required {required}; have {sorted(statuses)}")
    for status in sorted(statuses & NON_EVIDENCE_STATUSES):
        errors.append(f"non-evidence status present: {status}")

    provider_types = {str(p).lower() for p in context.get("provider_types") or []}
    disallowed = {str(p).lower() for p in policy.get("provider_type_disallowed") or []}
    bad = sorted(provider_types & disallowed)
    if bad:
        errors.append(f"disallowed provider types present: {bad}")
    if not provider_types:
        errors.append("missing provider_type")

    cs = certification.get("confidence_sequence") or {}
    lower = certification.get("lower_bound")
    if not cs.get("available"):
        errors.append("anytime-valid CS unavailable (bootstrap CI is never certification)")
    if lower is None:
        errors.append("missing CS lower bound")
    elif lower <= float(policy["gap_threshold"]):
        errors.append(f"CS lower bound {lower} does not exceed gap_threshold {policy['gap_threshold']}")

    return {
        "policy_passed": not errors,
        "errors": errors,
        "n_overall": n,
        "gap_threshold": policy["gap_threshold"],
        "alpha": policy["alpha"],
        "certified": not errors,
        "note": "Certification requires policy pass + available anytime-valid CS lower bound above threshold.",
    }
