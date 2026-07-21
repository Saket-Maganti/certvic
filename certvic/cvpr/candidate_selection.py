"""Outcome-blind perceptual deduplication and balanced candidate selection."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from certvic.cvpr.contracts import canonical_json_bytes, load_yaml, sha256_bytes
from certvic.cvpr.generation import DETERMINISTIC_ENGINES, GenerationError, plan_placement
from certvic.cvpr.task_schema import convert_legacy_task, require_task_matrix, with_task_hash
from certvic.cvpr.transactional import read_jsonl


@dataclass(frozen=True)
class SolverLimits:
    max_states: int = 250_000
    timeout_seconds: float = 30.0
    progress_interval_states: int = 10_000


def _bits(image: Image.Image, *, difference: bool) -> str:
    size = 8
    width = size + int(difference)
    gray = np.asarray(image.convert("L").resize((width, size), Image.Resampling.LANCZOS))
    values = gray[:, 1:] > gray[:, :-1] if difference else gray >= np.mean(gray)
    return "".join("1" if value else "0" for value in values.flat)


def hamming(left: str, right: str) -> int:
    if len(left) != len(right):
        raise ValueError("perceptual hashes must have the same length")
    return sum(a != b for a, b in zip(left, right, strict=True))


def _bbox(row: dict[str, Any], width: int, height: int) -> tuple[float, float, float, float]:
    value = row.get("target_bbox")
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError("target_bbox is required for selection geometry")
    x0, y0, x1, y1 = (float(part) for part in value)
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError("invalid target_bbox")
    return x0, y0, x1, y1


def _entropy(gray: np.ndarray) -> float:
    counts = np.bincount(gray.astype(np.uint8).ravel(), minlength=256).astype(float)
    probabilities = counts[counts > 0] / counts.sum()
    return float(-(probabilities * np.log2(probabilities)).sum() / 8.0)


def enrich_candidate(
    row: dict[str, Any],
    *,
    seed: int,
    area_fraction: float,
    minimum_distance_px: int,
    source_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = Path(str(row.get("image_path", row.get("source_image_path", ""))))
    if not path.is_file():
        raise ValueError(f"missing image: {path}")
    with Image.open(path) as opened:
        opened.load()
        source_mode = opened.mode
        image = opened.convert("RGB")
    width, height = image.size
    if source_rules:
        allowed_splits = {str(value) for value in source_rules.get("allowed_splits", [])}
        if allowed_splits and str(row.get("split")) not in allowed_splits:
            raise ValueError("candidate split is not allowed by the frozen source contract")
        if source_rules.get("license_eligible_required", True) and row.get("license_eligible") is not True:
            raise ValueError("candidate license eligibility is not verified")
        if min(width, height) < int(source_rules.get("minimum_short_side", 1)):
            raise ValueError("candidate source resolution is below the frozen minimum")
        if source_mode != "RGB" and source_rules.get("allow_controlled_rgb_conversion") is not True:
            raise ValueError("candidate source mode is not RGB")
        if source_rules.get("annotation_required", True) and not any(
            row.get(key) is not None for key in ("annotation_id", "target_mask_path", "target_bbox")
        ):
            raise ValueError("candidate has no target annotation")
    x0, y0, x1, y1 = _bbox(row, width, height)
    target_area = (x1 - x0) * (y1 - y0) / (width * height)
    cx, cy = (x0 + x1) / (2 * width), (y0 + y1) / (2 * height)
    center_distance = math.hypot(cx - 0.5, cy - 0.5) / math.sqrt(0.5)
    edge_distance = min(x0, y0, width - x1, height - y1) / min(width, height)
    gray = np.asarray(image.convert("L"))
    texture = float((np.abs(np.diff(gray.astype(float), axis=0)).mean()
                     + np.abs(np.diff(gray.astype(float), axis=1)).mean()) / (2 * 255.0))
    if target_area < 0.03:
        size_stratum = "small"
    elif target_area < 0.12:
        size_stratum = "medium"
    else:
        size_stratum = "large"
    complexity_count = int(row.get("object_count", 1))
    if complexity_count <= 2:
        complexity_stratum = "low"
    elif complexity_count <= 6:
        complexity_stratum = "medium"
    else:
        complexity_stratum = "high"
    if 0.35 <= cx <= 0.65 and 0.35 <= cy <= 0.65:
        position_stratum = "center"
    else:
        horizontal = "left" if cx < 0.5 else "right"
        vertical = "top" if cy < 0.5 else "bottom"
        position_stratum = f"{vertical}_{horizontal}"
    placements: dict[str, list[int]] = {}
    for index, engine in enumerate(DETERMINISTIC_ENGINES):
        try:
            placements[engine] = list(plan_placement(
                row,
                image.size,
                seed=seed + index,
                area_fraction=area_fraction,
                minimum_distance_px=minimum_distance_px,
            ))
        except GenerationError:
            placements[engine] = []
    return {
        **row,
        "image_path": str(path),
        "image_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "phash": _bits(image, difference=False),
        "dhash": _bits(image, difference=True),
        "target_area_fraction": target_area,
        "target_center_distance": center_distance,
        "target_edge_distance": edge_distance,
        "complexity_proxy": complexity_count,
        "complexity_stratum": complexity_stratum,
        "image_entropy": _entropy(gray),
        "texture_proxy": texture,
        "source_resolution": [width, height],
        "target_size_stratum": size_stratum,
        "target_position_stratum": position_stratum,
        "placement_proposals": placements,
        "outcome_blind": True,
        "provider_outputs_used": False,
    }


def perceptual_deduplicate(
    rows: list[dict[str, Any]], threshold: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    retained: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda value: str(value.get("source_id", value.get("item_id")))):
        match: tuple[dict[str, Any], int] | None = None
        for representative in retained:
            distance = min(hamming(row["phash"], representative["phash"]),
                           hamming(row["dhash"], representative["dhash"]))
            if distance <= threshold and (match is None or distance < match[1]):
                match = representative, distance
        if match is None:
            retained.append(row)
        else:
            representative, distance = match
            rejected.append({**row, "rejection_reason": "perceptual_duplicate",
                             "duplicate_of": representative.get("source_id"),
                             "perceptual_distance": distance})
            groups.append({
                "representative": representative.get("source_id"),
                "duplicate": row.get("source_id"),
                "distance": distance,
                "threshold": threshold,
                "method": "minimum_of_phash_and_dhash_hamming",
            })
    return retained, rejected, groups


def _category_targets(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    value = config.get("design", {}).get("category_targets")
    if not isinstance(value, dict) or not value:
        raise ValueError("design.category_targets must enumerate actual categories")
    required = {"primary", "reserve", "expected_answer_polarities", "size_strata", "position_strata"}
    for category, target in value.items():
        if not isinstance(target, dict) or required - set(target):
            raise ValueError(f"category {category} has an incomplete target contract")
    return value


def _stable_order(rows: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    def key(row: dict[str, Any]) -> str:
        identity = str(row.get("source_id", row.get("item_id")))
        strata = f"{row.get('target_size_stratum')}:{row.get('target_position_stratum')}"
        return hashlib.sha256(f"{seed}:{strata}:{identity}".encode()).hexdigest()

    return sorted(rows, key=key)


def _quota(target: dict[str, Any], field: str, role: str) -> Counter[str]:
    value = target[field]
    if isinstance(value, dict) and role in value and isinstance(value[role], dict):
        value = value[role]
    elif role == "reserve":
        return Counter()
    return Counter({str(key): int(count) for key, count in value.items()})


def _take_balanced(
    rows: list[dict[str, Any]], target: dict[str, Any], role: str, count: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, int]]]:
    quotas = {
        "expected_answer": _quota(target, "expected_answer_polarities", role),
        "target_size_stratum": _quota(target, "size_strata", role),
        "target_position_stratum": _quota(target, "position_strata", role),
    }
    selected: list[dict[str, Any]] = []
    unused: list[dict[str, Any]] = []
    for row in rows:
        values = {field: str(row.get(field, "unknown")).lower() for field in quotas}
        allowed = all(not quota or quota[values[field]] > 0 for field, quota in quotas.items())
        if allowed and len(selected) < count:
            selected.append(row)
            for field, quota in quotas.items():
                if quota:
                    quota[values[field]] -= 1
        else:
            unused.append(row)
    remaining = {field: {name: amount for name, amount in quota.items() if amount > 0}
                 for field, quota in quotas.items()}
    return selected, unused, {field: values for field, values in remaining.items() if values}


_SOLVER_FIELDS = {
    "expected_answer_polarities": "expected_answer",
    "size_strata": "target_size_stratum",
    "position_strata": "target_position_stratum",
    "image_complexity_strata": "image_complexity_stratum",
    "engine_family_balance": "engine_family",
    "edit_difficulty_balance": "edit_difficulty_stratum",
    "category_balance": "selection_category",
    "answer_transition_balance": "answer_transition",
    "question_template_balance": "question_template",
    "edit_magnitude_balance": "edit_magnitude_stratum",
    "edit_family_balance": "semantic_edit_family",
}


def _role_quotas(target: dict[str, Any], role: str, count: int) -> dict[str, Counter[str]]:
    quotas: dict[str, Counter[str]] = {}
    for config_field, row_field in _SOLVER_FIELDS.items():
        if config_field not in target:
            continue
        quota = _quota(target, config_field, role)
        if quota and sum(quota.values()) != count:
            raise ValueError(
                f"{role} {config_field} quotas sum to {sum(quota.values())}, expected {count}"
            )
        if quota:
            quotas[row_field] = quota
    return quotas


def _scipy_exact_selection(
    ordered: list[dict[str, Any]], target: dict[str, Any], *, seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]] | None:
    """Deterministic optional MILP fallback for resource-limited backtracking."""
    try:
        import scipy
        from scipy.optimize import Bounds, LinearConstraint, milp
        from scipy.sparse import lil_matrix
    except (ImportError, AttributeError):
        return None
    roles = ("primary", "reserve")
    counts = {role: int(target[role]) for role in roles}
    quotas = {role: _role_quotas(target, role, counts[role]) for role in roles}
    n_rows, n_vars = len(ordered), len(ordered) * 2
    constraints: list[tuple[dict[int, float], float, float]] = []
    for index in range(n_rows):
        constraints.append(({index: 1.0, n_rows + index: 1.0}, 0.0, 1.0))
    for role_index, role in enumerate(roles):
        offset = role_index * n_rows
        constraints.append(({offset + index: 1.0 for index in range(n_rows)},
                            float(counts[role]), float(counts[role])))
        for field, quota in quotas[role].items():
            for value, required in quota.items():
                coefficients = {
                    offset + index: 1.0 for index, row in enumerate(ordered)
                    if str(row.get(field, "unknown")).lower() == value
                }
                constraints.append((coefficients, float(required), float(required)))
    max_per_source = int(target.get("max_per_source", 1))
    sources: dict[str, list[int]] = defaultdict(list)
    duplicate_groups: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(ordered):
        source = str(row.get("source_id", row.get("source_image_id", row.get("item_id", ""))))
        sources[source].append(index)
        group = row.get("duplicate_group") or row.get("duplicate_group_id")
        if group not in {None, ""}:
            duplicate_groups[str(group)].append(index)
    for indexes in sources.values():
        constraints.append(({
            role_index * n_rows + index: 1.0
            for role_index in range(2) for index in indexes
        }, 0.0, float(max_per_source)))
    for indexes in duplicate_groups.values():
        constraints.append(({
            role_index * n_rows + index: 1.0
            for role_index in range(2) for index in indexes
        }, 0.0, 1.0))
    matrix = lil_matrix((len(constraints), n_vars), dtype=float)
    lower, upper = np.empty(len(constraints)), np.empty(len(constraints))
    for row_index, (coefficients, minimum, maximum) in enumerate(constraints):
        for column, coefficient in coefficients.items():
            matrix[row_index, column] = coefficient
        lower[row_index], upper[row_index] = minimum, maximum
    # Ordered inputs already use the seeded SHA-256 tie break.  Primary is
    # preferred before reserve, then the lexicographically earliest solution.
    objective = np.asarray([
        (role_index + 1) * 1e-6 + (index + 1) * 1e-9
        for role_index in range(2) for index in range(n_rows)
    ])
    started = time.monotonic()
    result = milp(
        c=objective, integrality=np.ones(n_vars), bounds=Bounds(0.0, 1.0),
        constraints=LinearConstraint(matrix.tocsr(), lower, upper),
        options={"presolve": True, "time_limit": 120.0},
    )
    elapsed = round(time.monotonic() - started, 6)
    if not result.success or result.x is None:
        return [], [], {
            "feasible": False, "resource_limited": False,
            "solver_version": f"scipy_milp_{scipy.__version__}",
            "fallback_used": True, "fallback_status": "NO_FEASIBLE_SELECTION_EXISTS",
            "elapsed_seconds": elapsed, "minimal_conflict": [{"reason": str(result.message)}],
        }
    primary_indexes = [index for index in range(n_rows) if result.x[index] > 0.5]
    reserve_indexes = [index for index in range(n_rows) if result.x[n_rows + index] > 0.5]
    selected = set(primary_indexes + reserve_indexes)
    primary, reserve = ([ordered[index] for index in primary_indexes],
                        [ordered[index] for index in reserve_indexes])
    return primary, reserve, {
        "feasible": True, "resource_limited": False,
        "solver_version": f"scipy_milp_{scipy.__version__}",
        "fallback_used": True, "fallback_status": "FEASIBLE_SELECTION_FOUND",
        "visited_states": 0, "memoized_failure_states": 0,
        "elapsed_seconds": elapsed, "progress": [],
        "objective": {"quota_deviation": 0,
                      "unique_sources": len(sources),
                      "qa_score_sum": sum(float(row.get("qa_score", row.get("salience_score", 0.0)))
                                          for row in primary + reserve),
                      "tie_break": "seeded_sha256_then_deterministic_milp_objective"},
        "surplus_indices": [index for index in range(n_rows) if index not in selected],
        "ordered": ordered,
    }


def _exact_category_selection(
    rows: list[dict[str, Any]], target: dict[str, Any], *, seed: int,
    limits: SolverLimits | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Solve exact marginals with pruning, memoization, and deterministic limits."""
    limits = limits or SolverLimits()
    if limits.max_states < 1 or limits.timeout_seconds <= 0:
        raise ValueError("solver limits must be positive")
    counts = {"primary": int(target["primary"]), "reserve": int(target["reserve"])}
    remaining = {
        role: _role_quotas(target, role, count) for role, count in counts.items()
    }
    max_per_source = int(target.get("max_per_source", 1))
    ordered = _stable_order(rows, seed)
    used: set[int] = set()
    source_counts: Counter[str] = Counter()
    duplicate_groups: set[str] = set()
    assignments: dict[str, list[int]] = {"primary": [], "reserve": []}
    visited = 0
    memoized_failures: set[tuple[Any, ...]] = set()
    started = time.monotonic()
    resource_limited: str | None = None
    progress: list[dict[str, Any]] = []

    def source(row: dict[str, Any]) -> str:
        return str(row.get("source_id", row.get("source_image_id", row.get("item_id", ""))))

    def duplicate_group(row: dict[str, Any]) -> str | None:
        value = row.get("duplicate_group") or row.get("duplicate_group_id")
        return str(value) if value not in {None, ""} else None

    def viable(index: int, role: str) -> bool:
        row = ordered[index]
        if index in used or len(assignments[role]) >= counts[role]:
            return False
        if source_counts[source(row)] >= max_per_source:
            return False
        group = duplicate_group(row)
        if group is not None and group in duplicate_groups:
            return False
        for field, quota in remaining[role].items():
            value = str(row.get(field, "unknown")).lower()
            if quota[value] <= 0:
                return False
        return True

    def unmet_constraints() -> list[tuple[int, str, str | None, str | None, list[int]]]:
        constraints: list[tuple[int, str, str | None, str | None, list[int]]] = []
        for role in ("primary", "reserve"):
            count_need = counts[role] - len(assignments[role])
            if count_need > 0:
                options = [index for index in range(len(ordered)) if viable(index, role)]
                constraints.append((len(options), role, None, None, options))
            for field, quota in remaining[role].items():
                for value, need in quota.items():
                    if need <= 0:
                        continue
                    options = [
                        index for index, row in enumerate(ordered)
                        if viable(index, role)
                        and str(row.get(field, "unknown")).lower() == value
                    ]
                    constraints.append((len(options), role, field, value, options))
        return constraints

    def state_key() -> tuple[Any, ...]:
        quotas = tuple(
            (role, field, tuple(sorted(quota.items())))
            for role in ("primary", "reserve")
            for field, quota in sorted(remaining[role].items())
        )
        return (
            tuple(sorted(used)), tuple(sorted(source_counts.items())),
            tuple(sorted(duplicate_groups)),
            tuple((role, len(assignments[role])) for role in ("primary", "reserve")), quotas,
        )

    def globally_feasible() -> bool:
        available = len(ordered) - len(used)
        total_need = sum(counts[role] - len(assignments[role]) for role in counts)
        if available < total_need:
            return False
        for role in ("primary", "reserve"):
            for field, quota in remaining[role].items():
                for value, need in quota.items():
                    if need <= 0:
                        continue
                    available_value = sum(
                        viable(index, role)
                        and str(row.get(field, "unknown")).lower() == value
                        for index, row in enumerate(ordered)
                    )
                    if available_value < need:
                        return False
        return True

    def solve() -> bool:
        nonlocal visited, resource_limited
        if resource_limited is not None:
            return False
        visited += 1
        elapsed = time.monotonic() - started
        if visited > limits.max_states:
            resource_limited = "maximum_states_exceeded"
            return False
        if elapsed > limits.timeout_seconds:
            resource_limited = "timeout_exceeded"
            return False
        if visited % limits.progress_interval_states == 0:
            progress.append({"visited_states": visited, "elapsed_seconds": round(elapsed, 6)})
        key = state_key()
        if key in memoized_failures or not globally_feasible():
            return False
        constraints = unmet_constraints()
        if not constraints:
            return all(len(assignments[role]) == counts[role] for role in assignments)
        constraint = min(
            constraints,
            key=lambda item: (
                item[0], item[1], item[2] or "", item[3] or ""
            ),
        )
        _, role, _, _, options = constraint
        if not options:
            return False
        for index in options:
            row = ordered[index]
            used.add(index)
            assignments[role].append(index)
            source_counts[source(row)] += 1
            group = duplicate_group(row)
            if group is not None:
                duplicate_groups.add(group)
            for field, quota in remaining[role].items():
                quota[str(row.get(field, "unknown")).lower()] -= 1
            if solve():
                return True
            for field, quota in remaining[role].items():
                quota[str(row.get(field, "unknown")).lower()] += 1
            if group is not None:
                duplicate_groups.remove(group)
            source_counts[source(row)] -= 1
            assignments[role].pop()
            used.remove(index)
            if resource_limited is not None:
                return False
        memoized_failures.add(key)
        return False

    feasible = solve()
    if not feasible:
        if resource_limited is not None:
            fallback = _scipy_exact_selection(ordered, target, seed=seed)
            if fallback is not None:
                primary, reserve, report = fallback
                report["backtracking_resource_limit_reason"] = resource_limited
                report["backtracking_visited_states"] = visited
                return primary, reserve, report
        conflicts = []
        for option_count, role, field, value, _ in sorted(
            unmet_constraints(),
            key=lambda item: (item[0], item[1], item[2] or "", item[3] or ""),
        ):
            if option_count == 0:
                conflicts.append({"role": role, "field": field or "item_count", "value": value,
                                  "available": 0})
        return [], [], {
            "feasible": False,
            "resource_limited": resource_limited is not None,
            "resource_limit_reason": resource_limited,
            "fallback_used": False,
            "fallback_status": ("OPTIONAL_SOLVER_UNAVAILABLE"
                                if resource_limited is not None else "NOT_REQUIRED"),
            "solver_version": "certvic.exact_backtracking.v2",
            "visited_states": visited,
            "memoized_failure_states": len(memoized_failures),
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "progress": progress,
            "minimal_conflict": conflicts[:10] or [{"reason": "joint_marginal_constraints_conflict"}],
        }
    primary = [ordered[index] for index in assignments["primary"]]
    reserve = [ordered[index] for index in assignments["reserve"]]
    selected = set(assignments["primary"] + assignments["reserve"])
    qa_score = sum(float(row.get("qa_score", row.get("salience_score", 0.0)))
                   for row in primary + reserve)
    return primary, reserve, {
        "feasible": True,
        "solver_version": "certvic.exact_backtracking.v2",
        "visited_states": visited,
        "memoized_failure_states": len(memoized_failures),
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "resource_limited": False,
        "fallback_used": False, "fallback_status": "NOT_REQUIRED",
        "progress": progress,
        "objective": {
            "quota_deviation": 0,
            "unique_sources": len({source(row) for row in primary + reserve}),
            "qa_score_sum": qa_score,
            "tie_break": "seeded_sha256_lexicographic",
        },
        "surplus_indices": [index for index in range(len(ordered)) if index not in selected],
        "ordered": ordered,
    }


