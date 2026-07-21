"""Disagreement extraction and fail-closed adjudicated inclusion."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from certvic.cvpr.human_review import JUDGMENT_FIELDS
from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes


def _read(path: str | Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames or []
    mapped = {row.get("blind_pair_id", ""): row for row in rows}
    if "" in mapped or len(mapped) != len(rows):
        raise ValueError("blank or duplicate pair IDs")
    return fields, mapped


def extract_disagreements(
    rater_1: str | Path, rater_2: str | Path, out: str | Path,
    *, fields: tuple[str, ...] = JUDGMENT_FIELDS,
) -> dict[str, Any]:
    _, left = _read(rater_1)
    _, right = _read(rater_2)
    if set(left) != set(right):
        raise ValueError("rater sheets contain different pair IDs")
    output_fields = ["blind_pair_id", "disagreement_fields", *fields]
    rows = []
    for pair_id in sorted(left):
        differences = [field for field in fields if left[pair_id].get(field) != right[pair_id].get(field)]
        if differences:
            rows.append({"blind_pair_id": pair_id, "disagreement_fields": "|".join(differences),
                         **{field: "" for field in fields}})
    path = Path(out)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(rows)
    return {"status": "ADJUDICATION_PENDING" if rows else "NO_DISAGREEMENTS",
            "disagreements": len(rows), "paper_evidence": False}


def finalize_inclusion(
    rater_1: str | Path,
    rater_2: str | Path,
    adjudication: str | Path,
    coordinator_key: str | Path,
    packet_hash_manifest: str | Path,
    *,
    packet_root: str | Path,
    fields: tuple[str, ...] = JUDGMENT_FIELDS,
) -> dict[str, Any]:
    _, left = _read(rater_1)
    _, right = _read(rater_2)
    _, adjudicated = _read(adjudication)
    _, key = _read(coordinator_key)
    if not (set(left) == set(right) == set(key)):
        raise ValueError("review and coordinator pair IDs do not match")
    manifest = json.loads(Path(packet_hash_manifest).read_text(encoding="utf-8"))
    root = Path(packet_root)
    hash_errors = [relative for relative, expected in manifest.get("files", {}).items()
                   if not (root / relative).is_file()
                   or hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected]
    if hash_errors:
        raise ValueError(f"review packet hash mismatch: {hash_errors[:10]}")
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for pair_id in sorted(left):
        final: dict[str, str] = {}
        for field in fields:
            first, second = left[pair_id].get(field, ""), right[pair_id].get(field, "")
            if not first or not second:
                unresolved.append(f"{pair_id}:{field}:incomplete_rater")
                continue
            if first == second:
                final[field] = first
            else:
                value = adjudicated.get(pair_id, {}).get(field, "")
                if not value:
                    unresolved.append(f"{pair_id}:{field}:adjudication_required")
                final[field] = value
        if not any(value.startswith(pair_id) for value in unresolved):
            accept = all(final[field].strip().lower() in {"yes", "true", "accept", "1"}
                         for field in fields if field not in {"confidence", "reason_code"})
            disagreement_fields = [
                field for field in fields if left[pair_id].get(field) != right[pair_id].get(field)
            ]
            reason_code = final.get("reason_code", "").strip() or (
                "ALL_REQUIRED_FIELDS_ACCEPTED" if accept else "REVIEW_CRITERION_REJECTED"
            )
            record = {
                "item_id": key[pair_id]["item_id"],
                "blind_pair_id": pair_id,
                "rater_1_decisions": {field: left[pair_id].get(field, "") for field in fields},
                "rater_2_decisions": {field: right[pair_id].get(field, "") for field in fields},
                "disagreement_fields": disagreement_fields,
                "adjudicated_decisions": {
                    field: adjudicated.get(pair_id, {}).get(field, "") for field in disagreement_fields
                },
                "final_decisions": final,
                "final_inclusion": accept,
                "final_reason_code": reason_code,
                "confidence_summary": {
                    "rater_1": left[pair_id].get("confidence"),
                    "rater_2": right[pair_id].get("confidence"),
                    "final": final.get("confidence"),
                },
                "review_status": "VALID_ADJUDICATED",
            }
            ledger.append(record)
            if accept:
                included.append(record)
            else:
                excluded.append(record)
    result = {
        "schema": "certvic.cvpr.final_inclusion.v1",
        "status": "BLOCKED_INCOMPLETE_REVIEW" if unresolved else "FINAL_INCLUSION_VALIDATED",
        "included": included,
        "excluded": excluded,
        "ledger": ledger,
        "unresolved": unresolved,
        "packet_hashes_verified": True,
        "raw_rater_sha256": {
            "rater_1": hashlib.sha256(Path(rater_1).read_bytes()).hexdigest(),
            "rater_2": hashlib.sha256(Path(rater_2).read_bytes()).hexdigest(),
            "adjudication": hashlib.sha256(Path(adjudication).read_bytes()).hexdigest(),
        },
        "paper_evidence": False,
    }
    result["final_ledger_sha256"] = sha256_bytes(canonical_json_bytes(ledger))
    return result
