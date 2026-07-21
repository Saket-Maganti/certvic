"""Plan ADE20K pilot edits without generating images."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from certvic.data.label_policy import (
    allowed_edits_for_label,
    eligible_families_for_label,
    is_label_blocked,
    load_label_policy,
    policy_provenance,
)
from certvic.io import read_jsonl, write_json, write_jsonl
from certvic.schema import EditType, RequiredChange, TaskFamily
from certvic.validation.leakage import check_path_no_leakage


DEFAULT_MIN_MASK_AREA_FRACTION = 0.01
DEFAULT_MAX_MASK_AREA_FRACTION = 0.40
DEFAULT_EDIT_TYPE_RATIOS = {
    EditType.REMOVE.value: 0.30,
    EditType.OCCLUDE.value: 0.25,
    EditType.DISPLACE.value: 0.30,
    EditType.CONTROL_IRRELEVANT.value: 0.15,
}

COMPATIBLE_EDIT_TYPES = {
    TaskFamily.SUPPORT_STABILITY.value: {EditType.REMOVE.value, EditType.DISPLACE.value},
    TaskFamily.AFFORDANCE_REACHABILITY.value: {EditType.REMOVE.value, EditType.DISPLACE.value},
    TaskFamily.OCCLUSION_SAFETY.value: {EditType.OCCLUDE.value},
    TaskFamily.CONTROL_IRRELEVANT.value: {EditType.CONTROL_IRRELEVANT.value},
}

REQUIRED_CHANGE_BY_FAMILY = {
    TaskFamily.SUPPORT_STABILITY.value: RequiredChange.CHANGE.value,
    TaskFamily.AFFORDANCE_REACHABILITY.value: RequiredChange.CHANGE.value,
    TaskFamily.OCCLUSION_SAFETY.value: RequiredChange.NO_CHANGE.value,
    TaskFamily.CONTROL_IRRELEVANT.value: RequiredChange.NO_CHANGE.value,
}


class EditPlanError(ValueError):
    """Raised when an edit plan cannot be written safely."""


def build_edit_plan(
    selection_path: str,
    out_path: str,
    summary_out: str,
    seed: int = 0,
    rejected_out: str | None = None,
    min_mask_area_fraction: float = DEFAULT_MIN_MASK_AREA_FRACTION,
    max_mask_area_fraction: float = DEFAULT_MAX_MASK_AREA_FRACTION,
    edit_type_ratios: dict[str, float] | None = None,
    label_policy_path: str | None = None,
) -> dict:
    selection = read_jsonl(selection_path)
    policy = load_label_policy(label_policy_path) if label_policy_path else None
    ratios = _normalize_ratios(edit_type_ratios or DEFAULT_EDIT_TYPE_RATIOS)
    rejected_path = rejected_out or str(Path(out_path).with_name("pilot_edit_plan_rejected.jsonl"))
    ordered = sorted(
        selection,
        key=lambda row: (
            int(row.get("selection_rank", 10**9)),
            str(row.get("source_id", "")),
            str(row.get("mask_id", "")),
        ),
    )

    planned: list[dict] = []
    rejected: list[dict] = []
    seen_edit_ids: set[str] = set()
    for index, candidate in enumerate(ordered):
        edit_type = _candidate_edit_type(candidate, seed, index, ratios)
        required_change = str(
            candidate.get("proposed_required_change")
            or candidate.get("required_change")
            or REQUIRED_CHANGE_BY_FAMILY.get(str(candidate.get("proposed_task_family") or candidate.get("task_family")), "")
        )
        edit_id = _edit_id(candidate, edit_type, seed)
        reasons = _feasibility_reasons(
            candidate,
            edit_id=edit_id,
            edit_type=edit_type,
            required_change=required_change,
            seen_edit_ids=seen_edit_ids,
            min_mask_area_fraction=min_mask_area_fraction,
            max_mask_area_fraction=max_mask_area_fraction,
            policy=policy,
        )
        if reasons:
            rejected.append(_rejected_record(candidate, edit_id, edit_type, required_change, reasons))
            continue
        planned_record = _planned_record(candidate, edit_id, edit_type, required_change, seed)
        planned.append(planned_record)
        seen_edit_ids.add(edit_id)

    write_jsonl(out_path, planned)
    write_jsonl(rejected_path, rejected)
    summary = {
        "selection_path": selection_path,
        "edit_plan_path": out_path,
        "rejected_path": rejected_path,
        "seed": seed,
        "input_candidates": len(selection),
        "planned": len(planned),
        "rejected": len(rejected),
        "by_edit_type": dict(sorted(Counter(row["edit_type"] for row in planned).items())),
        "rejection_reasons": _reason_counts(rejected),
        "rejections_by_label": _rejections_by(rejected, "label_id"),
        "rejections_by_family": _rejections_by(rejected, "attempted_task_family"),
        "rejections_by_edit_type": _rejections_by(rejected, "attempted_edit_type"),
        "min_mask_area_fraction": min_mask_area_fraction,
        "max_mask_area_fraction": max_mask_area_fraction,
        "edit_type_ratios": ratios,
        "evidence_status": "PLANNED_ONLY",
        "generation_status": "not_generated",
        "zero_cost": True,
        "edits_generated": False,
        "vlm_inference_run": False,
    }
    if policy is not None:
        summary.update(policy_provenance(policy))
    write_json(summary_out, summary)
    return summary


def _candidate_edit_type(candidate: dict, seed: int, index: int, ratios: dict[str, float]) -> str:
    proposed = candidate.get("proposed_edit_type") or candidate.get("edit_type")
    if proposed:
        return str(proposed)
    family = str(candidate.get("proposed_task_family") or candidate.get("task_family"))
    compatible = sorted(COMPATIBLE_EDIT_TYPES.get(family, set()))
    if not compatible:
        return EditType.REMOVE.value
    weighted: list[str] = []
    for edit_type, ratio in sorted(ratios.items()):
        if edit_type in compatible:
            weighted.extend([edit_type] * max(1, int(ratio * 100)))
    if not weighted:
        weighted = compatible
    rng = random.Random(f"{seed}|{index}|{candidate.get('source_id')}|{candidate.get('mask_id')}")
    return weighted[rng.randrange(len(weighted))]


def _feasibility_reasons(
    candidate: dict,
    edit_id: str,
    edit_type: str,
    required_change: str,
    seen_edit_ids: set[str],
    min_mask_area_fraction: float,
    max_mask_area_fraction: float,
    policy: dict | None = None,
) -> list[str]:
    reasons: list[str] = []
    if candidate.get("evidence_status") != "CANDIDATE_ONLY":
        reasons.append("candidate evidence_status must be CANDIDATE_ONLY")
    area = candidate.get("mask_area_fraction")
    if area is None:
        reasons.append("missing mask_area_fraction")
    else:
        area_value = float(area)
        if area_value < min_mask_area_fraction:
            reasons.append("mask area below minimum")
        if area_value > max_mask_area_fraction:
            reasons.append("mask area above maximum")
    if not _valid_bbox(candidate.get("bbox") or candidate.get("bbox_xyxy")):
        reasons.append("invalid bbox")

    image_path = candidate.get("image_path") or candidate.get("local_path") or candidate.get("source_url_or_pointer")
    if not image_path:
        reasons.append("missing image path or pointer")
    elif _requires_local_exists(str(image_path)) and not Path(str(image_path)).exists():
        reasons.append("local image path does not exist")

    family = str(candidate.get("proposed_task_family") or candidate.get("task_family") or "")
    compatible = COMPATIBLE_EDIT_TYPES.get(family)
    if not compatible:
        reasons.append("unknown task family")
    elif edit_type not in compatible:
        reasons.append("edit type incompatible with task family")

    expected_required_change = REQUIRED_CHANGE_BY_FAMILY.get(family)
    if expected_required_change is None:
        reasons.append("required_change cannot be checked for unknown task family")
    elif required_change != expected_required_change:
        reasons.append("required_change incompatible with task family")

    if not candidate.get("release_mode") or not candidate.get("license_posture"):
        reasons.append("source license/release posture not recorded")

    for warning in check_path_no_leakage(str(image_path or "")):
        reasons.append(f"source filename leakage: {warning}")

    planned_path = f"planned://pilot/{edit_id}"
    for warning in check_path_no_leakage(planned_path):
        reasons.append(f"planned filename leakage: {warning}")

    if policy is not None:
        label_id = candidate.get("label_id")
        if is_label_blocked(policy, label_id):
            reasons.append("label policy blocks this label")
        else:
            if family not in eligible_families_for_label(policy, label_id):
                reasons.append("label policy: family not eligible for label")
            if edit_type not in allowed_edits_for_label(policy, label_id):
                reasons.append("label policy: edit type not allowed for label")

    if edit_id in seen_edit_ids:
        reasons.append("duplicate edit_id")
    return reasons


def _planned_record(candidate: dict, edit_id: str, edit_type: str, required_change: str, seed: int) -> dict:
    family = str(candidate.get("proposed_task_family") or candidate.get("task_family"))
    domain = str(candidate.get("domain", "household"))
    bbox = candidate.get("bbox") or candidate.get("bbox_xyxy")
    area = candidate.get("mask_area_fraction")
    return {
        "edit_id": edit_id,
        "candidate_id": candidate.get("candidate_id"),
        "source_id": candidate["source_id"],
        "image_path": candidate.get("image_path"),
        "mask_id": candidate["mask_id"],
        "mask_path": candidate.get("mask_path"),
        "label_id": candidate.get("label_id"),
        "label_name": candidate.get("label_name") or candidate.get("object_label"),
        "bbox": bbox,
        "mask_area_fraction": area,
        "task_family": family,
        "domain": domain,
        "split": candidate.get("split", "pilot"),
        "edit_type": edit_type,
        "required_change": required_change,
        "planned_params": _planned_params(edit_type, bbox, area, seed),
        "expected_effect": _expected_effect(family, edit_type, required_change),
        "single_factor": True,
        "release_mode": candidate.get("release_mode"),
        "license_posture": candidate.get("license_posture"),
        "planned_edited_image_path": f"planned://pilot/{edit_id}",
        "evidence_status": "PLANNED_ONLY",
        "generation_status": "not_generated",
        "zero_cost": True,
        "edits_generated": False,
        "vlm_inference_run": False,
    }


def _planned_params(edit_type: str, bbox: list[int] | None, area: float | None, seed: int) -> dict:
    base = {
        "bbox": bbox,
        "mask_area_fraction": area,
        "seed": seed,
        "generator": "not_selected_v1_4_plan_only",
        "zero_cost": True,
    }
    if edit_type == EditType.REMOVE.value:
        return {**base, "operation": "mask_region_removal_planned"}
    if edit_type == EditType.OCCLUDE.value:
        return {**base, "operation": "neutral_patch_occlusion_planned", "occluder": "neutral_patch"}
    if edit_type == EditType.DISPLACE.value:
        return {**base, "operation": "mask_region_displacement_planned", "offset_xy": [16, 0]}
    if edit_type == EditType.CONTROL_IRRELEVANT.value:
        return {**base, "operation": "irrelevant_control_change_planned", "control_scope": "non_answer_factor"}
    return {**base, "operation": f"{edit_type}_planned"}


def _expected_effect(family: str, edit_type: str, required_change: str) -> str:
    if required_change == RequiredChange.NO_CHANGE.value:
        return f"{edit_type} plan should preserve the expected answer for {family}"
    return f"{edit_type} plan should change the expected answer for {family}"


def _rejected_record(
    candidate: dict,
    edit_id: str,
    edit_type: str,
    required_change: str,
    reasons: list[str],
) -> dict:
    return {
        "candidate_id": candidate.get("candidate_id"),
        "source_id": candidate.get("source_id"),
        "mask_id": candidate.get("mask_id"),
        "label_id": candidate.get("label_id"),
        "attempted_task_family": str(candidate.get("proposed_task_family") or candidate.get("task_family") or "unknown"),
        "edit_id": edit_id,
        "attempted_edit_type": edit_type,
        "attempted_required_change": required_change,
        "rejection_reasons": reasons,
        "rejection_reason": "; ".join(reasons),
        "evidence_status": candidate.get("evidence_status", "CANDIDATE_ONLY"),
        "generation_status": "not_generated",
        "zero_cost": True,
        "candidate": candidate,
    }


def _valid_bbox(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    if any(not isinstance(coord, int) or coord < 0 for coord in value):
        return False
    x1, y1, x2, y2 = value
    return x2 > x1 and y2 > y1


def _requires_local_exists(path: str) -> bool:
    lowered = path.lower()
    return not lowered.startswith(("http://", "https://", "s3://", "gs://", "planned://"))


def _edit_id(candidate: dict, edit_type: str, seed: int) -> str:
    payload = f"{seed}|{candidate.get('source_id')}|{candidate.get('mask_id')}|{edit_type}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"pilot_{digest}"


def _normalize_ratios(ratios: dict[str, float]) -> dict[str, float]:
    valid = {
        EditType.REMOVE.value,
        EditType.OCCLUDE.value,
        EditType.DISPLACE.value,
        EditType.CONTROL_IRRELEVANT.value,
    }
    cleaned = {str(key): float(value) for key, value in ratios.items() if str(key) in valid and float(value) > 0}
    if not cleaned:
        raise EditPlanError("edit_type_ratios must contain at least one supported positive ratio")
    total = sum(cleaned.values())
    return {key: value / total for key, value in sorted(cleaned.items())}


def _reason_counts(rejected: list[dict]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rejected:
        for reason in row.get("rejection_reasons", []):
            counts[reason] += 1
    return dict(sorted(counts.items()))


def _rejections_by(rejected: list[dict], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rejected:
        counts[str(row.get(key, "unknown"))] += 1
    return dict(sorted(counts.items()))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--summary-out", required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--rejected-out")
    parser.add_argument("--min-mask-area-fraction", type=float, default=DEFAULT_MIN_MASK_AREA_FRACTION)
    parser.add_argument("--max-mask-area-fraction", type=float, default=DEFAULT_MAX_MASK_AREA_FRACTION)
    parser.add_argument("--edit-type-ratios-json")
    parser.add_argument("--label-policy")
    args = parser.parse_args(argv)
    ratios = json.loads(args.edit_type_ratios_json) if args.edit_type_ratios_json else None
    try:
        summary = build_edit_plan(
            args.selection,
            args.out,
            args.summary_out,
            seed=args.seed,
            rejected_out=args.rejected_out,
            min_mask_area_fraction=args.min_mask_area_fraction,
            max_mask_area_fraction=args.max_mask_area_fraction,
            edit_type_ratios=ratios,
            label_policy_path=args.label_policy,
        )
    except EditPlanError as exc:
        raise SystemExit(f"Edit planning failed: {exc}") from None
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