def balanced_select(
    rows: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    seed: int,
    solver_limits: SolverLimits | None = None,
) -> dict[str, Any]:
    targets = _category_targets(config)
    requirements = config.get("selection_requirements", {})
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rejected: list[dict[str, Any]] = []
    for row in rows:
        category = str(row.get("category", ""))
        if category not in targets:
            rejected.append({**row, "rejection_reason": "category_not_in_frozen_targets"})
        elif requirements.get("require_license_eligible", False) and row.get("license_eligible") is not True:
            rejected.append({**row, "rejection_reason": "license_not_verified_eligible"})
        elif requirements.get("require_generation_qa", False) and row.get("generation_qa_status") != "PASS":
            rejected.append({**row, "rejection_reason": "generation_qa_not_passed"})
        elif requirements.get("require_salience_review", False) and row.get("salience_review_status") != "PASS":
            rejected.append({**row, "rejection_reason": "salience_review_not_passed"})
        elif requirements.get("require_detectability_review", False) and row.get("detectability_review_status") != "PASS":
            rejected.append({**row, "rejection_reason": "detectability_review_not_passed"})
        elif requirements.get("require_qa_enriched_manifest", False) and (
            row.get("qa_enrichment_schema") != "certvic.cvpr.confirmatory_qa.v1"
            or row.get("qa_status_source") != "COMPUTED_FROM_BYTES_AND_FROZEN_CONTRACT"
        ):
            rejected.append({**row, "rejection_reason": "canonical_qa_enrichment_missing"})
        elif not all(row.get("placement_proposals", {}).values()):
            rejected.append({**row, "rejection_reason": "no_valid_placement_for_all_families"})
        else:
            by_category[category].append(row)
    primary: list[dict[str, Any]] = []
    reserve: list[dict[str, Any]] = []
    shortage: list[dict[str, Any]] = []
    solver_reports: list[dict[str, Any]] = []
    for category, target in targets.items():
        ordered = _stable_order(by_category.get(category, []), seed)
        primary_count, reserve_count = int(target["primary"]), int(target["reserve"])
        selected_primary, selected_reserve, solver = _exact_category_selection(
            ordered, target, seed=seed, limits=solver_limits
        )
        solver_reports.append({"category": category, **{key: value for key, value in solver.items()
                                                        if key not in {"ordered", "surplus_indices"}}})
        surplus = (
            [solver["ordered"][index] for index in solver["surplus_indices"]]
            if solver.get("feasible") else ordered
        )
        primary.extend({**row, "selection_role": "primary"} for row in selected_primary)
        reserve.extend({**row, "selection_role": "reserve"} for row in selected_reserve)
        rejected.extend({**row, "rejection_reason": "surplus_after_balanced_selection"}
                        for row in surplus)
        if not solver.get("feasible"):
            shortage.append({
                "category": category,
                "available": len(ordered),
                "required": primary_count + reserve_count,
                "shortfall": primary_count + reserve_count
                - len(selected_primary) - len(selected_reserve),
                "minimal_conflict": solver.get("minimal_conflict", []),
            })
    selection_payload = {
        "primary": primary,
        "reserve": reserve,
        "design": config.get("design"),
        "exclusions": config.get("exclusions"),
        "selection_requirements": requirements,
        "seed": seed,
    }
    primary_hash = sha256_bytes(canonical_json_bytes(selection_payload))
    resource_limited = any(report.get("resource_limited") for report in solver_reports)
    return {
        "schema": "certvic.cvpr.balanced_selection.v2",
        "status": ("SOLVER_RESOURCE_LIMIT" if resource_limited else
                   ("BLOCKED_SHORTAGE" if shortage else "BALANCED_SELECTION_COMPLETE")),
        "feasibility_status": (
            "SOLVER_RESOURCE_LIMIT" if resource_limited else
            ("NO_FEASIBLE_SELECTION_EXISTS" if shortage else "FEASIBLE_SELECTION_FOUND")
        ),
        "primary": primary,
        "reserve": reserve,
        "rejected": rejected,
        "shortage": shortage,
        "balance": {
            "primary_by_category": dict(Counter(str(row["category"]) for row in primary)),
            "primary_by_size": dict(Counter(str(row["target_size_stratum"]) for row in primary)),
            "primary_by_position": dict(Counter(str(row["target_position_stratum"]) for row in primary)),
            "answer_polarity": dict(Counter(str(row.get("expected_answer", "unknown")) for row in primary)),
        },
        "selection_sha256": primary_hash,
        "selection_hash_scope": "canonical_full_primary_reserve_and_frozen_selection_contract",
        "solution_report": {
            "constraints": config.get("design", {}),
            "achieved_counts": {
                "primary": len(primary), "reserve": len(reserve),
            },
            "unsatisfied_constraints": shortage,
            "objective_value": sum(
                float(report.get("objective", {}).get("qa_score_sum", 0.0))
                for report in solver_reports
            ),
            "seed": seed,
            "solver_version": "certvic.exact_backtracking.v2",
            "categories": solver_reports,
        },
        "seed": seed,
        "paper_evidence": False,
    }


