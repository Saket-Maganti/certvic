"""Single fail-closed CLI for qualification, review, agreement, and adjudication."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from certvic.cvpr.adjudication import extract_disagreements, finalize_inclusion
from certvic.cvpr.agreement import agreement_report
from certvic.cvpr.human_review import TRACKS, judgment_fields
from certvic.cvpr.review_packets import build_visual_packet
from certvic.cvpr.transactional import read_jsonl
from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.review_ops import (
    append_timeline,
    assign_adjudicator,
    exclusion_html,
    packet_diff,
    packet_inventory,
    qualification_is_current,
    reviewer_progress,
    verify_blind_ids,
)


YES_NO = {"yes", "no", "true", "false", "accept", "reject", "1", "0"}
CONFIDENCE = {"low", "medium", "high"}


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def score_qualification(
    response_path: str | Path,
    answer_key_path: str | Path,
    *,
    reviewer_id: str,
    minimum_score_fraction: float = 0.8,
    validity_days: int = 180,
) -> dict[str, Any]:
    if not reviewer_id.strip():
        raise ValueError("reviewer identity is required")
    with Path(response_path).open(encoding="utf-8", newline="") as handle:
        responses = {row["question_id"]: row.get("decision", "").strip().upper()
                     for row in csv.DictReader(handle)}
    with Path(answer_key_path).open(encoding="utf-8", newline="") as handle:
        answers = {row["question_id"]: row["answer"].strip().upper()
                   for row in csv.DictReader(handle)}
    if set(responses) != set(answers) or any(not value for value in responses.values()):
        raise ValueError("qualification response is incomplete or has unexpected question IDs")
    correct = sum(responses[key] == value for key, value in answers.items())
    score = correct / len(answers)
    recorded = datetime.now(timezone.utc)
    return {
        "schema": "certvic.cvpr.reviewer_qualification.v1",
        "reviewer_identity_sha256": hashlib.sha256(reviewer_id.strip().encode()).hexdigest(),
        "reviewer_role": "INDEPENDENT_RATER",
        "qualification_version": "certvic.cvpr.reviewer_qualification.v1",
        "score_fraction": score,
        "threshold": minimum_score_fraction,
        "qualified": score >= minimum_score_fraction,
        "response_sha256": _sha(response_path),
        "answer_key_sha256": _sha(answer_key_path),
        "recorded_at_utc": recorded.isoformat(),
        "expires_at_utc": (recorded + timedelta(days=validity_days)).isoformat(),
        "paper_evidence": False,
    }


def validate_completed_sheet(
    sheet_path: str | Path,
    *,
    track: str,
    qualification: dict[str, Any],
    packet_manifest_path: str | Path,
) -> dict[str, Any]:
    if qualification.get("qualified") is not True:
        raise ValueError("reviewer did not pass the frozen qualification threshold")
    if not qualification_is_current(qualification):
        raise ValueError("reviewer qualification is expired or lacks a valid expiry")
    fields = judgment_fields(track)
    with Path(sheet_path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        observed_fields = set(reader.fieldnames or [])
    if observed_fields != {"blind_pair_id", *fields}:
        raise ValueError("review sheet columns differ from the frozen track schema")
    ids = [str(row["blind_pair_id"]) for row in rows]
    if not ids or len(ids) != len(set(ids)) or any(not value for value in ids):
        raise ValueError("review sheet has blank or duplicate pair IDs")
    errors: list[str] = []
    for index, row in enumerate(rows, start=2):
        for field in fields:
            value = str(row.get(field, "")).strip().lower()
            if not value:
                errors.append(f"row {index}: blank {field}")
            elif field == "confidence" and value not in CONFIDENCE:
                errors.append(f"row {index}: invalid confidence")
            elif field not in {"confidence", "reason_code"} and value not in YES_NO:
                errors.append(f"row {index}: invalid {field}")
    packet = json.loads(Path(packet_manifest_path).read_text(encoding="utf-8"))
    if packet.get("track") != track or tuple(packet.get("judgment_fields", [])) != fields:
        errors.append("packet manifest track/schema mismatch")
    template_ids: set[str] = set()
    for name in ("rater_1.csv", "rater_2.csv"):
        template = Path(packet_manifest_path).parent / name
        if template.is_file():
            with template.open(encoding="utf-8", newline="") as handle:
                template_ids = {str(row.get("blind_pair_id", "")) for row in csv.DictReader(handle)}
            break
    if template_ids and set(ids) != template_ids:
        errors.append("review sheet item universe differs from immutable packet")
    return {
        "schema": "certvic.cvpr.completed_review_validation.v1",
        "passed": not errors, "errors": errors, "rows": len(rows), "track": track,
        "sheet_sha256": _sha(sheet_path),
        "reviewer_identity_sha256": qualification["reviewer_identity_sha256"],
        "packet_manifest_sha256": _sha(packet_manifest_path), "paper_evidence": False,
        "qualification_sha256": sha256_bytes(canonical_json_bytes(qualification)),
        "item_universe_sha256": sha256_bytes(canonical_json_bytes(sorted(ids))),
    }


def validate_adjudication(
    adjudication_sheet: str | Path,
    disagreement_packet: str | Path,
    agreement_artifact: str | Path,
    adjudicator_role_artifact: str | Path,
    *,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    """Bind a completed adjudication to exact rater inputs and an authorized adjudicator."""
    agreement = json.loads(Path(agreement_artifact).read_text(encoding="utf-8"))
    role = json.loads(Path(adjudicator_role_artifact).read_text(encoding="utf-8"))
    authorized = role.get("authorized") is True or (
        role.get("qualified") is True and role.get("role") in {"ADJUDICATOR", "COORDINATOR"}
    )
    if not authorized or not role.get("adjudicator_identity_sha256"):
        raise ValueError("adjudicator role/qualification artifact is not authorized")
    with Path(disagreement_packet).open(encoding="utf-8", newline="") as handle:
        disagreement_rows = list(csv.DictReader(handle))
    with Path(adjudication_sheet).open(encoding="utf-8", newline="") as handle:
        adjudication_rows = list(csv.DictReader(handle))
    disagreements = {str(row.get("blind_pair_id", "")): row for row in disagreement_rows}
    adjudicated = {str(row.get("blind_pair_id", "")): row for row in adjudication_rows}
    if "" in disagreements or len(disagreements) != len(disagreement_rows):
        raise ValueError("disagreement packet has blank or duplicate IDs")
    if set(adjudicated) != set(disagreements):
        raise ValueError("adjudication sheet does not exactly match the disagreement packet")
    unresolved: list[str] = []
    for pair_id, disagreement in disagreements.items():
        changed = set(str(disagreement.get("disagreement_fields", "")).split("|"))
        for field in changed & set(fields):
            if not str(adjudicated[pair_id].get(field, "")).strip():
                unresolved.append(f"{pair_id}:{field}")
    result = {
        "schema": "certvic.cvpr.adjudication_validation.v1",
        "passed": not unresolved,
        "unresolved": unresolved,
        "disagreements": len(disagreements),
        "input_sheet_sha256": agreement.get("input_sheet_sha256"),
        "agreement_artifact_sha256": _sha(agreement_artifact),
        "disagreement_packet_sha256": _sha(disagreement_packet),
        "adjudication_sheet": str(Path(adjudication_sheet).resolve()),
        "adjudication_sheet_sha256": _sha(adjudication_sheet),
        "adjudicator_identity_sha256": role["adjudicator_identity_sha256"],
        "adjudicator_role_artifact_sha256": _sha(adjudicator_role_artifact),
        "all_disagreements_resolved": not unresolved,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "paper_evidence": False,
    }
    return result


def finalize_review_state(
    *,
    rater_1: str | Path,
    rater_2: str | Path,
    rater_1_validation: str | Path,
    rater_2_validation: str | Path,
    rater_1_qualification: str | Path,
    rater_2_qualification: str | Path,
    agreement_artifact: str | Path,
    adjudication_artifact: str | Path,
    coordinator_key: str | Path,
    packet_manifest: str | Path,
    packet_root: str | Path,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    """Finalize only a qualification-, independence-, agreement-, and provenance-bound review."""
    sheet_hashes = {"rater_1": _sha(rater_1), "rater_2": _sha(rater_2)}
    if sheet_hashes["rater_1"] == sheet_hashes["rater_2"]:
        raise ValueError("raw rater sheets must differ byte-for-byte")
    validations = {
        "rater_1": json.loads(Path(rater_1_validation).read_text(encoding="utf-8")),
        "rater_2": json.loads(Path(rater_2_validation).read_text(encoding="utf-8")),
    }
    qualifications = {
        "rater_1": json.loads(Path(rater_1_qualification).read_text(encoding="utf-8")),
        "rater_2": json.loads(Path(rater_2_qualification).read_text(encoding="utf-8")),
    }
    for role in ("rater_1", "rater_2"):
        if qualifications[role].get("qualified") is not True:
            raise ValueError(f"{role} did not pass qualification")
        if qualifications[role].get("qualification_version") != "certvic.cvpr.reviewer_qualification.v1":
            raise ValueError(f"{role} qualification version mismatch")
        if validations[role].get("passed") is not True:
            raise ValueError(f"{role} completed-sheet validation failed")
        if validations[role].get("sheet_sha256") != sheet_hashes[role]:
            raise ValueError(f"{role} validation does not bind the supplied raw sheet")
        if validations[role].get("reviewer_identity_sha256") != qualifications[role].get(
            "reviewer_identity_sha256"
        ):
            raise ValueError(f"{role} validation and qualification identities differ")
        if validations[role].get("qualification_sha256") != sha256_bytes(
            canonical_json_bytes(qualifications[role])
        ):
            raise ValueError(f"{role} validation does not bind the qualification artifact")
    identities = [qualifications[role]["reviewer_identity_sha256"] for role in qualifications]
    if len(set(identities)) != 2:
        raise ValueError("Rater 1 and Rater 2 identities must be distinct")
    qualification_hashes = {
        role: _sha(path) for role, path in {
            "rater_1": rater_1_qualification, "rater_2": rater_2_qualification,
        }.items()
    }
    if len(set(qualification_hashes.values())) != 2:
        raise ValueError("rater qualification artifacts must be distinct")
    packet_hash = _sha(packet_manifest)
    if any(value.get("packet_manifest_sha256") != packet_hash for value in validations.values()):
        raise ValueError("both completed sheets must bind to the same immutable packet")
    if validations["rater_1"].get("item_universe_sha256") != validations["rater_2"].get(
        "item_universe_sha256"
    ):
        raise ValueError("validated rater sheets have different item universes")
    agreement = json.loads(Path(agreement_artifact).read_text(encoding="utf-8"))
    if agreement.get("rater_identities_distinct") is not True:
        raise ValueError("agreement artifact does not prove distinct raters")
    if set(agreement.get("rater_identity_hashes", {}).values()) != set(identities):
        raise ValueError("agreement rater identities do not match qualified reviewers")
    if agreement.get("input_sheet_sha256") != sheet_hashes:
        raise ValueError("agreement was not computed from the exact validated sheets")
    adjudication = json.loads(Path(adjudication_artifact).read_text(encoding="utf-8"))
    if adjudication.get("passed") is not True or adjudication.get(
        "all_disagreements_resolved"
    ) is not True:
        raise ValueError("adjudication is incomplete or invalid")
    if adjudication.get("input_sheet_sha256") != sheet_hashes:
        raise ValueError("adjudication provenance does not bind the validated sheets")
    if adjudication.get("agreement_artifact_sha256") != _sha(agreement_artifact):
        raise ValueError("adjudication does not bind the supplied agreement artifact")
    sheet = Path(str(adjudication.get("adjudication_sheet", "")))
    if not sheet.is_file() or _sha(sheet) != adjudication.get("adjudication_sheet_sha256"):
        raise ValueError("adjudication sheet bytes do not match the validation artifact")
    result = finalize_inclusion(
        rater_1, rater_2, sheet, coordinator_key, packet_manifest,
        packet_root=packet_root, fields=fields,
    )
    if result["status"] != "FINAL_INCLUSION_VALIDATED":
        raise ValueError("lower-level inclusion finalization remains unresolved")
    provenance = {
        "reviewer_identity_hashes": {role: qualifications[role]["reviewer_identity_sha256"]
                                     for role in qualifications},
        "qualification_artifact_hashes": qualification_hashes,
        "validation_artifact_hashes": {
            "rater_1": _sha(rater_1_validation), "rater_2": _sha(rater_2_validation),
        },
        "packet_hash": packet_hash,
        "rater_sheet_hashes": sheet_hashes,
        "agreement_artifact_hash": _sha(agreement_artifact),
        "adjudication_artifact_hash": _sha(adjudication_artifact),
        "adjudicator_identity_sha256": adjudication["adjudicator_identity_sha256"],
    }
    for row in result["ledger"]:
        row.update({
            "packet_hash": packet_hash,
            "rater_artifact_hashes": sheet_hashes,
            "adjudication_artifact_hash": provenance["adjudication_artifact_hash"],
        })
    result["schema"] = "certvic.cvpr.final_review_state.v2"
    result["provenance"] = provenance
    result["review_timeline"] = [
        {"stage": "qualification", "artifact_hashes": qualification_hashes},
        {"stage": "sheet_validation", "artifact_hashes": provenance["validation_artifact_hashes"]},
        {"stage": "agreement", "artifact_hash": provenance["agreement_artifact_hash"]},
        {"stage": "adjudication", "artifact_hash": provenance["adjudication_artifact_hash"]},
        {"stage": "finalization", "status": "FINAL_INCLUSION_VALIDATED"},
    ]
    result["final_ledger_sha256"] = sha256_bytes(canonical_json_bytes(result["ledger"]))
    payload = {key: value for key, value in result.items() if key != "final_artifact_sha256"}
    result["final_artifact_sha256"] = sha256_bytes(canonical_json_bytes(payload))
    return result


def _write(path: str | Path, value: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CertVIC human review operations")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--items", required=True)
    build.add_argument("--track", choices=TRACKS, required=True)
    build.add_argument("--out-dir", required=True)
    build.add_argument("--seed", type=int, default=12013)
    qualify = sub.add_parser("qualify")
    qualify.add_argument("--response", required=True)
    qualify.add_argument("--answer-key", required=True)
    qualify.add_argument("--reviewer-id", required=True)
    qualify.add_argument("--out", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--sheet", required=True)
    validate.add_argument("--track", choices=TRACKS, required=True)
    validate.add_argument("--qualification", required=True)
    validate.add_argument("--packet-manifest", required=True)
    validate.add_argument("--out", required=True)
    agree = sub.add_parser("agreement")
    agree.add_argument("--rater-1", required=True)
    agree.add_argument("--rater-2", required=True)
    agree.add_argument("--rater-1-id", required=True)
    agree.add_argument("--rater-2-id", required=True)
    agree.add_argument("--track", choices=TRACKS, required=True)
    agree.add_argument("--out", required=True)
    adjudicate = sub.add_parser("adjudication-packet")
    adjudicate.add_argument("--rater-1", required=True)
    adjudicate.add_argument("--rater-2", required=True)
    adjudicate.add_argument("--track", choices=TRACKS, required=True)
    adjudicate.add_argument("--out", required=True)
    validate_adjudication_parser = sub.add_parser("validate-adjudication")
    validate_adjudication_parser.add_argument("--sheet", required=True)
    validate_adjudication_parser.add_argument("--disagreement-packet", required=True)
    validate_adjudication_parser.add_argument("--agreement", required=True)
    validate_adjudication_parser.add_argument("--adjudicator-role-artifact", required=True)
    validate_adjudication_parser.add_argument("--track", choices=TRACKS, required=True)
    validate_adjudication_parser.add_argument("--out", required=True)
    finalize = sub.add_parser("finalize")
    finalize.add_argument("--rater-1", required=True)
    finalize.add_argument("--rater-2", required=True)
    finalize.add_argument("--rater-1-validation", required=True)
    finalize.add_argument("--rater-2-validation", required=True)
    finalize.add_argument("--rater-1-qualification", required=True)
    finalize.add_argument("--rater-2-qualification", required=True)
    finalize.add_argument("--agreement", required=True)
    finalize.add_argument("--adjudication-artifact", required=True)
    finalize.add_argument("--coordinator-key", required=True)
    finalize.add_argument("--packet-manifest", required=True)
    finalize.add_argument("--packet-root", required=True)
    finalize.add_argument("--track", choices=TRACKS, required=True)
    finalize.add_argument("--out", required=True)
    inventory = sub.add_parser("inventory")
    inventory.add_argument("--packet-root", required=True)
    progress = sub.add_parser("progress")
    progress.add_argument("--template", required=True)
    progress.add_argument("--completed", required=True)
    progress.add_argument("--track", choices=TRACKS, required=True)
    blind = sub.add_parser("verify-blind-ids")
    blind.add_argument("--coordinator-key", required=True)
    blind.add_argument("--sheet", action="append", required=True)
    assignment = sub.add_parser("assign-adjudicator")
    assignment.add_argument("--adjudicator-id", required=True)
    assignment.add_argument("--qualification", required=True)
    assignment.add_argument("--out", required=True)
    timeline = sub.add_parser("timeline")
    timeline.add_argument("--timeline", required=True)
    timeline.add_argument("--stage", required=True)
    timeline.add_argument("--artifact", required=True)
    timeline.add_argument("--actor-role", required=True)
    diff = sub.add_parser("packet-diff")
    diff.add_argument("--left", required=True)
    diff.add_argument("--right", required=True)
    exclusions = sub.add_parser("exclusion-html")
    exclusions.add_argument("--final-state", required=True)
    exclusions.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        result = build_visual_packet(read_jsonl(args.items), args.track, args.out_dir, seed=args.seed)
    elif args.command == "qualify":
        result = score_qualification(args.response, args.answer_key, reviewer_id=args.reviewer_id)
        _write(args.out, result)
    elif args.command == "validate":
        qualification = json.loads(Path(args.qualification).read_text(encoding="utf-8"))
        result = validate_completed_sheet(args.sheet, track=args.track, qualification=qualification,
                                          packet_manifest_path=args.packet_manifest)
        _write(args.out, result)
    elif args.command == "agreement":
        result = agreement_report(args.rater_1, args.rater_2, rater_1_id=args.rater_1_id,
                                  rater_2_id=args.rater_2_id,
                                  fields=judgment_fields(args.track))
        _write(args.out, result)
    elif args.command == "adjudication-packet":
        result = extract_disagreements(args.rater_1, args.rater_2, args.out,
                                       fields=judgment_fields(args.track))
    elif args.command == "validate-adjudication":
        result = validate_adjudication(
            args.sheet, args.disagreement_packet, args.agreement,
            args.adjudicator_role_artifact, fields=judgment_fields(args.track),
        )
        _write(args.out, result)
    elif args.command == "finalize":
        result = finalize_review_state(
            rater_1=args.rater_1, rater_2=args.rater_2,
            rater_1_validation=args.rater_1_validation,
            rater_2_validation=args.rater_2_validation,
            rater_1_qualification=args.rater_1_qualification,
            rater_2_qualification=args.rater_2_qualification,
            agreement_artifact=args.agreement,
            adjudication_artifact=args.adjudication_artifact,
            coordinator_key=args.coordinator_key, packet_manifest=args.packet_manifest,
            packet_root=args.packet_root, fields=judgment_fields(args.track),
        )
        _write(args.out, result)
    elif args.command == "inventory":
        result = packet_inventory(args.packet_root)
    elif args.command == "progress":
        result = reviewer_progress(args.template, args.completed, judgment_fields(args.track))
    elif args.command == "verify-blind-ids":
        result = verify_blind_ids(args.coordinator_key, args.sheet)
    elif args.command == "assign-adjudicator":
        result = assign_adjudicator(args.adjudicator_id, qualification_hash=_sha(args.qualification))
        _write(args.out, result)
    elif args.command == "timeline":
        result = append_timeline(
            args.timeline, stage=args.stage, artifact_path=args.artifact, actor_role=args.actor_role
        )
    elif args.command == "packet-diff":
        result = packet_diff(args.left, args.right)
    else:
        result = exclusion_html(args.final_state, args.out)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("passed", True) and not str(result.get("status", "")).startswith("BLOCKED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
