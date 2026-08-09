"""Fail-closed duplicate, overlap, perceptual-near-duplicate, and leakage audit."""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy.fft import dctn

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from local_operator.cvpr2027_common import (  # noqa: E402
    REPO,
    REPORT_ROOT,
    artifact_manifest,
    read_jsonl,
    resolve_repository_path,
    sha256_file,
    write_csv,
    write_json,
)
from local_operator.cvpr2027_pilot_analysis import (  # noqa: E402
    IRRELEVANT_TASKS,
    RELEVANT_TASKS,
)


PHASH_THRESHOLD = 6


@dataclass(frozen=True)
class Dataset:
    name: str
    tasks: Path
    evidence_class: str
    prospective: bool


DATASETS = [
    Dataset("pilot_intervention_91", RELEVANT_TASKS, "HISTORICAL_PILOT", False),
    Dataset("specificity_v1_94", IRRELEVANT_TASKS, "HISTORICAL_PILOT", False),
    Dataset(
        "specificity_v2_30",
        REPO / "data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl",
        "RETROSPECTIVE_ONLY",
        False,
    ),
    Dataset(
        "confirmatory",
        REPO / "data/studies/specificity_confirmatory_cvpr/task_bundle/tasks.jsonl",
        "PROSPECTIVE_CONFIRMATORY",
        True,
    ),
    Dataset(
        "main500",
        REPO / "data/studies/main_study_cvpr/task_bundle/tasks.jsonl",
        "CONDITIONAL_MAIN",
        True,
    ),
    Dataset(
        "second_domain",
        REPO / "data/studies/second_domain_cvpr/task_bundle/tasks.jsonl",
        "CONDITIONAL_SECOND_DOMAIN",
        True,
    ),
]


def _image_array(path: Path, size: tuple[int, int]) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("L").resize(size, Image.Resampling.LANCZOS), dtype=float)


def _bits_to_int(bits: np.ndarray) -> int:
    result = 0
    for value in bits.reshape(-1):
        result = (result << 1) | int(bool(value))
    return result


def image_hashes(path: Path) -> dict[str, int]:
    ahash_array = _image_array(path, (8, 8))
    ahash = _bits_to_int(ahash_array > ahash_array.mean())
    dhash_array = _image_array(path, (9, 8))
    dhash = _bits_to_int(dhash_array[:, 1:] > dhash_array[:, :-1])
    phash_array = _image_array(path, (32, 32))
    coefficients = dctn(phash_array, type=2, norm="ortho")[:8, :8]
    median = np.median(coefficients.reshape(-1)[1:])
    phash = _bits_to_int(coefficients > median)
    return {"ahash": ahash, "dhash": dhash, "phash": phash}


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def _resolve(task: dict[str, Any], task_path: Path, field: str) -> Path | None:
    value = task.get(field)
    if value is None:
        return None
    if str(value).startswith("__CTRL__/"):
        return resolve_repository_path(value, base=task_path.parent)
    return resolve_repository_path(value, base=REPO)


def inventory() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    task_rows = []
    images = []
    for dataset in DATASETS:
        if not dataset.tasks.is_file():
            continue
        for task in read_jsonl(dataset.tasks):
            item_id = str(task.get("item_id", ""))
            source = task.get("source") or {}
            source_id = str(task.get("source_id") or source.get("source_id") or item_id)
            question = str(task.get("question_original", ""))
            task_rows.append(
                {
                    "dataset": dataset.name,
                    "evidence_class": dataset.evidence_class,
                    "prospective": dataset.prospective,
                    "item_id": item_id,
                    "source_id": source_id,
                    "question": question,
                    "task_file": dataset.tasks.relative_to(REPO).as_posix(),
                }
            )
            for variant, field in [
                ("original", "original_image_path"),
                ("edited", "edited_image_path"),
            ]:
                path = _resolve(task, dataset.tasks, field)
                if path is None or not path.is_file():
                    continue
                hashes = image_hashes(path)
                images.append(
                    {
                        "dataset": dataset.name,
                        "evidence_class": dataset.evidence_class,
                        "prospective": dataset.prospective,
                        "item_id": item_id,
                        "source_id": source_id,
                        "variant": variant,
                        "path": path.relative_to(REPO).as_posix(),
                        "sha256": sha256_file(path),
                        **hashes,
                    }
                )
    return task_rows, images


