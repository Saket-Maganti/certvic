"""ADE20K label policy: principled task-family / edit eligibility per label.

A label policy maps semantic label ids to the task families and edit types that
are *valid* for that label, plus a block reason for labels that should never be
manipulated (e.g. background "stuff" like sky or wall). Labels that are not in
the policy are treated as **unresolved** and receive a conservative fallback so
construct validity is never silently assumed for an unknown object.

This module performs no downloads, no GPU work, and no inference. The shipped
`configs/ade20k_label_policy.yaml` is an unverified template; callers must verify
the label map against their ADE20K version before making evidence claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from certvic.schema import EditType, TaskFamily

VALID_FAMILIES = {family.value for family in TaskFamily}
VALID_EDIT_TYPES = {edit.value for edit in EditType}

# Used when no policy file is supplied at all.
CONSERVATIVE_FALLBACK = {
    "unresolved_eligible_task_families": [TaskFamily.CONTROL_IRRELEVANT.value],
    "unresolved_allowed_edit_types": [EditType.CONTROL_IRRELEVANT.value],
    "unresolved_block_reason": None,
}


class LabelPolicyError(ValueError):
    """Raised when a label policy file cannot be parsed or is internally invalid."""


def _coerce_label_id(label_id: Any) -> int | None:
    if label_id is None:
        return None
    if isinstance(label_id, bool):  # guard: bool is an int subclass
        return None
    try:
        return int(label_id)
    except (TypeError, ValueError):
        return None


def _validate_list(values: Any, allowed: set[str], field: str, label_id: Any) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise LabelPolicyError(f"label {label_id}: {field} must be a list")
    cleaned: list[str] = []
    for value in values:
        text = str(value)
        if text not in allowed:
            raise LabelPolicyError(f"label {label_id}: unknown {field} value {text!r}")
        if text not in cleaned:
            cleaned.append(text)
    return cleaned


def load_label_policy(path: str | None) -> dict:
    """Load a label policy file into a normalized in-memory policy.

    Returns a dict with keys: version, verified, entries (by int label_id),
    fallback, policy_hash, source_path. Passing ``None`` yields an empty policy
    whose every lookup falls through to the conservative fallback.
    """
    if path is None:
        return {
            "version": "certvic.no_label_policy",
            "verified": False,
            "entries": {},
            "fallback": dict(CONSERVATIVE_FALLBACK),
            "policy_hash": _hash_payload({"version": "certvic.no_label_policy"}),
            "source_path": None,
        }
    policy_path = Path(path)
    if not policy_path.exists():
        raise LabelPolicyError(f"label policy file not found: {policy_path}")
    try:
        data = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise LabelPolicyError(f"could not parse label policy {policy_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LabelPolicyError(f"label policy {policy_path} must be a mapping")

    fallback = {**CONSERVATIVE_FALLBACK, **(data.get("defaults") or {})}
    fallback["unresolved_eligible_task_families"] = _validate_list(
        fallback.get("unresolved_eligible_task_families"), VALID_FAMILIES, "unresolved_eligible_task_families", "fallback"
    )
    fallback["unresolved_allowed_edit_types"] = _validate_list(
        fallback.get("unresolved_allowed_edit_types"), VALID_EDIT_TYPES, "unresolved_allowed_edit_types", "fallback"
    )

    entries: dict[int, dict] = {}
    for raw in data.get("labels") or []:
        label_id = _coerce_label_id(raw.get("label_id"))
        if label_id is None:
            raise LabelPolicyError(f"label entry missing a valid integer label_id: {raw!r}")
        if label_id in entries:
            raise LabelPolicyError(f"duplicate label_id in policy: {label_id}")
        families = _validate_list(raw.get("eligible_task_families"), VALID_FAMILIES, "eligible_task_families", label_id)
        edits = _validate_list(raw.get("allowed_edit_types"), VALID_EDIT_TYPES, "allowed_edit_types", label_id)
        block_reason = raw.get("block_reason")
        entries[label_id] = {
            "label_id": label_id,
            "label_name": str(raw.get("label_name") or f"ade20k_label_{label_id}"),
            "eligible_task_families": families,
            "allowed_edit_types": edits,
            "domain_tags": [str(tag) for tag in (raw.get("domain_tags") or [])],
            "block_reason": str(block_reason) if block_reason else None,
            "notes": str(raw.get("notes")) if raw.get("notes") else None,
        }

    return {
        "version": str(data.get("version") or "certvic.ade20k_label_policy.unversioned"),
        "verified": bool(data.get("verified", False)),
        "entries": entries,
        "fallback": fallback,
        "policy_hash": _hash_payload(data),
        "source_path": str(policy_path),
    }


def _entry(policy: dict, label_id: Any) -> dict | None:
    coerced = _coerce_label_id(label_id)
    if coerced is None:
        return None
    return policy.get("entries", {}).get(coerced)


def is_resolved(policy: dict, label_id: Any) -> bool:
    return _entry(policy, label_id) is not None


def resolve_label_name(policy: dict, label_id: Any) -> str:
    entry = _entry(policy, label_id)
    if entry is not None:
        return entry["label_name"]
    coerced = _coerce_label_id(label_id)
    return f"ade20k_label_{coerced}" if coerced is not None else "ade20k_label_unknown"


def is_label_blocked(policy: dict, label_id: Any) -> bool:
    entry = _entry(policy, label_id)
    if entry is not None:
        return entry["block_reason"] is not None
    return bool(policy.get("fallback", {}).get("unresolved_block_reason"))


def block_reason(policy: dict, label_id: Any) -> str | None:
    entry = _entry(policy, label_id)
    if entry is not None:
        return entry["block_reason"]
    return policy.get("fallback", {}).get("unresolved_block_reason")


def eligible_families_for_label(policy: dict, label_id: Any) -> list[str]:
    if is_label_blocked(policy, label_id):
        return []
    entry = _entry(policy, label_id)
    if entry is not None:
        return list(entry["eligible_task_families"])
    return list(policy.get("fallback", {}).get("unresolved_eligible_task_families", []))


def allowed_edits_for_label(policy: dict, label_id: Any) -> list[str]:
    if is_label_blocked(policy, label_id):
        return []
    entry = _entry(policy, label_id)
    if entry is not None:
        return list(entry["allowed_edit_types"])
    return list(policy.get("fallback", {}).get("unresolved_allowed_edit_types", []))


def is_family_eligible(policy: dict, label_id: Any, task_family: str) -> bool:
    return task_family in eligible_families_for_label(policy, label_id)


def is_edit_allowed(policy: dict, label_id: Any, edit_type: str) -> bool:
    return edit_type in allowed_edits_for_label(policy, label_id)


def explain_label_decision(policy: dict, label_id: Any, task_family: str | None = None, edit_type: str | None = None) -> dict:
    """Return a full, auditable explanation of a label's eligibility."""
    coerced = _coerce_label_id(label_id)
    resolved = is_resolved(policy, label_id)
    blocked = is_label_blocked(policy, label_id)
    families = eligible_families_for_label(policy, label_id)
    edits = allowed_edits_for_label(policy, label_id)
    reasons: list[str] = []
    if blocked:
        reasons.append(f"blocked: {block_reason(policy, label_id)}")
    if not resolved:
        reasons.append("unresolved_label_conservative_fallback")
    if task_family is not None and not blocked and task_family not in families:
        reasons.append(f"family_not_eligible: {task_family}")
    if edit_type is not None and not blocked and edit_type not in edits:
        reasons.append(f"edit_not_allowed: {edit_type}")
    eligible = bool(not blocked and families and edits)
    if task_family is not None:
        eligible = eligible and task_family in families
    if edit_type is not None:
        eligible = eligible and edit_type in edits
    return {
        "label_id": coerced,
        "label_name": resolve_label_name(policy, label_id),
        "resolved": resolved,
        "blocked": blocked,
        "block_reason": block_reason(policy, label_id),
        "eligible_task_families": families,
        "allowed_edit_types": edits,
        "eligible": eligible,
        "checked_task_family": task_family,
        "checked_edit_type": edit_type,
        "reasons": reasons or ["eligible"],
        "policy_version": policy.get("version"),
        "policy_hash": policy.get("policy_hash"),
        "policy_verified": policy.get("verified", False),
    }


def policy_provenance(policy: dict) -> dict:
    return {
        "label_policy_version": policy.get("version"),
        "label_policy_hash": policy.get("policy_hash"),
        "label_policy_verified": policy.get("verified", False),
        "label_policy_source": policy.get("source_path"),
        "label_policy_entry_count": len(policy.get("entries", {})),
    }


def _hash_payload(data: Any) -> str:
    canonical = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()[:16]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Inspect an ADE20K label policy decision")
    parser.add_argument("--policy", required=True)
    parser.add_argument("--label-id", type=int, required=True)
    parser.add_argument("--task-family")
    parser.add_argument("--edit-type")
    args = parser.parse_args(argv)
    policy = load_label_policy(args.policy)
    print(json.dumps(explain_label_decision(policy, args.label_id, args.task_family, args.edit_type), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