def overlap_certificate(
    selected: list[dict[str, Any]], inventory: dict[str, Any], duplicate_groups: list[dict[str, Any]]
) -> dict[str, Any]:
    selected_ids = {str(row.get("item_id", "")) for row in selected}
    selected_sources = {str(row.get("source_id", "")) for row in selected}
    selected_images = {str(row.get("source_image_id", row.get("source_id", ""))) for row in selected}
    selected_hashes = {str(row.get("image_sha256", "")) for row in selected}
    checks = {
        "item_id_overlap": sorted(selected_ids & set(map(str, inventory.get("item_ids", [])))),
        "source_id_overlap": sorted(selected_sources & set(map(str, inventory.get("source_ids", [])))),
        "source_image_id_overlap": sorted(
            selected_images & set(map(str, inventory.get("source_image_ids", [])))
        ),
        "image_sha256_overlap": sorted(
            selected_hashes & set(map(str, inventory.get("original_image_sha256", [])))
        ),
        "selected_perceptual_duplicate_groups": [group for group in duplicate_groups
                                                  if group["duplicate"] in selected_sources],
    }
    return {
        "schema": "certvic.cvpr.zero_overlap_certificate.v1",
        "passed": not any(checks.values()),
        "checks": checks,
        "inventory_sha256": sha256_bytes(canonical_json_bytes(inventory)),
        "selected_count": len(selected),
        "paper_evidence": False,
    }