def _collision_row(
    collision_type: str,
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    distance: int | None = None,
) -> dict[str, Any]:
    retrospective_expected = {left["dataset"], right["dataset"]} == {
        "specificity_v1_94",
        "specificity_v2_30",
    }
    return {
        "collision_type": collision_type,
        "left_dataset": left["dataset"],
        "right_dataset": right["dataset"],
        "left_item_id": left["item_id"],
        "right_item_id": right["item_id"],
        "left_variant": left.get("variant"),
        "right_variant": right.get("variant"),
        "left_path": left.get("path"),
        "right_path": right.get("path"),
        "hamming_distance": distance,
        "prospective_collision": bool(left["prospective"] or right["prospective"]),
        "classification": (
            "KNOWN_V2_RETROSPECTIVE_REUSE"
            if retrospective_expected
            else "SCIENTIFIC_SET_COLLISION"
        ),
    }


def collisions(task_rows: list[dict[str, Any]], images: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for key, collision_type in [("item_id", "ITEM_ID"), ("source_id", "SOURCE_ID")]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in task_rows:
            groups[row[key]].append(row)
        for values in groups.values():
            for left, right in itertools.combinations(values, 2):
                if left["dataset"] != right["dataset"]:
                    output.append(_collision_row(collision_type, left, right))
    for key, collision_type in [("sha256", "EXACT_SHA256")]:
        groups = defaultdict(list)
        for row in images:
            groups[row[key]].append(row)
        for values in groups.values():
            for left, right in itertools.combinations(values, 2):
                if left["dataset"] != right["dataset"] or left["item_id"] != right["item_id"]:
                    output.append(_collision_row(collision_type, left, right))
    for left, right in itertools.combinations(images, 2):
        if left["dataset"] == right["dataset"] and left["item_id"] == right["item_id"]:
            continue
        if left["sha256"] == right["sha256"]:
            continue
        for hash_name in ["phash", "dhash", "ahash"]:
            distance = hamming(int(left[hash_name]), int(right[hash_name]))
            if distance <= PHASH_THRESHOLD:
                output.append(
                    _collision_row(
                        f"{hash_name.upper()}_NEAR_DUPLICATE", left, right, distance=distance
                    )
                )
    unique = {}
    for row in output:
        key = json.dumps(row, sort_keys=True)
        unique[key] = row
    return sorted(
        unique.values(),
        key=lambda row: (
            row["collision_type"],
            row["left_dataset"],
            row["right_dataset"],
            row["left_item_id"],
            row["right_item_id"],
        ),
    )


def prompt_and_path_leakage(task_rows: list[dict[str, Any]], images: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    prohibited_path_tokens = re.compile(r"(?:^|[_/.-])(gold|answer_yes|answer_no|provider_output)(?:[_/.-]|$)", re.I)
    for row in images:
        if prohibited_path_tokens.search(str(row["path"])):
            output.append(
                {
                    "leakage_type": "FILENAME_OR_DIRECTORY_GOLD_LEAKAGE",
                    "dataset": row["dataset"],
                    "item_id": row["item_id"],
                    "value": row["path"],
                }
            )
    for row in task_rows:
        question = row["question"].casefold()
        if any(marker in question for marker in ["correct answer is", "gold answer", "model output"]):
            output.append(
                {
                    "leakage_type": "PROMPT_GOLD_LEAKAGE",
                    "dataset": row["dataset"],
                    "item_id": row["item_id"],
                    "value": row["question"],
                }
            )
    return output


def _recursive_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_recursive_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_recursive_keys(item) for item in value), set())
    return set()


