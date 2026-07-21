"""Blank, blinded review-sheet generation and fail-closed completion validation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path
from typing import Any


JUDGMENT_FIELDS = (
    "target_unaffected",
    "expected_answer_unchanged",
    "perturbation_acceptable",
    "image_answerable",
    "prompt_unambiguous",
    "retain",
    "confidence",
    "reason_code",
)
SEMANTIC_JUDGMENT_FIELDS = (
    "semantic_transition_supported",
    "target_edit_successful",
    "non_target_content_preserved",
    "perturbation_acceptable",
    "original_image_answerable",
    "edited_image_answerable",
    "retain",
    "confidence",
    "reason_code",
)
TRACKS = (
    "pilot_intervention_validity",
    "v1_specificity_validity",
    "retrospective_v2_30_sensitivity",
    "qwen_12_failure_forensic_review",
    "specificity_confirmatory_cvpr",
    "main_study_cvpr",
    "second_domain_cvpr",
)


def judgment_fields(track: str) -> tuple[str, ...]:
    if track in {"main_study_cvpr", "second_domain_cvpr"}:
        return SEMANTIC_JUDGMENT_FIELDS
    return JUDGMENT_FIELDS


def blind_id(track: str, item_id: str, seed: int) -> str:
    payload = f"{seed}:{track}:{item_id}".encode()
    return f"CVPR-{hashlib.sha256(payload).hexdigest()[:16].upper()}"


def build_blank_sheets(
    items: list[dict[str, Any]],
    track: str,
    out_dir: str | Path,
    *,
    seed: int,
) -> dict[str, Any]:
    if track not in TRACKS:
        raise ValueError(f"unknown review track: {track}")
    rows = []
    for item in items:
        item_id = str(item["item_id"])
        row = {
            "blind_pair_id": blind_id(track, item_id, seed),
            "pair_order": "AB",
            **{field: "" for field in JUDGMENT_FIELDS},
        }
        rows.append((item_id, row))
    random.Random(seed).shuffle(rows)
    for index, (_, row) in enumerate(rows):
        if index % 2:
            row["pair_order"] = "BA"
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fields = ["blind_pair_id", "pair_order", *JUDGMENT_FIELDS]
    for rater in (1, 2):
        with (out / f"rater_{rater}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(row for _, row in rows)
    with (out / "adjudication.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(row for _, row in rows)
    with (out / "coordinator_key.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["blind_pair_id", "item_id"])
        writer.writerows((row["blind_pair_id"], item_id) for item_id, row in rows)
    return {"track": track, "items": len(rows), "status": "HUMAN_REVIEW_PENDING"}


def validate_sheet(path: str | Path, *, allow_blank: bool) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    errors: list[str] = []
    ids = [row.get("blind_pair_id", "") for row in rows]
    if len(ids) != len(set(ids)) or not all(ids):
        errors.append("blank or duplicate blind_pair_id")
    for index, row in enumerate(rows, start=2):
        for field in JUDGMENT_FIELDS:
            if not row.get(field) and not allow_blank:
                errors.append(f"row {index}: blank {field}")
    return {
        "passed": not errors,
        "errors": errors,
        "rows": len(rows),
        "status": "STRUCTURALLY_VALID_BLANK" if allow_blank and not errors else "COMPLETE",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or validate blinded CertVIC review sheets")
    parser.add_argument("--items")
    parser.add_argument("--track", choices=TRACKS)
    parser.add_argument("--out-dir")
    parser.add_argument("--seed", type=int, default=12013)
    parser.add_argument("--validate-sheet")
    parser.add_argument("--allow-blank", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status-out")
    args = parser.parse_args(argv)
    if args.validate_sheet:
        result = validate_sheet(args.validate_sheet, allow_blank=args.allow_blank)
    else:
        if not args.items or not args.track or not args.out_dir:
            parser.error("--items, --track, and --out-dir are required to build sheets")
        rows = [json.loads(line) for line in Path(args.items).read_text().splitlines()
                if line.strip()]
        if args.dry_run:
            result = {"track": args.track, "items": len(rows), "status": "DRY_RUN_NO_FILES_WRITTEN"}
        else:
            result = build_blank_sheets(rows, args.track, args.out_dir, seed=args.seed)
    if args.status_out:
        Path(args.status_out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("passed", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
