"""Operational hardening helpers for genuine blinded human review."""

from __future__ import annotations

import csv
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from certvic.cvpr.ceiling_common import atomic_json, canonical_json_bytes, sha256_file, utc_now
from certvic.cvpr.contracts import sha256_bytes


def _csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def packet_inventory(packet_root: str | Path) -> dict[str, Any]:
    root = Path(packet_root)
    manifest_path = root / "reviewer_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    sheets = {
        name: {"rows": len(_csv_rows(root / name)), "sha256": sha256_file(root / name) if (root / name).is_file() else None}
        for name in ("rater_1.csv", "rater_2.csv", "adjudication.csv", "coordinator_key.csv")
    }
    image_files = sorted(
        path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    expected = manifest.get("items", manifest.get("item_count"))
    errors: list[str] = []
    rater_counts = {sheets[name]["rows"] for name in ("rater_1.csv", "rater_2.csv")}
    if len(rater_counts) != 1 or 0 in rater_counts:
        errors.append("rater templates are missing or have different row counts")
    if isinstance(expected, int) and rater_counts != {expected}:
        errors.append("rater templates differ from manifest item count")
    return {
        "schema": "certvic.cvpr.review_packet_inventory.v1",
        "passed": not errors,
        "packet_version_sha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
        "sheets": sheets,
        "image_count": len(image_files),
        "errors": errors,
        "paper_evidence": False,
    }


def reviewer_progress(template: str | Path, completed: str | Path, fields: tuple[str, ...]) -> dict[str, Any]:
    template_rows = _csv_rows(Path(template))
    completed_rows = _csv_rows(Path(completed))
    template_ids = {str(row.get("blind_pair_id", "")) for row in template_rows}
    completed_by_id = {str(row.get("blind_pair_id", "")): row for row in completed_rows}
    missing_rows = sorted(template_ids - set(completed_by_id))
    extra_rows = sorted(set(completed_by_id) - template_ids)
    incomplete = sorted(
        pair_id for pair_id in template_ids & set(completed_by_id)
        if any(not str(completed_by_id[pair_id].get(field, "")).strip() for field in fields)
    )
    completed_count = len(template_ids) - len(missing_rows) - len(incomplete)
    return {
        "schema": "certvic.cvpr.reviewer_progress.v1",
        "passed": not missing_rows and not extra_rows and not incomplete,
        "total": len(template_ids),
        "completed": completed_count,
        "missing_rows": missing_rows,
        "incomplete_rows": incomplete,
        "extra_rows": extra_rows,
        "progress_fraction": completed_count / len(template_ids) if template_ids else 0.0,
        "paper_evidence": False,
    }


def verify_blind_ids(coordinator_key: str | Path, sheets: list[str | Path]) -> dict[str, Any]:
    key_rows = _csv_rows(Path(coordinator_key))
    ids = [str(row.get("blind_pair_id", "")) for row in key_rows]
    errors: list[str] = []
    if not ids or len(ids) != len(set(ids)) or "" in ids:
        errors.append("coordinator key has blank or duplicate blind IDs")
    expected = set(ids)
    for sheet in sheets:
        observed_rows = _csv_rows(Path(sheet))
        observed = [str(row.get("blind_pair_id", "")) for row in observed_rows]
        if len(observed) != len(set(observed)) or set(observed) != expected:
            errors.append(f"{sheet}: blind-ID universe mismatch")
        forbidden = {"item_id", "source_image_id", "provider", "model", "expected_answer"}
        if any(forbidden & set(row) for row in observed_rows):
            errors.append(f"{sheet}: unblinded columns present")
    return {
        "schema": "certvic.cvpr.blind_id_verification.v1",
        "passed": not errors,
        "blind_id_count": len(expected),
        "errors": errors,
        "paper_evidence": False,
    }


def qualification_is_current(qualification: dict[str, Any], *, now: datetime | None = None) -> bool:
    expires = qualification.get("expires_at_utc")
    if not isinstance(expires, str):
        return False
    try:
        expiry = datetime.fromisoformat(expires).astimezone(timezone.utc)
    except ValueError:
        return False
    return expiry > (now or datetime.now(timezone.utc))


def assign_adjudicator(adjudicator_id: str, *, qualification_hash: str) -> dict[str, Any]:
    if not adjudicator_id.strip() or len(qualification_hash) != 64:
        raise ValueError("adjudicator identity and qualification artifact SHA-256 are required")
    return {
        "schema": "certvic.cvpr.adjudicator_assignment.v1",
        "role": "ADJUDICATOR",
        "authorized": True,
        "adjudicator_identity_sha256": hashlib.sha256(adjudicator_id.strip().encode()).hexdigest(),
        "qualification_artifact_sha256": qualification_hash,
        "assigned_at_utc": utc_now(),
        "paper_evidence": False,
    }


def append_timeline(
    path: str | Path, *, stage: str, artifact_path: str | Path, actor_role: str
) -> dict[str, Any]:
    destination = Path(path)
    value = json.loads(destination.read_text(encoding="utf-8")) if destination.is_file() else {
        "schema": "certvic.cvpr.review_timeline.v1", "events": [], "paper_evidence": False
    }
    if value.get("schema") != "certvic.cvpr.review_timeline.v1":
        raise ValueError("review timeline schema mismatch")
    previous_hash = value["events"][-1]["event_hash"] if value["events"] else None
    event = {
        "sequence": len(value["events"]) + 1,
        "stage": stage,
        "actor_role": actor_role,
        "artifact_sha256": sha256_file(artifact_path),
        "previous_event_hash": previous_hash,
        "recorded_at_utc": utc_now(),
    }
    event["event_hash"] = sha256_bytes(canonical_json_bytes(event))
    value["events"].append(event)
    value["timeline_hash"] = sha256_bytes(canonical_json_bytes(value["events"]))
    atomic_json(destination, value)
    return value


def packet_diff(left: str | Path, right: str | Path) -> dict[str, Any]:
    def inventory(root: Path) -> dict[str, str]:
        return {
            path.relative_to(root).as_posix(): sha256_file(path)
            for path in sorted(root.rglob("*")) if path.is_file()
        }

    left_rows, right_rows = inventory(Path(left)), inventory(Path(right))
    return {
        "schema": "certvic.cvpr.review_packet_diff.v1",
        "added": sorted(set(right_rows) - set(left_rows)),
        "removed": sorted(set(left_rows) - set(right_rows)),
        "changed": sorted(
            name for name in set(left_rows) & set(right_rows) if left_rows[name] != right_rows[name]
        ),
        "unchanged": sorted(
            name for name in set(left_rows) & set(right_rows) if left_rows[name] == right_rows[name]
        ),
        "paper_evidence": False,
    }


def exclusion_html(final_state: str | Path, out: str | Path) -> dict[str, Any]:
    value = json.loads(Path(final_state).read_text(encoding="utf-8"))
    rows = [row for row in value.get("ledger", []) if row.get("final_inclusion") is not True]
    body = "\n".join(
        "<tr><td>" + html.escape(str(row.get("blind_pair_id", row.get("item_id", ""))))
        + "</td><td>" + html.escape(str(row.get("reason_code", row.get("exclusion_reason", "UNSPECIFIED"))))
        + "</td></tr>"
        for row in rows
    )
    document = (
        "<!doctype html><meta charset='utf-8'><title>CertVIC exclusions</title>"
        "<h1>Outcome-blind exclusion reasons</h1><table><thead><tr><th>Blind ID</th>"
        "<th>Reason</th></tr></thead><tbody>" + body + "</tbody></table>"
    )
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(document, encoding="utf-8")
    return {
        "schema": "certvic.cvpr.review_exclusion_html.v1",
        "excluded_rows": len(rows),
        "sha256": sha256_file(out),
        "paper_evidence": False,
    }