def reviewer_packet_audit() -> dict[str, Any]:
    packet_root = (
        REPO
        / "reports/v11_full_ceiling_audit/human_review_packet/"
        "reviewer_bundle"
    )
    packet_manifest_path = packet_root.parent / "packet_manifest.json"
    packet_manifest = json.loads(packet_manifest_path.read_text(encoding="utf-8"))
    prohibited_keys = {
        "provider",
        "provider_name",
        "raw_output",
        "parsed_answer",
        "model_output",
        "flip",
        "failure_label",
    }
    observed_keys: set[str] = set()
    suspicious_members = []
    for path in sorted(packet_root.rglob("*")):
        if not path.is_file():
            continue
        name = path.relative_to(packet_root).as_posix()
        if any(
            token in name.casefold()
            for token in ["provider_output", "predictions", "failure_label"]
        ):
            suspicious_members.append(name)
        if name.endswith(".json"):
            observed_keys.update(
                _recursive_keys(json.loads(path.read_text(encoding="utf-8")))
            )
    found = sorted(prohibited_keys & observed_keys)
    return {
        "packet": packet_root.relative_to(REPO).as_posix(),
        "declared_archive_sha256": packet_manifest["reviewer_zip_sha256"],
        "packet_manifest_sha256": sha256_file(packet_manifest_path),
        "prohibited_fields_found": found,
        "suspicious_member_names": suspicious_members,
        "provider_outcome_blinding_pass": not found and not suspicious_members,
        "paper_evidence": False,
    }


def run(output_root: Path = REPORT_ROOT) -> dict[str, Any]:
    started = time.perf_counter()
    audit_root = output_root / "audits"
    task_rows, images = inventory()
    collision_rows = collisions(task_rows, images)
    leakage_rows = prompt_and_path_leakage(task_rows, images)
    review = reviewer_packet_audit()
    prospective = [row for row in collision_rows if row["prospective_collision"]]
    collision_counts = Counter(row["collision_type"] for row in collision_rows)
    v1_items = {row["item_id"] for row in task_rows if row["dataset"] == "specificity_v1_94"}
    v2_items = {row["item_id"] for row in task_rows if row["dataset"] == "specificity_v2_30"}
    report = {
        "schema": "certvic.cvpr2027.duplicate_leakage_audit.v1",
        "status": (
            "FAIL_CLOSED_PROSPECTIVE_COLLISION"
            if prospective
            else "PASS_WITH_DOCUMENTED_RETROSPECTIVE_V2_REUSE"
        ),
        "datasets_present": sorted({row["dataset"] for row in task_rows}),
        "task_rows": len(task_rows),
        "image_records": len(images),
        "collision_counts": dict(sorted(collision_counts.items())),
        "prospective_collision_count": len(prospective),
        "v1_v2_item_overlap": len(v1_items & v2_items),
        "v1_v2_expected_overlap": 30,
        "v2_classification": "RETROSPECTIVE_ONLY",
        "perceptual_hamming_threshold": PHASH_THRESHOLD,
        "prompt_filename_metadata_leakage": leakage_rows,
        "reviewer_packet": review,
        "confirmatory_bytes_present": any(row["dataset"] == "confirmatory" for row in task_rows),
        "main_bytes_present": any(row["dataset"] == "main500" for row in task_rows),
        "second_domain_bytes_present": any(
            row["dataset"] == "second_domain" for row in task_rows
        ),
        "paper_evidence": False,
    }
    output_paths = [
        write_csv(audit_root / "duplicate_pairs.csv", collision_rows),
        write_json(audit_root / "DUPLICATE_LEAKAGE_AUDIT.json", report),
    ]
    output_paths.append(
        write_json(audit_root / "LEAKAGE_ARTIFACT_MANIFEST.json", artifact_manifest(output_paths))
    )
    return {
        "status": "COMPLETE" if not prospective else "FAILED_LOCAL_REPAIR_REQUIRED",
        "runtime_seconds": time.perf_counter() - started,
        "verdict": report["status"],
        "collisions": len(collision_rows),
        "prospective_collisions": len(prospective),
        "outputs": [path.relative_to(REPO).as_posix() for path in output_paths],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPORT_ROOT)
    args = parser.parse_args(argv)
    result = run(args.output_root)
    print(result)
    return 0 if result["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
