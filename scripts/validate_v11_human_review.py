"""Validate V11 blinded human-review packets and compute independent-rater IAA.

The validator fails closed on blank, partial, malformed, or same-rater sheets. Use
``--allow-blank`` only to validate an untouched template before it is issued. Agreement
and Cohen's kappa are never computed until both independent rater sheets are complete.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_v11_human_review_packet import (  # noqa: E402
    ADJUDICATION_COLUMNS,
    DEFAULT_OUT,
    RATING_FIELDS,
    SHEET_COLUMNS,
)


ALLOWED_VALUES = {
    "prompt_unambiguous": {"yes", "no", "uncertain"},
    "image_answerable": {"yes", "no", "uncertain"},
    "target_visible_a": {"yes", "no", "uncertain"},
    "target_visible_b": {"yes", "no", "uncertain"},
    "target_unaffected": {"yes", "no", "uncertain", "not_applicable"},
    "expected_answer_relation_valid": {"yes", "no", "uncertain"},
    "expected_answer_unchanged": {"yes", "no", "uncertain", "not_applicable"},
    "perturbation_acceptable": {"yes", "no", "uncertain"},
    "artifact_severity": {"none", "minor", "major", "uncertain"},
    "retention_decision": {"retain", "exclude", "uncertain"},
    "confidence": {"high", "medium", "low"},
}
REVIEWER_CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,63}$")
_PRIVATE_MARKERS = ("/" + "Users/", "/" + "home/", "file" + "://")
PRIVATE_PATH_RE = re.compile(
    "(?:" + "|".join(re.escape(marker) for marker in _PRIVATE_MARKERS) + r"|[A-Za-z]:\\)"
)
BANNED_REVIEWER_TOKENS = {
    "qwen2_5_vl_7b",
    "internvl_8b",
    "llava_onevision_7b",
    "qwen_spurious",
    "provider_name",
    "parsed_answer",
    "selection_basis",
    "observed_qwen_v1_answer_flip",
}
TEXT_SUFFIXES = {".csv", ".json", ".md", ".txt"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path, expected_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_columns:
            raise ValueError(
                f"{path}: columns differ; expected {expected_columns}, found {reader.fieldnames}"
            )
        return list(reader)


def _valid_utc(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return (
        parsed.tzinfo is not None
        and parsed.utcoffset() is not None
        and parsed.utcoffset().total_seconds() == 0
    )


def _allowed_for_track(field: str, value: str, track_id: str) -> bool:
    if value not in ALLOWED_VALUES[field]:
        return False
    if field in {"target_unaffected", "expected_answer_unchanged"}:
        if track_id == "intervention91":
            return value == "not_applicable"
        return value != "not_applicable"
    return True


def _cohen_kappa(left: list[str], right: list[str]) -> dict[str, Any]:
    if len(left) != len(right) or not left:
        raise ValueError("kappa requires equally sized non-empty vectors")
    n = len(left)
    observed = sum(a == b for a, b in zip(left, right, strict=True)) / n
    labels = sorted(set(left) | set(right))
    left_counts = Counter(left)
    right_counts = Counter(right)
    expected = sum((left_counts[label] / n) * (right_counts[label] / n) for label in labels)
    if math.isclose(expected, 1.0):
        kappa: float | None = None
        reason = "undefined because both raters used one category exclusively"
    else:
        kappa = (observed - expected) / (1.0 - expected)
        reason = None
    return {
        "n": n,
        "percent_agreement": observed * 100.0,
        "cohen_kappa": kappa,
        "kappa_undefined_reason": reason,
    }


def _scan_reviewer_tree(reviewer_root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(p for p in reviewer_root.rglob("*") if p.is_file()):
        relative = path.relative_to(reviewer_root).as_posix()
        if "coordinator" in relative.lower() or "selection_provenance" in relative.lower():
            errors.append(f"reviewer tree exposes coordinator material: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        if PRIVATE_PATH_RE.search(text):
            errors.append(f"private absolute path found in reviewer file: {relative}")
        lowered = text.lower()
        for token in sorted(BANNED_REVIEWER_TOKENS):
            if token in lowered:
                errors.append(f"outcome/provider token {token!r} found in reviewer file: {relative}")
    return errors


def _scan_reviewer_zip(zip_path: Path) -> list[str]:
    errors: list[str] = []
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            errors.append("reviewer zip has duplicate member names")
        for name in names:
            lowered_name = name.lower()
            if name.startswith("/") or ".." in Path(name).parts:
                errors.append(f"reviewer zip has unsafe member path: {name}")
            if "coordinator" in lowered_name or "selection_provenance" in lowered_name:
                errors.append(f"reviewer zip exposes coordinator material: {name}")
            if Path(name).suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = archive.read(name).decode("utf-8")
            if PRIVATE_PATH_RE.search(text):
                errors.append(f"private absolute path found in reviewer zip member: {name}")
            lowered = text.lower()
            for token in sorted(BANNED_REVIEWER_TOKENS):
                if token in lowered:
                    errors.append(f"outcome/provider token {token!r} found in zip member: {name}")
    return errors


def _sheet_state(
    path: Path,
    expected_ids: set[str],
    track_id: str,
) -> tuple[str, list[dict[str, str]], list[str], str | None]:
    errors: list[str] = []
    rows = _read_csv(path, SHEET_COLUMNS)
    ids = [row["blind_pair_id"] for row in rows]
    if len(ids) != len(set(ids)):
        errors.append(f"{path}: duplicate blind_pair_id")
    if set(ids) != expected_ids:
        errors.append(f"{path}: blind_pair_id set differs from reviewer manifest")
    orders = [row["blind_order"] for row in rows]
    if sorted(orders, key=int) != [str(i) for i in range(1, len(rows) + 1)]:
        errors.append(f"{path}: blind_order is not exactly 1..N")

    required = [*RATING_FIELDS, "reviewer_code", "reviewed_at_utc"]
    values = [row[field].strip() for row in rows for field in required]
    if all(not value for value in values):
        return "blank", rows, errors, None
    if any(not value for value in values):
        errors.append(f"{path}: partial sheet; every required human field must be completed")
        return "partial", rows, errors, None

    reviewer_codes = {row["reviewer_code"].strip() for row in rows}
    if len(reviewer_codes) != 1:
        errors.append(f"{path}: exactly one reviewer_code must be used throughout the sheet")
        reviewer_code = None
    else:
        reviewer_code = next(iter(reviewer_codes))
        if not REVIEWER_CODE_RE.fullmatch(reviewer_code):
            errors.append(f"{path}: invalid reviewer_code format")
    for row_number, row in enumerate(rows, 2):
        for field in RATING_FIELDS:
            value = row[field].strip().lower()
            if not _allowed_for_track(field, value, track_id):
                errors.append(f"{path}:{row_number}: invalid {field}={value!r}")
        if not _valid_utc(row["reviewed_at_utc"].strip()):
            errors.append(f"{path}:{row_number}: reviewed_at_utc must include a UTC offset")
    return "complete", rows, errors, reviewer_code


def _validate_adjudication(
    path: Path,
    expected_ids: set[str],
    disagreement_ids: set[str],
    track_id: str,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    rows = _read_csv(path, ADJUDICATION_COLUMNS)
    by_id = {row["blind_pair_id"]: row for row in rows}
    if len(by_id) != len(rows) or set(by_id) != expected_ids:
        errors.append(f"{path}: adjudication IDs are missing, duplicated, or unexpected")
        return False, errors
    if not disagreement_ids:
        return True, errors
    for pair_id in sorted(disagreement_ids):
        row = by_id[pair_id]
        for field in RATING_FIELDS:
            column = f"final_{field}"
            value = row[column].strip().lower()
            if not _allowed_for_track(field, value, track_id):
                errors.append(f"{path}: {pair_id} requires valid {column}")
        code = row["adjudicator_code"].strip()
        if not REVIEWER_CODE_RE.fullmatch(code):
            errors.append(f"{path}: {pair_id} requires a valid adjudicator_code")
        if not _valid_utc(row["adjudicated_at_utc"].strip()):
            errors.append(f"{path}: {pair_id} requires an ISO-8601 UTC adjudication time")
    return not errors, errors


def _agreement(
    rater_1: list[dict[str, str]],
    rater_2: list[dict[str, str]],
) -> tuple[dict[str, Any], set[str]]:
    left = {row["blind_pair_id"]: row for row in rater_1}
    right = {row["blind_pair_id"]: row for row in rater_2}
    ids = sorted(left)
    metrics = {}
    disagreement_ids: set[str] = set()
    for field in RATING_FIELDS:
        left_values = [left[pair_id][field].strip().lower() for pair_id in ids]
        right_values = [right[pair_id][field].strip().lower() for pair_id in ids]
        metrics[field] = _cohen_kappa(left_values, right_values)
        disagreement_ids.update(
            pair_id
            for pair_id, a, b in zip(ids, left_values, right_values, strict=True)
            if a != b
        )
    return metrics, disagreement_ids


def validate_packet(
    packet_dir: Path = DEFAULT_OUT,
    *,
    allow_blank: bool = False,
    write_report: bool = True,
) -> dict[str, Any]:
    packet_dir = packet_dir.resolve()
    reviewer_root = packet_dir / "reviewer_bundle"
    errors: list[str] = []
    if not reviewer_root.is_dir():
        raise FileNotFoundError(f"reviewer bundle missing: {reviewer_root}")
    reviewer_manifest_path = reviewer_root / "reviewer_manifest.json"
    packet_manifest_path = packet_dir / "packet_manifest.json"
    reviewer_manifest = json.loads(reviewer_manifest_path.read_text(encoding="utf-8"))
    packet_manifest = json.loads(packet_manifest_path.read_text(encoding="utf-8"))
    if reviewer_manifest.get("public_release_allowed") is not False:
        errors.append("reviewer manifest must mark ADE-derived packet non-public")
    if packet_manifest.get("public_release_allowed") is not False:
        errors.append("packet manifest must mark ADE-derived packet non-public")
    errors.extend(_scan_reviewer_tree(reviewer_root))

    zip_path = packet_dir / str(packet_manifest["reviewer_zip"])
    if not zip_path.is_file():
        errors.append(f"reviewer zip missing: {zip_path.name}")
    else:
        if _sha256(zip_path) != packet_manifest.get("reviewer_zip_sha256"):
            errors.append("reviewer zip hash differs from packet manifest")
        errors.extend(_scan_reviewer_zip(zip_path))

    image_entries = [image for track in reviewer_manifest["tracks"] for image in track["images"]]
    expected_image_paths = {str(entry["path"]) for entry in image_entries}
    actual_image_paths = {
        path.relative_to(reviewer_root).as_posix()
        for path in reviewer_root.rglob("*")
        if path.is_file() and "/images/" in f"/{path.relative_to(reviewer_root).as_posix()}"
    }
    if actual_image_paths != expected_image_paths:
        errors.append("reviewer image inventory differs from reviewer manifest")
    for entry in image_entries:
        path = reviewer_root / str(entry["path"])
        if not path.is_file() or _sha256(path) != entry["sha256"]:
            errors.append(f"missing or hash-mismatched reviewer image: {entry['path']}")

    tracks_report: list[dict[str, Any]] = []
    packet_states: list[str] = []
    for track in reviewer_manifest["tracks"]:
        track_id = str(track["track_id"])
        expected_ids = set(map(str, track["blind_pair_ids"]))
        track_root = reviewer_root / "tracks" / track_id
        state_1, rows_1, sheet_errors_1, code_1 = _sheet_state(
            track_root / "rater_1.csv", expected_ids, track_id
        )
        state_2, rows_2, sheet_errors_2, code_2 = _sheet_state(
            track_root / "rater_2.csv", expected_ids, track_id
        )
        errors.extend(sheet_errors_1)
        errors.extend(sheet_errors_2)
        if state_1 != state_2:
            errors.append(f"{track_id}: both raters must complete independently before validation")
        state = state_1 if state_1 == state_2 else "partial"
        packet_states.append(state)
        metrics = None
        disagreement_ids: set[str] = set()
        adjudication_complete = False
        if state == "complete" and not sheet_errors_1 and not sheet_errors_2:
            if code_1 == code_2:
                errors.append(f"{track_id}: rater_1 and rater_2 must have distinct reviewer codes")
            else:
                metrics, disagreement_ids = _agreement(rows_1, rows_2)
                adjudication_complete, adjudication_errors = _validate_adjudication(
                    track_root / "adjudication.csv", expected_ids, disagreement_ids, track_id
                )
                errors.extend(adjudication_errors)
        else:
            try:
                _, adjudication_errors = _validate_adjudication(
                    track_root / "adjudication.csv", expected_ids, set(), track_id
                )
                errors.extend(adjudication_errors)
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
        tracks_report.append(
            {
                "track_id": track_id,
                "n_pairs": len(expected_ids),
                "rater_1_state": state_1,
                "rater_2_state": state_2,
                "independent_reviewer_codes": (
                    bool(code_1 and code_2 and code_1 != code_2) if state == "complete" else None
                ),
                "agreement": metrics,
                "n_pairs_requiring_adjudication": (
                    len(disagreement_ids) if metrics is not None else None
                ),
                "adjudication_complete": adjudication_complete if metrics is not None else None,
            }
        )

    all_blank = bool(packet_states) and all(state == "blank" for state in packet_states)
    all_complete = bool(packet_states) and all(state == "complete" for state in packet_states)
    if all_blank:
        status = "PENDING_BLANK_TEMPLATES"
        if not allow_blank:
            errors.append("human review is blank; rerun with --allow-blank only for template QA")
    elif all_complete:
        if errors:
            status = "COMPLETED_SHEETS_INVALID_OR_ADJUDICATION_PENDING"
        else:
            status = "INDEPENDENT_REVIEW_COMPLETE_IAA_COMPUTED"
    else:
        status = "PARTIAL_OR_MIXED_COMPLETION_REFUSED"
        errors.append("packet contains partial or mixed review completion")

    report = {
        "schema": "certvic.v11.human_review_validation.v1",
        "status": status,
        "valid": not errors,
        "review_complete": all_complete and not errors,
        "allow_blank": allow_blank,
        "paper_evidence": False,
        "evidence_status": (
            "DERIVED_FROM_REAL_EVIDENCE"
            if all_complete and not errors
            else "HUMAN_REVIEW_PENDING"
        ),
        "agreement_computed": all(
            track["agreement"] is not None for track in tracks_report
        ),
        "tracks": tracks_report,
        "errors": sorted(set(errors)),
    }
    if write_report:
        output = packet_dir / "human_review_validation.json"
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--allow-blank", action="store_true")
    parser.add_argument("--no-write-report", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = validate_packet(
            args.packet_dir,
            allow_blank=args.allow_blank,
            write_report=not args.no_write_report,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        raise SystemExit(2) from exc
    print(json.dumps(report, sort_keys=True))
    if not report["valid"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
