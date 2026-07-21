"""Canonical task contract shared by every CVPR study lane.

Legacy formats may enter only through :func:`convert_legacy_task`.  Runtime,
analysis, selection, and import code consume the canonical names directly and
must never implement their own alias lookup.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from certvic.cvpr.contracts import canonical_json_bytes
from certvic.cvpr.transactional import read_jsonl


TASK_SCHEMA = "certvic.cvpr.task.v1"
STUDIES = {
    "specificity_confirmatory_cvpr",
    "main_study_cvpr",
    "second_domain_cvpr",
    "synthetic_confirmatory",
    "synthetic_main",
    "synthetic_coco",
}
SEMANTIC_FAMILIES = {"object_removal", "object_insertion", "attribute_modification"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")

CANONICAL_FIELDS = (
    "task_schema_version", "study", "task_id", "source_dataset", "source_split",
    "source_image_id", "source_image_path", "source_image_hash", "license_status",
    "question", "original_expected_answer", "edited_expected_answer", "required_change",
    "semantic_edit_family", "control_edit_family", "target_category", "queried_category",
    "queried_category_absent", "target_bbox", "target_mask_path", "target_mask_hash",
    "protected_scene_mask_path", "protected_scene_mask_hash", "attribute_name",
    "original_attribute", "edited_attribute", "attribute_transform",
    "original_attribute_verified", "edit_engine_policy", "selected_engine",
    "engine_fallbacks", "engine_parameters", "seed", "primary_or_reserve", "strata",
    "review_status", "qa_status", "task_hash",
)


class TaskSchemaError(ValueError):
    """A task violates the frozen canonical task contract."""


def _hash_payload(task: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(
        {key: value for key, value in task.items() if key != "task_hash"}
    )).hexdigest()


def with_task_hash(task: dict[str, Any]) -> dict[str, Any]:
    result = dict(task)
    result["task_hash"] = _hash_payload(result)
    return result


def _null_permitted(task: dict[str, Any], field: str) -> bool:
    family = task.get("semantic_edit_family")
    study = str(task.get("study", ""))
    if field in {"protected_scene_mask_path", "protected_scene_mask_hash"}:
        return task.get("queried_category_absent") is not True
    if field in {
        "attribute_name", "original_attribute", "edited_attribute", "attribute_transform",
        "original_attribute_verified",
    }:
        return family != "attribute_modification"
    if field in {"target_mask_path", "target_mask_hash"}:
        return isinstance(task.get("target_bbox"), list) and (
            family == "object_insertion" or task.get("control_edit_family") is not None
        )
    if field == "control_edit_family":
        return family in SEMANTIC_FAMILIES
    if field == "semantic_edit_family":
        return study in {"specificity_confirmatory_cvpr", "synthetic_confirmatory"}
    if field == "target_category":
        return study in {"specificity_confirmatory_cvpr", "synthetic_confirmatory"}
    if field in {"queried_category", "queried_category_absent"}:
        return task.get("queried_category_absent") is not True and (
            family in SEMANTIC_FAMILIES
            or study in {"specificity_confirmatory_cvpr", "synthetic_confirmatory"}
        )
    if field == "primary_or_reserve":
        return task.get("review_status") in {"HUMAN_REVIEW_PENDING", "SYNTHETIC_REVIEW"}
    return False


def resolve_task_path(
    task: dict[str, Any], field: str, *, bundle_root: str | Path | None = None,
) -> Path | None:
    """Resolve a task path without mutating the portable, hash-bound task row."""
    value = task.get(field)
    if value is None:
        return None
    path = Path(str(value))
    portable = task.get("path_contract") == "BUNDLE_RELATIVE"
    if portable:
        if path.is_absolute() or ".." in path.parts:
            raise TaskSchemaError(f"{field} must be a safe bundle-relative path")
        if bundle_root is None:
            raise TaskSchemaError(f"{field} requires a verified bundle_root")
        return Path(bundle_root) / path
    return path if path.is_absolute() or bundle_root is None else Path(bundle_root) / path


def validate_task(
    task: dict[str, Any], *, verify_files: bool = False,
    bundle_root: str | Path | None = None,
) -> list[str]:
    errors: list[str] = []
    missing = [field for field in CANONICAL_FIELDS if field not in task]
    if missing:
        errors.append(f"missing canonical fields: {missing}")
        return errors
    for field in CANONICAL_FIELDS:
        if task[field] is None and not _null_permitted(task, field):
            errors.append(f"{field} may not be null for this study/family")
    if task.get("task_schema_version") != TASK_SCHEMA:
        errors.append(f"task_schema_version must be {TASK_SCHEMA}")
    if str(task.get("study")) not in STUDIES:
        errors.append(f"unsupported study: {task.get('study')}")
    if not str(task.get("task_id", "")).strip():
        errors.append("task_id must be nonblank")
    if task.get("required_change") not in {True, False}:
        errors.append("required_change must be boolean")
    if task.get("required_change") is True and str(task.get("original_expected_answer")).lower() == str(
        task.get("edited_expected_answer")
    ).lower():
        errors.append("answer-changing tasks require distinct canonical gold answers")
    family = task.get("semantic_edit_family")
    if family is not None and family not in SEMANTIC_FAMILIES:
        errors.append(f"unsupported semantic_edit_family: {family}")
    bbox = task.get("target_bbox")
    if bbox is not None and (not isinstance(bbox, list) or len(bbox) != 4):
        errors.append("target_bbox must be null or four coordinates")
    if task.get("queried_category_absent") is True:
        if str(task.get("original_expected_answer", "")).lower() != "no":
            errors.append("absent-category negatives require original_expected_answer=no")
        if not task.get("protected_scene_mask_path") or not task.get("protected_scene_mask_hash"):
            errors.append("absent-category negatives require a protected-scene mask")
    if family == "attribute_modification":
        if task.get("original_attribute_verified") is not True:
            errors.append("attribute tasks require original_attribute_verified=true")
        expected = f"{task.get('original_attribute')}_to_{task.get('edited_attribute')}"
        if task.get("attribute_transform") != expected:
            errors.append(f"attribute_transform must exactly match {expected}")
    for field in ("source_image_hash", "target_mask_hash", "protected_scene_mask_hash"):
        value = task.get(field)
        if value is not None and not SHA256.fullmatch(str(value)):
            errors.append(f"{field} must be a SHA-256")
    observed_hash = task.get("task_hash")
    if not SHA256.fullmatch(str(observed_hash)) or observed_hash != _hash_payload(task):
        errors.append("task_hash does not bind the complete canonical task")
    if verify_files:
        for path_field, hash_field in (
            ("source_image_path", "source_image_hash"),
            ("target_mask_path", "target_mask_hash"),
            ("protected_scene_mask_path", "protected_scene_mask_hash"),
        ):
            value = task.get(path_field)
            if value is None:
                continue
            try:
                path = resolve_task_path(task, path_field, bundle_root=bundle_root)
            except TaskSchemaError as exc:
                errors.append(str(exc))
                continue
            assert path is not None
            if not path.is_file():
                errors.append(f"{path_field} is missing: {path}")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != task.get(hash_field):
                errors.append(f"{path_field} bytes differ from {hash_field}")
    return errors


def require_task(
    task: dict[str, Any], *, verify_files: bool = False,
    bundle_root: str | Path | None = None,
) -> dict[str, Any]:
    errors = validate_task(task, verify_files=verify_files, bundle_root=bundle_root)
    if errors:
        raise TaskSchemaError("; ".join(errors))
    return task


def require_task_matrix(
    tasks: Iterable[dict[str, Any]], *, verify_files: bool = False,
    bundle_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    rows = list(tasks)
    if not rows:
        raise TaskSchemaError("canonical task matrix is empty")
    ids = [str(row.get("task_id", "")) for row in rows]
    if len(ids) != len(set(ids)):
        raise TaskSchemaError("canonical task matrix has duplicate task_id values")
    for index, task in enumerate(rows, start=1):
        errors = validate_task(task, verify_files=verify_files, bundle_root=bundle_root)
        if errors:
            raise TaskSchemaError(f"task row {index}: {'; '.join(errors)}")
    return rows


def convert_legacy_task(row: dict[str, Any], *, study: str) -> dict[str, Any]:
    """Convert one declared legacy row; no consumer should repeat these aliases."""
    task_id = str(row.get("task_id", row.get("item_id", row.get("edit_id", ""))))
    source_path = row.get("source_image_path", row.get("image_path"))
    source_hash = row.get("source_image_hash", row.get("source_sha256", row.get("image_sha256")))
    target_mask_path = row.get("target_mask_path", row.get("mask_path"))
    target_mask_hash = row.get("target_mask_hash", row.get("mask_sha256"))
    family = row.get("semantic_edit_family", row.get("edit_family"))
    control_family = row.get("control_edit_family", row.get("perturbation_family"))
    original = row.get("original_expected_answer", row.get("original_gold_answer",
                       row.get("answer_original", row.get("expected_original",
                       row.get("expected_answer")))))
    edited = row.get("edited_expected_answer", row.get("edited_gold_answer",
                     row.get("answer_edited", row.get("expected_edited",
                     row.get("expected_answer")))))
    required = row.get("required_change")
    if required in {"change", "required", 1}:
        required = True
    elif required in {"no_change", "stable", 0}:
        required = False
    task = {
        **row,
        "task_schema_version": TASK_SCHEMA,
        "study": study,
        "task_id": task_id,
        "item_id": task_id,
        "source_dataset": row.get("source_dataset", row.get("dataset", "UNKNOWN_SOURCE")),
        "source_split": row.get("source_split", row.get("split", "UNKNOWN_SPLIT")),
        "source_image_id": str(row.get("source_image_id", row.get("source_id", task_id))),
        "source_image_path": source_path,
        "source_image_hash": source_hash,
        "license_status": row.get("license_status", "VERIFIED_ELIGIBLE" if row.get(
            "license_eligible"
        ) is True else "UNVERIFIED"),
        "question": row.get("question", row.get("original_question")),
        "original_expected_answer": original,
        "edited_expected_answer": edited,
        "required_change": required,
        "semantic_edit_family": family,
        "control_edit_family": control_family,
        "target_category": row.get("target_category", row.get("category")),
        "queried_category": row.get("queried_category", row.get("category")),
        "queried_category_absent": row.get("queried_category_absent", False),
        "target_bbox": row.get("target_bbox"),
        "target_mask_path": target_mask_path,
        "target_mask_hash": target_mask_hash,
        "protected_scene_mask_path": row.get("protected_scene_mask_path"),
        "protected_scene_mask_hash": row.get("protected_scene_mask_hash"),
        "attribute_name": row.get("attribute_name"),
        "original_attribute": row.get("original_attribute"),
        "edited_attribute": row.get("edited_attribute"),
        "attribute_transform": row.get("attribute_transform"),
        "original_attribute_verified": row.get("original_attribute_verified"),
        "edit_engine_policy": row.get("edit_engine_policy", "certvic.semantic_engine_policy.v1"),
        "selected_engine": row.get("selected_engine", row.get(
            "candidate_engine", row.get("engine_family", row.get("perturbation_family"))
        )),
        "engine_fallbacks": row.get("engine_fallbacks", []),
        "engine_parameters": row.get("engine_parameters", {}),
        "seed": int(row.get("seed", 0)),
        "primary_or_reserve": row.get("primary_or_reserve", row.get("selection_role")),
        "strata": row.get("strata", {}),
        "review_status": row.get("review_status", row.get(
            "human_validity_status", "HUMAN_REVIEW_PENDING"
        )),
        "qa_status": row.get("qa_status", row.get(
            "generation_qa_status", "QA_PENDING"
        )),
    }
    return with_task_hash(task)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert or validate canonical CertVIC tasks")
    parser.add_argument("--input", required=True)
    parser.add_argument("--study")
    parser.add_argument("--out")
    parser.add_argument("--verify-files", action="store_true")
    parser.add_argument("--bundle-root")
    args = parser.parse_args(argv)
    rows = read_jsonl(args.input)
    if args.study:
        rows = [convert_legacy_task(row, study=args.study) for row in rows]
    require_task_matrix(rows, verify_files=args.verify_files, bundle_root=args.bundle_root)
    if args.out:
        Path(args.out).write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
        )
    print(json.dumps({"status": "CANONICAL_TASKS_VALID", "rows": len(rows),
                      "schema": TASK_SCHEMA}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