def bind_final_review(
    rows: list[dict[str, Any]], final_review: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Restrict a QA universe to retained rows from a provenance-complete final review."""
    if final_review.get("schema") != "certvic.cvpr.final_review_state.v2" or final_review.get(
        "status"
    ) != "FINAL_INCLUSION_VALIDATED":
        raise ValueError("selection requires FINAL_INCLUSION_VALIDATED review schema v2")
    ledger = final_review.get("ledger")
    if not isinstance(ledger, list) or not ledger:
        raise ValueError("final review ledger must contain the complete item universe")
    if final_review.get("final_ledger_sha256") != sha256_bytes(canonical_json_bytes(ledger)):
        raise ValueError("final review ledger hash mismatch")
    payload = {key: value for key, value in final_review.items() if key != "final_artifact_sha256"}
    if final_review.get("final_artifact_sha256") != sha256_bytes(canonical_json_bytes(payload)):
        raise ValueError("final review artifact signature mismatch")
    provenance = final_review.get("provenance")
    required_provenance = {
        "reviewer_identity_hashes", "qualification_artifact_hashes",
        "validation_artifact_hashes", "packet_hash", "rater_sheet_hashes",
        "agreement_artifact_hash", "adjudication_artifact_hash", "adjudicator_identity_sha256",
    }
    if not isinstance(provenance, dict) or required_provenance - set(provenance):
        raise ValueError("final review provenance is incomplete")
    hashes: list[str] = []
    for value in provenance.values():
        hashes.extend(value.values() if isinstance(value, dict) else [value])
    if any(not isinstance(value, str) or len(value) != 64 for value in hashes):
        raise ValueError("final review provenance contains a malformed artifact hash")
    row_map = {str(row.get("item_id", row.get("task_id", ""))): row for row in rows}
    ledger_map = {str(row.get("item_id", "")): row for row in ledger}
    if "" in row_map or "" in ledger_map or len(row_map) != len(rows) or len(ledger_map) != len(ledger):
        raise ValueError("QA or final-review universe has blank or duplicate item IDs")
    if set(row_map) != set(ledger_map):
        raise ValueError("final review ledger must exactly match the QA-enriched item universe")
    retained: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for item_id in sorted(row_map):
        review_row = ledger_map[item_id]
        joined = {
            **row_map[item_id],
            "review_status": review_row.get("review_status"),
            "review_provenance": {
                "final_review_artifact_sha256": final_review["final_artifact_sha256"],
                "final_review_ledger_sha256": final_review["final_ledger_sha256"],
                "packet_hash": provenance["packet_hash"],
                "final_reason_code": review_row.get("final_reason_code"),
            },
        }
        if review_row.get("final_inclusion") is True and review_row.get(
            "review_status"
        ) == "VALID_ADJUDICATED":
            retained.append(joined)
        else:
            excluded.append({**joined, "rejection_reason": "excluded_by_final_review"})
    review_proof = {
        "schema": "certvic.cvpr.selection_review_proof.v1",
        "complete_universe": len(rows), "retained": len(retained), "excluded": len(excluded),
        "final_review_artifact_sha256": final_review["final_artifact_sha256"],
        "final_review_ledger_sha256": final_review["final_ledger_sha256"],
        "packet_hash": provenance["packet_hash"], "paper_evidence": False,
    }
    return retained, excluded, review_proof


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select balanced CertVIC CVPR candidates")
    parser.add_argument("--qa-enriched-manifest", required=True)
    parser.add_argument("--final-inclusion-ledger", required=True)
    parser.add_argument("--config", default="configs/studies/specificity_confirmatory_cvpr.yaml")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--seed", type=int, default=12013)
    parser.add_argument("--max-states", type=int, default=250_000)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args(argv)
    config = load_yaml(args.config)
    design = config["design"]
    final_review = json.loads(Path(args.final_inclusion_ledger).read_text(encoding="utf-8"))
    reviewed, review_exclusions, review_proof = bind_final_review(
        read_jsonl(args.qa_enriched_manifest), final_review
    )
    enriched = [enrich_candidate(
        row,
        seed=args.seed,
        area_fraction=float(design["perturbation_area_fraction"]["minimum"]),
        minimum_distance_px=int(design["minimum_distance_from_target_px"]),
        source_rules=config.get("source_rules"),
    ) for row in reviewed]
    retained, duplicate_rejections, groups = perceptual_deduplicate(
        enriched, int(config["exclusions"]["perceptual_duplicate_hamming_distance_max"])
    )
    result = balanced_select(
        retained, config, seed=args.seed,
        solver_limits=SolverLimits(max_states=args.max_states, timeout_seconds=args.timeout_seconds),
    )
    result["rejected"].extend([*review_exclusions, *duplicate_rejections])
    inventory_path = Path(str(config["exclusions"]["frozen_inventory"]))
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    certificate = overlap_certificate(result["primary"] + result["reserve"], inventory, groups)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    canonical_primary = [convert_legacy_task(
        {**row, "primary_or_reserve": "primary", "selection_role": "primary",
         "qa_status": row.get("generation_qa_status"), "review_status": "VALID_ADJUDICATED"},
        study=str(config["study_id"]),
    ) for row in result["primary"]]
    canonical_reserve = [convert_legacy_task(
        {**row, "primary_or_reserve": "reserve", "selection_role": "reserve",
         "qa_status": row.get("generation_qa_status"), "review_status": "VALID_ADJUDICATED"},
        study=str(config["study_id"]),
    ) for row in result["reserve"]]
    canonical_primary = require_task_matrix([with_task_hash(row) for row in canonical_primary]) \
        if canonical_primary else []
    canonical_reserve = require_task_matrix([with_task_hash(row) for row in canonical_reserve]) \
        if canonical_reserve else []
    _write_jsonl(out / "selected_primary.jsonl", canonical_primary)
    _write_jsonl(out / "selected_reserve.jsonl", canonical_reserve)
    _write_jsonl(out / "rejected_candidates.jsonl", result["rejected"])
    (out / "shortage_report.json").write_text(json.dumps(result["shortage"], indent=2) + "\n")
    (out / "balance_report.json").write_text(json.dumps(result["balance"], indent=2) + "\n")
    (out / "overlap_certificate.json").write_text(json.dumps(certificate, indent=2) + "\n")
    (out / "review_selection_proof.json").write_text(
        json.dumps(review_proof, indent=2, sort_keys=True) + "\n"
    )
    freeze = {
        "schema": "certvic.cvpr.final_task_freeze.v1", "study": config["study_id"],
        "status": "FINAL_TASKS_FROZEN" if result["status"] == "BALANCED_SELECTION_COMPLETE"
        and certificate["passed"] else "BLOCKED_NOT_FROZEN",
        "primary_tasks_sha256": sha256_bytes(canonical_json_bytes(canonical_primary)),
        "reserve_tasks_sha256": sha256_bytes(canonical_json_bytes(canonical_reserve)),
        "selection_sha256": result["selection_sha256"],
        "review_artifact_sha256": final_review["final_artifact_sha256"],
        "solver_report_sha256": sha256_bytes(canonical_json_bytes(result["solution_report"])),
        "study_config_sha256": hashlib.sha256(Path(args.config).read_bytes()).hexdigest(),
        "paper_evidence": False,
    }
    freeze["freeze_hash"] = sha256_bytes(canonical_json_bytes(freeze))
    (out / "final_task_freeze.json").write_text(
        json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    status = result["status"] if certificate["passed"] else "BLOCKED_OVERLAP"
    print(json.dumps({"status": status, "selection_sha256": result["selection_sha256"]}))
    return 0 if status == "BALANCED_SELECTION_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
