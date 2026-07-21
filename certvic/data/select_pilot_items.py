"""Deterministic pilot candidate selection."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

from certvic.data.label_policy import (
    allowed_edits_for_label,
    eligible_families_for_label,
    explain_label_decision,
    is_label_blocked,
    is_resolved,
    load_label_policy,
    policy_provenance,
    resolve_label_name,
)
from certvic.io import read_jsonl, write_json, write_jsonl
from certvic.schema import Domain, EditType, LicenseCategory, RequiredChange, TaskFamily


class PilotSelectionError(ValueError):
    """Raised when a pilot candidate set cannot satisfy selection constraints."""


DEFAULT_ALLOWED_TASK_FAMILIES = [
    TaskFamily.SUPPORT_STABILITY.value,
    TaskFamily.AFFORDANCE_REACHABILITY.value,
    TaskFamily.OCCLUSION_SAFETY.value,
    TaskFamily.CONTROL_IRRELEVANT.value,
]
DEFAULT_DOMAIN = Domain.HOUSEHOLD.value


def select_pilot_items(
    sources_path: str,
    masks_path: str,
    out_path: str,
    target: int = 200,
    seed: int = 0,
    min_mask_area_fraction: float | None = None,
    max_mask_area_fraction: float | None = None,
    summary_out: str | None = None,
    allow_duplicate_sources: bool = False,
    max_masks_per_source: int = 1,
    domains: list[str] | None = None,
    splits: list[str] | None = None,
    label_allowlist: list[int | str] | None = None,
    label_blocklist: list[int | str] | None = None,
    allowed_task_families: list[str] | None = None,
    require_target: bool = True,
    label_policy_path: str | None = None,
    per_family_target: dict[str, int] | None = None,
) -> dict:
    sources = read_jsonl(sources_path)
    masks = read_jsonl(masks_path)
    if target <= 0:
        raise PilotSelectionError("target must be positive")
    if max_masks_per_source <= 0:
        raise PilotSelectionError("max_masks_per_source must be positive")

    policy = load_label_policy(label_policy_path) if label_policy_path else None
    allowed_families = _normalize_allowed_families(allowed_task_families)
    allowed_domains = {str(value) for value in domains or []}
    allowed_splits = {str(value) for value in splits or []}
    allow_labels = _normalize_label_filter(label_allowlist)
    block_labels = _normalize_label_filter(label_blocklist)

    source_by_id: dict[str, dict] = {}
    duplicate_sources: set[str] = set()
    for source in sources:
        source_id = source.get("source_id")
        if not source_id:
            continue
        if source_id in source_by_id:
            duplicate_sources.add(str(source_id))
            continue
        source_by_id[str(source_id)] = source

    rejected = {
        "duplicate_source_id": len(duplicate_sources),
        "missing_source": 0,
        "missing_mask": 0,
        "mask_area_too_small": 0,
        "mask_area_too_large": 0,
        "invalid_bbox": 0,
        "split_filtered": 0,
        "domain_filtered": 0,
        "label_not_allowed": 0,
        "label_blocked": 0,
        "label_policy_blocked": 0,
        "label_policy_no_eligible_family": 0,
        "source_limit": 0,
    }
    unresolved_label_ids: set[str] = set()

    mask_by_source: dict[str, list[dict]] = defaultdict(list)
    candidates: list[dict] = []
    for mask in sorted(masks, key=lambda item: (str(item.get("source_id", "")), str(item.get("mask_id", "")))):
        source_id = str(mask.get("source_id") or "")
        source = source_by_id.get(source_id)
        if source is None:
            if source_id:
                rejected["missing_source"] += 1
            continue
        mask_by_source[source_id].append(mask)
        rejection_reason = _mask_filter_rejection(
            source,
            mask,
            min_mask_area_fraction=min_mask_area_fraction,
            max_mask_area_fraction=max_mask_area_fraction,
            domains=allowed_domains,
            splits=allowed_splits,
            label_allowlist=allow_labels,
            label_blocklist=block_labels,
        )
        if rejection_reason:
            rejected[rejection_reason] += 1
            continue
        if policy is not None:
            label_id = mask.get("label_id")
            if not is_resolved(policy, label_id):
                unresolved_label_ids.add(str(label_id))
            if is_label_blocked(policy, label_id):
                rejected["label_policy_blocked"] += 1
                continue
            eligible = [family for family in eligible_families_for_label(policy, label_id) if family in allowed_families]
            if not eligible:
                rejected["label_policy_no_eligible_family"] += 1
                continue
            candidate = _candidate_record(source, mask, eligible)
            candidate = _apply_label_policy(candidate, policy, label_id)
            candidates.append(candidate)
        else:
            candidates.append(_candidate_record(source, mask, allowed_families))

    for source_id in source_by_id:
        if not mask_by_source.get(source_id):
            rejected["missing_mask"] += 1

    effective_max_masks_per_source = max_masks_per_source if allow_duplicate_sources else 1
    selected, source_limit_rejections = _balanced_sample(
        candidates,
        target=target,
        seed=seed,
        max_masks_per_source=effective_max_masks_per_source,
    )
    rejected["source_limit"] += source_limit_rejections
    selected = _with_selection_ranks(selected)

    warnings: list[str] = []
    if len(selected) < target:
        warnings.append(
            f"target_count_not_met: requested {target}, selected {len(selected)} from "
            f"{len(candidates)} valid candidates"
        )
    by_family = _count_by(selected, "task_family")
    if per_family_target:
        for family, family_target in sorted(per_family_target.items()):
            have = by_family.get(family, 0)
            if have < int(family_target):
                warnings.append(
                    f"family_target_not_met: {family} requested {family_target}, selected {have}"
                )

    write_jsonl(out_path, selected)
    summary = {
        "selected": len(selected),
        "target": target,
        "seed": seed,
        "valid_candidates": len(candidates),
        "source_records": len(sources),
        "mask_records": len(masks),
        "unique_source_records": len(source_by_id),
        "rejected": rejected,
        "by_task_family": _count_by(selected, "task_family"),
        "by_domain": _count_by(selected, "domain"),
        "by_split": _count_by(selected, "split"),
        "min_mask_area_fraction": min_mask_area_fraction,
        "max_mask_area_fraction": max_mask_area_fraction,
        "allow_duplicate_sources": allow_duplicate_sources,
        "max_masks_per_source": max_masks_per_source,
        "effective_max_masks_per_source": effective_max_masks_per_source,
        "domains": sorted(allowed_domains),
        "splits": sorted(allowed_splits),
        "label_allowlist": sorted(allow_labels),
        "label_blocklist": sorted(block_labels),
        "allowed_task_families": allowed_families,
        "per_family_target": dict(sorted(per_family_target.items())) if per_family_target else None,
        "warnings": warnings,
        "evidence_status": "CANDIDATE_ONLY",
        "selection_path": out_path,
    }
    if policy is not None:
        summary.update(policy_provenance(policy))
        summary["unresolved_label_count"] = len(unresolved_label_ids)
        summary["unresolved_label_ids"] = sorted(unresolved_label_ids)
        if not policy.get("verified"):
            warnings.append("label_policy_unverified: confirm label map before evidence runs")
    summary_path = summary_out or str(Path(out_path).with_name("selection_summary.json"))
    write_json(summary_path, summary)
    if warnings and require_target:
        raise PilotSelectionError(
            f"Not enough valid pilot candidates: requested {target}, selected {len(selected)}. "
            f"See {summary_path} for rejection counts and warnings."
        )
    return summary


def _mask_filter_rejection(
    source: dict,
    mask: dict,
    min_mask_area_fraction: float | None,
    max_mask_area_fraction: float | None,
    domains: set[str],
    splits: set[str],
    label_allowlist: set[str],
    label_blocklist: set[str],
) -> str | None:
    if not _valid_bbox(mask.get("bbox_xyxy")):
        return "invalid_bbox"
    area = _mask_area(mask)
    if min_mask_area_fraction is not None and area is not None and area < min_mask_area_fraction:
        return "mask_area_too_small"
    if max_mask_area_fraction is not None and area is not None and area > max_mask_area_fraction:
        return "mask_area_too_large"
    split = _candidate_split(source, mask)
    if splits and split not in splits:
        return "split_filtered"
    domain = _candidate_domain(source, mask)
    if domains and domain not in domains:
        return "domain_filtered"
    label_values = _candidate_label_values(mask)
    if label_allowlist and not (label_values & label_allowlist):
        return "label_not_allowed"
    if label_blocklist and label_values & label_blocklist:
        return "label_blocked"
    return None


def _valid_bbox(value) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    if any(not isinstance(coord, int) or coord < 0 for coord in value):
        return False
    x1, y1, x2, y2 = value
    return x2 > x1 and y2 > y1


def _mask_area(mask: dict) -> float | None:
    for key in ["mask_area_fraction", "area_fraction"]:
        if key in mask and mask[key] is not None:
            return float(mask[key])
    metadata = mask.get("metadata")
    if isinstance(metadata, dict):
        for key in ["mask_area_fraction", "area_fraction"]:
            if key in metadata and metadata[key] is not None:
                return float(metadata[key])
    return None


def _candidate_record(source: dict, mask: dict, allowed_families: list[str]) -> dict:
    source_id = str(source["source_id"])
    mask_id = str(mask["mask_id"])
    family = _candidate_family(source, mask, allowed_families)
    edit_type = _proposed_edit_type(family, mask)
    required_change = _proposed_required_change(family, edit_type)
    label_id = mask.get("label_id")
    label_name = str(mask.get("object_label") or mask.get("label_name") or f"label_{label_id}")
    image_path = _source_image_pointer(source)
    release_mode, license_posture = _release_posture(source)
    return {
        "candidate_id": _candidate_id(source_id, mask_id),
        "source_id": source_id,
        "image_path": image_path,
        "source_url_or_pointer": source.get("source_url_or_pointer"),
        "local_path": source.get("local_path"),
        "mask_id": mask_id,
        "mask_path": mask.get("mask_path"),
        "label_id": label_id,
        "label_name": label_name,
        "object_label": label_name,
        "bbox": mask.get("bbox_xyxy"),
        "bbox_xyxy": mask.get("bbox_xyxy"),
        "mask_area_fraction": _mask_area(mask),
        "task_family": family,
        "proposed_task_family": family,
        "domain": _candidate_domain(source, mask),
        "split": _candidate_split(source, mask),
        "proposed_edit_type": edit_type,
        "edit_type": edit_type,
        "proposed_required_change": required_change,
        "required_change": required_change,
        "selection_reason": "passed_source_bbox_area_domain_split_label_filters",
        "release_mode": release_mode,
        "license_posture": license_posture,
        "license_category": source.get("license_category", LicenseCategory.UNKNOWN.value),
        "redistribution_allowed": bool(source.get("redistribution_allowed", False)),
        "evidence_status": "CANDIDATE_ONLY",
        "source_record": source,
        "mask_record": mask,
    }


def _apply_label_policy(candidate: dict, policy: dict, label_id) -> dict:
    """Annotate a candidate with policy decisions and enforce an allowed edit type."""
    family = str(candidate["task_family"])
    allowed_edits = allowed_edits_for_label(policy, label_id)
    edit_type = str(candidate.get("proposed_edit_type") or candidate.get("edit_type"))
    if allowed_edits and edit_type not in allowed_edits:
        # Prefer a policy-allowed edit that is also compatible with the family default.
        edit_type = allowed_edits[0]
        candidate["proposed_edit_type"] = edit_type
        candidate["edit_type"] = edit_type
        candidate["proposed_required_change"] = _proposed_required_change(family, edit_type)
        candidate["required_change"] = candidate["proposed_required_change"]
    resolved_name = resolve_label_name(policy, label_id)
    candidate["label_name"] = resolved_name
    candidate["object_label"] = resolved_name
    candidate["label_resolved"] = is_resolved(policy, label_id)
    candidate["label_policy_decision"] = explain_label_decision(policy, label_id, family, edit_type)
    candidate["selection_reason"] = "passed_filters_and_label_policy"
    return candidate


def _candidate_family(source: dict, mask: dict, allowed_families: list[str]) -> str:
    for record in [mask, source]:
        for key in ["task_family", "family"]:
            value = record.get(key)
            if value and str(value) in allowed_families:
                return str(value)
        metadata = record.get("metadata")
        if isinstance(metadata, dict):
            for key in ["task_family", "family"]:
                value = metadata.get(key)
                if value and str(value) in allowed_families:
                    return str(value)
    label_id = mask.get("label_id")
    if isinstance(label_id, int):
        return allowed_families[label_id % len(allowed_families)]
    stable = sum(ord(char) for char in str(mask.get("mask_id", "")))
    return allowed_families[stable % len(allowed_families)]


def _candidate_domain(source: dict, mask: dict) -> str:
    return _first_metadata_value([mask, source], ["domain"]) or DEFAULT_DOMAIN


def _candidate_split(source: dict, mask: dict) -> str:
    value = _first_metadata_value([mask, source], ["split"])
    if value:
        return value
    joined = " ".join(
        str(value or "")
        for value in [
            source.get("source_id"),
            source.get("local_path"),
            source.get("source_url_or_pointer"),
            mask.get("annotation_path"),
            mask.get("mask_path"),
        ]
    ).lower()
    if "validation" in joined or "_val_" in joined or "/val" in joined:
        return "val"
    if "training" in joined or "_train_" in joined or "/train" in joined:
        return "train"
    return "unknown"


def _first_metadata_value(records: list[dict], keys: list[str]) -> str | None:
    for record in records:
        for key in keys:
            if record.get(key):
                return str(record[key])
        metadata = record.get("metadata")
        if isinstance(metadata, dict):
            for key in keys:
                if metadata.get(key):
                    return str(metadata[key])
    return None


def _candidate_label_values(mask: dict) -> set[str]:
    values = set()
    for key in ["label_id", "object_label", "label_name"]:
        value = mask.get(key)
        if value is not None:
            values.add(str(value))
    return values


def _normalize_label_filter(values: list[int | str] | None) -> set[str]:
    normalized: set[str] = set()
    for value in values or []:
        for part in str(value).split(","):
            stripped = part.strip()
            if stripped:
                normalized.add(stripped)
    return normalized


def _normalize_allowed_families(values: list[str] | None) -> list[str]:
    families = []
    valid = {family.value for family in TaskFamily}
    for value in values or DEFAULT_ALLOWED_TASK_FAMILIES:
        for part in str(value).split(","):
            stripped = part.strip()
            if not stripped:
                continue
            if stripped not in valid:
                raise PilotSelectionError(f"Unknown task family: {stripped}")
            families.append(stripped)
    deduped = list(dict.fromkeys(families))
    if not deduped:
        raise PilotSelectionError("allowed_task_families must not be empty")
    return deduped


def _proposed_edit_type(family: str, mask: dict) -> str:
    if mask.get("proposed_edit_type"):
        return str(mask["proposed_edit_type"])
    if family == TaskFamily.SUPPORT_STABILITY.value:
        return EditType.DISPLACE.value
    if family == TaskFamily.AFFORDANCE_REACHABILITY.value:
        return EditType.REMOVE.value
    if family == TaskFamily.OCCLUSION_SAFETY.value:
        return EditType.OCCLUDE.value
    if family == TaskFamily.CONTROL_IRRELEVANT.value:
        return EditType.CONTROL_IRRELEVANT.value
    return EditType.REMOVE.value


def _proposed_required_change(family: str, edit_type: str) -> str:
    if family in {TaskFamily.CONTROL_IRRELEVANT.value, TaskFamily.OCCLUSION_SAFETY.value}:
        return RequiredChange.NO_CHANGE.value
    if edit_type == EditType.CONTROL_IRRELEVANT.value:
        return RequiredChange.NO_CHANGE.value
    return RequiredChange.CHANGE.value


def _source_image_pointer(source: dict) -> str | None:
    for key in ["local_path", "image_path", "source_url_or_pointer"]:
        if source.get(key):
            return str(source[key])
    return None


def _release_posture(source: dict) -> tuple[str, dict]:
    category = str(source.get("license_category", LicenseCategory.UNKNOWN.value))
    redistribution_allowed = bool(source.get("redistribution_allowed", False))
    if category in {LicenseCategory.CC0.value, LicenseCategory.PUBLIC_DOMAIN.value}:
        release_mode = "pixel_release_ok" if redistribution_allowed else "recipe_only"
    elif category == LicenseCategory.CC_BY.value:
        release_mode = "pixel_release_ok" if redistribution_allowed and source.get("license_text") else "recipe_only"
    elif category in {LicenseCategory.RESEARCH_ONLY.value, LicenseCategory.POINTER_ONLY.value}:
        release_mode = "recipe_only"
    else:
        release_mode = "blocked_until_verified"
    return release_mode, {
        "license_category": category,
        "redistribution_allowed": redistribution_allowed,
        "release_mode": release_mode,
        "pixel_rehost_allowed": release_mode == "pixel_release_ok",
    }


def _candidate_id(source_id: str, mask_id: str) -> str:
    digest = hashlib.sha1(f"{source_id}|{mask_id}".encode("utf-8")).hexdigest()[:12]
    return f"candidate_{digest}"


def _balanced_sample(
    candidates: list[dict],
    target: int,
    seed: int,
    max_masks_per_source: int,
) -> tuple[list[dict], int]:
    rng = random.Random(seed)
    by_family: dict[str, list[dict]] = defaultdict(list)
    for candidate in candidates:
        by_family[candidate["task_family"]].append(candidate)
    for bucket in by_family.values():
        bucket.sort(key=lambda item: (str(item["source_id"]), str(item["mask_id"])))
        rng.shuffle(bucket)

    selected: list[dict] = []
    selected_keys: set[str] = set()
    selected_per_source: dict[str, int] = defaultdict(int)
    source_limit_rejections = 0
    families = sorted(by_family)
    while len(selected) < target:
        progressed = False
        for family in families:
            while by_family[family]:
                candidate = by_family[family].pop()
                key = str(candidate["candidate_id"])
                source_id = str(candidate["source_id"])
                if key in selected_keys:
                    continue
                if selected_per_source[source_id] >= max_masks_per_source:
                    source_limit_rejections += 1
                    continue
                selected.append(candidate)
                selected_keys.add(key)
                selected_per_source[source_id] += 1
                progressed = True
                break
            if len(selected) >= target:
                break
        if not progressed:
            break
    return selected, source_limit_rejections


def _with_selection_ranks(selected: list[dict]) -> list[dict]:
    ranked = []
    for rank, candidate in enumerate(selected):
        record = dict(candidate)
        record["selection_rank"] = rank
        ranked.append(record)
    return ranked


def _count_by(rows: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", required=True)
    parser.add_argument("--masks", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--target", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--min-mask-area-fraction", type=float)
    parser.add_argument("--max-mask-area-fraction", type=float)
    parser.add_argument("--summary-out")
    parser.add_argument("--allow-duplicate-sources", action="store_true")
    parser.add_argument("--max-masks-per-source", type=int, default=1)
    parser.add_argument("--domains", nargs="*")
    parser.add_argument("--splits", nargs="*")
    parser.add_argument("--label-allowlist", nargs="*")
    parser.add_argument("--label-blocklist", nargs="*")
    parser.add_argument("--allowed-task-families", nargs="*")
    parser.add_argument("--label-policy")
    parser.add_argument("--per-family-target-json")
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args(argv)
    per_family_target = json.loads(args.per_family_target_json) if args.per_family_target_json else None
    try:
        print(
            json.dumps(
                select_pilot_items(
                    args.sources,
                    args.masks,
                    args.out,
                    args.target,
                    args.seed,
                    min_mask_area_fraction=args.min_mask_area_fraction,
                    max_mask_area_fraction=args.max_mask_area_fraction,
                    summary_out=args.summary_out,
                    allow_duplicate_sources=args.allow_duplicate_sources,
                    max_masks_per_source=args.max_masks_per_source,
                    domains=args.domains,
                    splits=args.splits,
                    label_allowlist=args.label_allowlist,
                    label_blocklist=args.label_blocklist,
                    allowed_task_families=args.allowed_task_families,
                    require_target=not args.allow_partial,
                    label_policy_path=args.label_policy,
                    per_family_target=per_family_target,
                ),
                sort_keys=True,
            )
        )
    except PilotSelectionError as exc:
        raise SystemExit(f"Pilot selection failed: {exc}") from None


if __name__ == "__main__":
    main()
