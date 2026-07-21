"""Construct prospective Main-study semantic task candidates from source annotations."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image

from certvic.cvpr.contracts import canonical_json_bytes, load_yaml, sha256_bytes
from certvic.cvpr.semantic_edits import prospective_engine_selection
from certvic.cvpr.task_schema import TASK_SCHEMA, require_task, with_task_hash
from certvic.cvpr.transactional import read_jsonl


class MainTaskBuilderError(ValueError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _path(root: Path, value: Any) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else root / path


def _strata(width: int, height: int, bbox: list[float], annotations: int) -> dict[str, str]:
    x0, y0, x1, y1 = bbox
    fraction = max(0.0, (x1 - x0) * (y1 - y0) / (width * height))
    size = "small" if fraction < 0.05 else ("medium" if fraction < 0.20 else "large")
    center_x, center_y = (x0 + x1) / 2 / width, (y0 + y1) / 2 / height
    if 1 / 3 <= center_x <= 2 / 3 and 1 / 3 <= center_y <= 2 / 3:
        position = "center"
    else:
        position = ("top" if center_y < 0.5 else "bottom") + "_" + (
            "left" if center_x < 0.5 else "right"
        )
    complexity = "low" if annotations <= 3 else ("medium" if annotations <= 8 else "high")
    difficulty = "easy" if size == "large" and complexity == "low" else (
        "hard" if size == "small" or complexity == "high" else "medium"
    )
    return {"target_size": size, "target_position": position,
            "image_complexity": complexity, "difficulty": difficulty}


def _validate_source(root: Path, row: dict[str, Any]) -> tuple[Path, int, int]:
    if row.get("license_eligible") is not True:
        raise MainTaskBuilderError("source license is not verified eligible")
    image = _path(root, row.get("source_image_path", row.get("image_path", "")))
    if not image.is_file():
        raise MainTaskBuilderError("source image bytes are missing")
    if row.get("source_sha256") and row["source_sha256"] != _sha(image):
        raise MainTaskBuilderError("source image hash mismatch")
    with Image.open(image) as opened:
        opened.verify()
        width, height = opened.size
    return image, width, height


def _mask(root: Path, annotation: dict[str, Any]) -> tuple[Path, str]:
    path = _path(root, annotation.get("mask_path", ""))
    if not path.is_file():
        raise MainTaskBuilderError("annotation mask is missing")
    observed = _sha(path)
    if annotation.get("mask_sha256") and annotation["mask_sha256"] != observed:
        raise MainTaskBuilderError("annotation mask hash mismatch")
    return path, observed


def _canonical(row: dict[str, Any], *, seed: int) -> dict[str, Any]:
    decision = prospective_engine_selection(row)
    if decision["status"] != "ENGINE_SELECTED":
        raise MainTaskBuilderError(f"engine selection rejected task: {decision['reason']}")
    result = {
        **row,
        "task_schema_version": TASK_SCHEMA,
        "study": "main_study_cvpr",
        "task_id": row["item_id"],
        "selected_engine": decision["engine"],
        "engine_selection_reason": decision["reason"],
        "engine_fallbacks": decision.get("fallbacks", []),
        "edit_engine_policy": decision["policy_version"],
        "engine_parameters": row.get("engine_parameters", {}),
        "seed": seed,
        "primary_or_reserve": None,
        "review_status": "HUMAN_REVIEW_PENDING",
        "qa_status": "QA_PENDING",
    }
    return require_task(with_task_hash(result), verify_files=True)


def build_tasks(
    source_root: str | Path,
    sources: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    root = Path(source_root)
    policy = config.get("task_builder", {})
    supported = tuple(config.get("semantic_interventions", {}).get("allowed_families", []))
    if not supported:
        raise MainTaskBuilderError("Main config has no frozen semantic edit families")
    category_vocab = tuple(policy.get("supported_categories", []))
    candidate_assets = policy.get("insertion_assets", {})
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for source in sorted(sources, key=lambda row: str(row.get("source_image_id", row.get("source_id", "")))):
        source_id = str(source.get("source_image_id", source.get("source_id", "")))
        try:
            image, width, height = _validate_source(root, source)
            annotations = source.get("annotations")
            if not source_id or not isinstance(annotations, list) or not annotations:
                raise MainTaskBuilderError("source ID or annotations are missing")
        except MainTaskBuilderError as exc:
            rejected.append({"source_image_id": source_id, "reason": str(exc)})
            continue
        present = {str(annotation.get("category", "")) for annotation in annotations}
        for index, annotation in enumerate(annotations):
            category = str(annotation.get("category", ""))
            bbox = [float(value) for value in annotation.get("bbox", [])]
            try:
                if len(bbox) != 4 or not (0 <= bbox[0] < bbox[2] <= width
                                          and 0 <= bbox[1] < bbox[3] <= height):
                    raise MainTaskBuilderError("annotation bbox is invalid")
                mask_path, mask_hash = _mask(root, annotation)
            except MainTaskBuilderError as exc:
                rejected.append({"source_image_id": source_id, "annotation": index,
                                 "reason": str(exc)})
                continue
            strata = _strata(width, height, bbox, len(annotations))
            base = {
                "source_image_id": source_id,
                "source_image_path": str(image),
                "source_image_hash": _sha(image),
                "source_sha256": _sha(image),
                "source_dataset": source.get("source_dataset", source.get("dataset", "ADE20K")),
                "source_split": source.get("split"),
                "license_status": source.get("license_status", "VERIFIED_ELIGIBLE"),
                "target_category": category,
                "queried_category": category,
                "queried_category_absent": False,
                "target_geometry": {"bbox": bbox, "mask_path": str(mask_path)},
                "target_bbox": bbox,
                "target_mask_path": str(mask_path),
                "target_mask_hash": mask_hash,
                "mask_path": str(mask_path),
                "mask_sha256": mask_hash,
                "protected_scene_mask_path": None,
                "protected_scene_mask_hash": None,
                "control_edit_family": None,
                "attribute_name": None,
                "original_attribute": None,
                "edited_attribute": None,
                "attribute_transform": None,
                "original_attribute_verified": None,
                "strata": strata,
                "difficulty_proxy": strata["difficulty"],
                "reserve_group": f"{category}:{strata['target_size']}:{strata['target_position']}",
                "provenance": {
                    "source_manifest_schema": source.get("schema"),
                    "annotation_id": annotation.get("annotation_id", index),
                    "builder": "certvic.cvpr.main_task_builder.v1",
                },
                "human_validity_status": "HUMAN_REVIEW_PENDING",
                "paper_evidence": False,
            }
            if "object_removal" in supported:
                item_id = f"main-removal-{source_id}-{index}"
                candidate = {
                    **base, "item_id": item_id,
                    "question": f"Is there a {category} in the image?",
                    "original_expected_answer": "yes", "required_change": True,
                    "semantic_intervention": "remove_target_object",
                    "edited_expected_answer": "no", "semantic_edit_family": "object_removal",
                    "edit_family": "object_removal",
                    "deterministic_simple_case_verified": annotation.get(
                        "deterministic_simple_case_verified"
                    ) is True,
                    "candidate_asset": None, "insertion_asset_license": "NOT_APPLICABLE",
                }
                try:
                    candidates.append(_canonical(candidate, seed=int(config.get("seed", 15001))))
                except MainTaskBuilderError as exc:
                    rejected.append({"item_id": item_id, "reason": str(exc)})
            attributes = annotation.get("verified_attributes", {})
            if "attribute_modification" in supported and isinstance(attributes, dict):
                for attribute, transition in sorted(attributes.items()):
                    if not isinstance(transition, dict) or not transition.get("from") or not transition.get("to"):
                        continue
                    transform = f"{transition['from']}_to_{transition['to']}"
                    candidate = {
                        **base,
                        "item_id": f"main-attribute-{source_id}-{index}-{attribute}",
                        "question": (
                            f"Is the {category} {transition['from']}?"
                        ),
                        "original_expected_answer": "yes",
                        "semantic_intervention": {
                            "attribute": attribute, "from": transition["from"], "to": transition["to"]
                        },
                        "edited_expected_answer": "no", "required_change": True,
                        "semantic_edit_family": "attribute_modification",
                        "edit_family": "attribute_modification",
                        "attribute_name": attribute,
                        "original_attribute": transition["from"],
                        "edited_attribute": transition["to"],
                        "attribute_transform": transform,
                        "original_attribute_verified": transition.get("verified") is True,
                        "candidate_asset": None, "insertion_asset_license": "NOT_APPLICABLE",
                    }
                    try:
                        candidates.append(_canonical(candidate, seed=int(config.get("seed", 15001))))
                    except (MainTaskBuilderError, ValueError) as exc:
                        rejected.append({"item_id": candidate["item_id"], "reason": str(exc)})
        if "object_insertion" in supported:
            for category in sorted(set(category_vocab) - present):
                asset = candidate_assets.get(category)
                if not isinstance(asset, dict) or asset.get("license_eligible") is not True:
                    rejected.append({"source_image_id": source_id, "category": category,
                                     "reason": "verified insertion asset unavailable"})
                    continue
                asset_path = _path(root, asset.get("path", ""))
                if not asset_path.is_file() or _sha(asset_path) != asset.get("sha256"):
                    rejected.append({"source_image_id": source_id, "category": category,
                                     "reason": "insertion asset hash mismatch"})
                    continue
                bbox = [int(width * 0.05), int(height * 0.05), int(width * 0.25), int(height * 0.25)]
                strata = _strata(width, height, bbox, len(annotations))
                candidate = {
                    "item_id": f"main-insertion-{source_id}-{category}",
                    "source_image_id": source_id, "source_image_path": str(image),
                    "source_image_hash": _sha(image), "source_sha256": _sha(image),
                    "source_dataset": source.get("source_dataset", source.get("dataset", "ADE20K")),
                    "source_split": source.get("split"),
                    "license_status": source.get("license_status", "VERIFIED_ELIGIBLE"),
                    "target_category": category, "queried_category": category,
                    "queried_category_absent": False,
                    "target_geometry": {"bbox": bbox, "semantics": "prospective_insertion_region"},
                    "target_bbox": bbox, "target_mask_path": None, "target_mask_hash": None,
                    "mask_path": None, "mask_sha256": None,
                    "protected_scene_mask_path": None, "protected_scene_mask_hash": None,
                    "question": f"Is there a {category} in the image?",
                    "original_expected_answer": "no", "required_change": True,
                    "semantic_intervention": "insert_verified_asset",
                    "edited_expected_answer": "yes", "semantic_edit_family": "object_insertion",
                    "edit_family": "object_insertion", "control_edit_family": None,
                    "candidate_asset": str(asset_path), "insertion_asset_path": str(asset_path),
                    "insertion_asset_sha256": asset["sha256"],
                    "insertion_asset_license": asset.get("license"),
                    "attribute_name": None, "original_attribute": None,
                    "edited_attribute": None, "attribute_transform": None,
                    "original_attribute_verified": None,
                    "strata": strata, "difficulty_proxy": strata["difficulty"],
                    "reserve_group": f"{category}:{strata['target_size']}:{strata['target_position']}",
                    "provenance": {"source_manifest_schema": source.get("schema"),
                                   "asset_sha256": asset["sha256"],
                                   "builder": "certvic.cvpr.main_task_builder.v1"},
                    "human_validity_status": "HUMAN_REVIEW_PENDING", "paper_evidence": False,
                }
                try:
                    candidates.append(_canonical(candidate, seed=int(config.get("seed", 15001))))
                except MainTaskBuilderError as exc:
                    rejected.append({"item_id": candidate["item_id"], "reason": str(exc)})
    candidates.sort(key=lambda row: hashlib.sha256(
        f"{config.get('seed', 15001)}:{row['item_id']}".encode()
    ).hexdigest())
    family_targets = {str(key): int(value) for key, value in policy.get("family_candidate_targets", {}).items()}
    selected: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    for row in candidates:
        family = str(row["semantic_edit_family"])
        if family_targets and family_counts[family] >= family_targets.get(family, 0):
            rejected.append({"item_id": row["item_id"], "reason": "surplus_beyond_frozen_family_target"})
            continue
        selected.append(row)
        family_counts[family] += 1
    shortages = {
        family: max(0, count - family_counts[family]) for family, count in family_targets.items()
        if family_counts[family] < count
    }
    report = {
        "schema": "certvic.cvpr.main_task_build_report.v1",
        "status": "MAIN_CANDIDATE_TASKS_BUILT" if not shortages else "BLOCKED_CANDIDATE_SHORTAGE",
        "candidate_tasks": len(selected), "rejected_tasks": len(rejected),
        "family_counts": dict(family_counts), "family_targets": family_targets,
        "shortage_report": shortages,
        "balance_report": {
            "families": dict(family_counts),
            "categories": dict(Counter(row["target_category"] for row in selected)),
            "answer_transitions": dict(Counter(
                f"{row['original_expected_answer']}_to_{row['edited_expected_answer']}"
                for row in selected
            )),
            "target_size": dict(Counter(row["strata"]["target_size"] for row in selected)),
            "target_position": dict(Counter(row["strata"]["target_position"] for row in selected)),
            "image_complexity": dict(Counter(row["strata"]["image_complexity"] for row in selected)),
            "difficulty": dict(Counter(row["difficulty_proxy"] for row in selected)),
        },
        "task_builder_sha256": sha256_bytes(canonical_json_bytes(selected)),
        "rejected": rejected, "tasks": selected, "paper_evidence": False,
    }
    return report


def write_outputs(result: dict[str, Any], out: str | Path, report: str | Path) -> None:
    tasks, rejected = result.pop("tasks"), result.pop("rejected")
    out_path, report_path = Path(out), Path(report)
    rejected_path = out_path.with_name(out_path.stem + ".rejected.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in tasks), encoding="utf-8")
    rejected_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rejected),
                             encoding="utf-8")
    result["candidate_tasks_path"] = str(out_path)
    result["rejected_tasks_path"] = str(rejected_path)
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finalize_main_tasks(
    qa_rows: list[dict[str, Any]],
    final_review: dict[str, Any],
    config: dict[str, Any],
    out_dir: str | Path,
) -> dict[str, Any]:
    """Join QA/review and solve primary plus reserve under one exact contract."""
    from certvic.cvpr.candidate_selection import bind_final_review
    from certvic.cvpr.candidate_selection import SolverLimits, _exact_category_selection
    from certvic.cvpr.task_schema import convert_legacy_task

    reviewed, review_exclusions, review_proof = bind_final_review(qa_rows, final_review)
    eligible: list[dict[str, Any]] = []
    exclusions = list(review_exclusions)
    for row in reviewed:
        qa_status = row.get("qa_status", row.get("generation_qa_status",
                            row.get("automated_qa_status")))
        if qa_status not in {"PASS", "QA_PASS", "AUTOMATED_QA_PASS"}:
            exclusions.append({**row, "rejection_reason": "automated_QA_not_passed"})
        else:
            eligible.append(row)
    finalization = config.get("main_finalization", {})
    quotas = {
        "primary": {str(key): int(value) for key, value in finalization.get(
            "primary_family_targets", {}
        ).items()},
        "reserve": {str(key): int(value) for key, value in finalization.get(
            "reserve_family_targets", {}
        ).items()},
    }
    if not quotas["primary"] or sum(quotas["primary"].values()) != int(config["target_items"]):
        raise MainTaskBuilderError("Main primary family targets must sum to target_items")
    if sum(quotas["reserve"].values()) != int(config["reserve_items"]):
        raise MainTaskBuilderError("Main reserve family targets must sum to reserve_items")
    seed = int(config.get("seed", 15001))
    maximum_per_source = int(finalization.get("maximum_tasks_per_source", 1))
    enriched: list[dict[str, Any]] = []
    for row in eligible:
        strata = row.get("strata", {})
        family = str(row.get("semantic_edit_family", row.get("edit_family", "unknown")))
        original, edited = str(row.get("original_expected_answer", "")).lower(), str(
            row.get("edited_expected_answer", "")
        ).lower()
        size = str(strata.get("target_size", row.get("target_size_stratum", "unknown")))
        question_template = str(row.get(
            "question_template", "attribute_yes_no" if family == "attribute_modification"
            else "object_presence_yes_no"
        ))
        magnitude = str(row.get("edit_magnitude_stratum", size))
        enriched.append({
            **row,
            "selection_category": str(row.get("target_category", row.get("category", "unknown"))),
            "answer_transition": f"{original}_to_{edited}",
            "target_size_stratum": size,
            "target_position_stratum": str(strata.get(
                "target_position", row.get("target_position_stratum", "unknown")
            )),
            "image_complexity_stratum": str(strata.get(
                "image_complexity", row.get("image_complexity_stratum", "unknown")
            )),
            "edit_difficulty_stratum": str(strata.get(
                "difficulty", row.get("difficulty_proxy", "unknown")
            )),
            "engine_family": str(row.get("selected_engine", "unknown")),
            "question_template": question_template,
            "edit_magnitude_stratum": magnitude,
        })
    exact_target: dict[str, Any] = {
        "primary": int(config["target_items"]), "reserve": int(config["reserve_items"]),
        "max_per_source": maximum_per_source,
        "edit_family_balance": {"primary": quotas["primary"], "reserve": quotas["reserve"]},
    }
    frozen = finalization.get("locked_strata_targets", {})
    field_contracts = {
        "category": "category_balance",
        "answer_transition": "answer_transition_balance",
        "target_size": "size_strata",
        "target_position": "position_strata",
        "image_complexity": "image_complexity_strata",
        "difficulty": "edit_difficulty_balance",
        "engine_family": "engine_family_balance",
        "question_template": "question_template_balance",
        "edit_magnitude": "edit_magnitude_balance",
    }
    for config_name, solver_name in field_contracts.items():
        value = frozen.get(config_name)
        if value:
            exact_target[solver_name] = value
    limits_config = finalization.get("solver_limits", {})
    primary_rows, reserve_rows, exact = _exact_category_selection(
        enriched, exact_target, seed=seed, limits=SolverLimits(
            max_states=int(limits_config.get("max_states", 1_000_000)),
            timeout_seconds=float(limits_config.get("timeout_seconds", 120.0)),
            progress_interval_states=int(limits_config.get("progress_interval_states", 10_000)),
        )
    )
    selected: dict[str, list[dict[str, Any]]] = {"primary": [], "reserve": []}
    for role, rows in (("primary", primary_rows), ("reserve", reserve_rows)):
        for row in rows:
            canonical = row if row.get("task_schema_version") == TASK_SCHEMA else convert_legacy_task(
                row, study="main_study_cvpr"
            )
            # Solver-only derived fields are deliberately retained and hash-bound.
            canonical = with_task_hash({
                **canonical, "primary_or_reserve": role,
                "review_status": "VALID_ADJUDICATED", "qa_status": "PASS",
                "review_provenance": row["review_provenance"],
            })
            selected[role].append(require_task(canonical, verify_files=True))
    selected_ids = {str(row.get("task_id", row.get("item_id", "")))
                    for row in primary_rows + reserve_rows}
    surplus = [row for row in enriched if str(row.get("task_id", row.get("item_id", "")))
               not in selected_ids]
    exclusions.extend({**row, "rejection_reason": "surplus_after_exact_main_balance"}
                      for row in surplus)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    shortages = [] if exact.get("feasible") else exact.get("minimal_conflict", [])
    status = "MAIN_FINAL_TASKS_FROZEN" if exact.get("feasible") else (
        "BLOCKED_MAIN_SOLVER_RESOURCE_LIMIT" if exact.get("resource_limited")
        else "BLOCKED_MAIN_SELECTION_INFEASIBLE"
    )
    solver_report = {
        "schema": "certvic.cvpr.main_exact_selection.v1", "status": status,
        "algorithm": "DETERMINISTIC_JOINT_PRIMARY_RESERVE_EXACT_MARGINAL_SOLVER",
        "primary_family_targets": quotas["primary"], "reserve_family_targets": quotas["reserve"],
        "locked_strata_targets": frozen,
        "same_stratum_replacement_key": finalization.get("same_stratum_replacement_key", []),
        "maximum_tasks_per_source": maximum_per_source, "shortages": shortages,
        "feasibility": "FEASIBLE_SELECTION_FOUND" if exact.get("feasible") else (
            "SOLVER_RESOURCE_LIMIT" if exact.get("resource_limited") else
            exact.get("fallback_status", "NO_FEASIBLE_SELECTION_EXISTS")
        ),
        "solver_version": exact.get("solver_version"),
        "states_explored": exact.get("visited_states", exact.get("backtracking_visited_states", 0)),
        "runtime_seconds": exact.get("elapsed_seconds"),
        "fallback_used": exact.get("fallback_used", False),
        "fallback_status": exact.get("fallback_status", "NOT_REQUIRED"),
        "objective": exact.get("objective"),
        "constraints": exact_target,
        "review_proof": review_proof, "paper_evidence": False,
    }
    solver_report["selection_freeze_hash"] = sha256_bytes(canonical_json_bytes({
        "constraints": exact_target,
        "primary_task_ids": sorted(str(row["task_id"]) for row in selected["primary"]),
        "reserve_task_ids": sorted(str(row["task_id"]) for row in selected["reserve"]),
        "review_artifact_sha256": final_review["final_artifact_sha256"],
    }))
    balance_report = {
        "schema": "certvic.cvpr.main_balance_report.v1",
        "primary": {
            "families": dict(Counter(row["semantic_edit_family"] for row in selected["primary"])),
            "categories": dict(Counter(str(row.get("target_category")) for row in selected["primary"])),
            "answer_transitions": dict(Counter(
                f"{row['original_expected_answer']}_to_{row['edited_expected_answer']}"
                for row in selected["primary"]
            )),
            "target_size": dict(Counter(str(row.get("strata", {}).get("target_size"))
                                        for row in selected["primary"])),
            "target_position": dict(Counter(str(row.get("strata", {}).get("target_position"))
                                            for row in selected["primary"])),
            "image_complexity": dict(Counter(str(row.get("strata", {}).get("image_complexity"))
                                             for row in selected["primary"])),
            "difficulty": dict(Counter(str(row.get("strata", {}).get("difficulty"))
                                       for row in selected["primary"])),
            "engine_family": dict(Counter(str(row.get("selected_engine"))
                                          for row in selected["primary"])),
        },
        "paper_evidence": False,
    }
    freeze = {
        "schema": "certvic.cvpr.main_task_freeze.v1", "status": status,
        "study": "main_study_cvpr",
        "primary_tasks_sha256": sha256_bytes(canonical_json_bytes(selected["primary"])),
        "reserve_tasks_sha256": sha256_bytes(canonical_json_bytes(selected["reserve"])),
        "exclusions_sha256": sha256_bytes(canonical_json_bytes(exclusions)),
        "balance_report_sha256": sha256_bytes(canonical_json_bytes(balance_report)),
        "solver_report_sha256": sha256_bytes(canonical_json_bytes(solver_report)),
        "final_review_artifact_sha256": final_review["final_artifact_sha256"],
        "task_schema": TASK_SCHEMA, "paper_evidence": False,
    }
    freeze["freeze_hash"] = sha256_bytes(canonical_json_bytes(freeze))
    paths = {
        "main_primary_tasks.jsonl": selected["primary"],
        "main_reserve_tasks.jsonl": selected["reserve"],
        "main_exclusions.jsonl": exclusions,
    }
    for name, rows in paths.items():
        (out / name).write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
        )
    for name, payload in {
        "main_balance_report.json": balance_report,
        "main_solver_report.json": solver_report,
        "main_freeze_manifest.json": freeze,
    }.items():
        (out / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": status, "primary": len(selected["primary"]),
            "reserve": len(selected["reserve"]), "excluded": len(exclusions),
            "shortages": shortages, "freeze_hash": freeze["freeze_hash"],
            "paper_evidence": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build prospective Main-study task candidates")
    parser.add_argument("--source-root")
    parser.add_argument("--source-manifest")
    parser.add_argument("--config", required=True)
    parser.add_argument("--out")
    parser.add_argument("--report")
    parser.add_argument("--qa-enriched-manifest")
    parser.add_argument("--final-inclusion-ledger")
    parser.add_argument("--finalize-out-dir")
    args = parser.parse_args(argv)
    config = load_yaml(args.config)
    if args.qa_enriched_manifest or args.final_inclusion_ledger or args.finalize_out_dir:
        if not all((args.qa_enriched_manifest, args.final_inclusion_ledger, args.finalize_out_dir)):
            parser.error("Main finalization requires QA manifest, final inclusion ledger, and out dir")
        result = finalize_main_tasks(
            read_jsonl(args.qa_enriched_manifest),
            json.loads(Path(args.final_inclusion_ledger).read_text(encoding="utf-8")),
            config, args.finalize_out_dir,
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "MAIN_FINAL_TASKS_FROZEN" else 2
    if not all((args.source_root, args.source_manifest, args.out, args.report)):
        parser.error("candidate build requires source root, source manifest, out, and report")
    result = build_tasks(args.source_root, read_jsonl(args.source_manifest), config)
    status = result["status"]
    write_outputs(result, args.out, args.report)
    print(json.dumps({"status": status, "out": args.out, "report": args.report}, sort_keys=True))
    return 0 if status == "MAIN_CANDIDATE_TASKS_BUILT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
