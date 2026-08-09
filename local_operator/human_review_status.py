"""One-command, fail-closed status and infrastructure for genuine two-rater review."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from local_operator.cvpr2027_common import (  # noqa: E402
    REPO,
    REPORT_ROOT,
    sha256_file,
    write_csv,
    write_json,
)


JUDGMENT_FIELDS = [
    "target_unaffected",
    "expected_answer_unchanged",
    "perturbation_acceptable",
    "image_answerable",
    "prompt_unambiguous",
    "retain",
    "confidence",
    "reason_code",
]
FORBIDDEN_BLIND_FIELDS = {
    "provider",
    "provider_name",
    "model",
    "model_output",
    "raw_output",
    "parsed_answer",
    "failure_label",
    "flip",
}


def _csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _completed(rows: list[dict[str, str]]) -> bool:
    return bool(rows) and all(
        row.get("blind_pair_id")
        and all(str(row.get(field, "")).strip() for field in JUDGMENT_FIELDS)
        for row in rows
    )


def _qualification(path: Path) -> tuple[bool, str | None, list[str]]:
    if not path.is_file():
        return False, None, ["missing qualification artifact"]
    value = json.loads(path.read_text(encoding="utf-8"))
    errors = []
    if value.get("passed") is not True:
        errors.append("qualification did not pass")
    identity = value.get("rater_identity_sha256")
    if not isinstance(identity, str) or len(identity) != 64:
        errors.append("qualification lacks a hashed rater identity")
    if float(value.get("score_fraction", 0.0)) < float(value.get("minimum_score_fraction", 0.8)):
        errors.append("qualification score is below policy")
    return not errors, identity if isinstance(identity, str) else None, errors


def _validate_sheet(rows: list[dict[str, str]], expected_ids: set[str]) -> list[str]:
    errors = []
    ids = [str(row.get("blind_pair_id", "")) for row in rows]
    if not ids or "" in ids or len(ids) != len(set(ids)):
        errors.append("blank or duplicate blind_pair_id")
    if expected_ids and set(ids) != expected_ids:
        errors.append("review sheet row universe differs from immutable template")
    fields = set(rows[0]) if rows else set()
    forbidden = sorted(fields & FORBIDDEN_BLIND_FIELDS)
    if forbidden:
        errors.append(f"unblinded provider/output fields present: {forbidden}")
    if any(any(not str(row.get(field, "")).strip() for field in JUDGMENT_FIELDS) for row in rows):
        errors.append("review sheet has missing judgments")
    return errors


def _cohen(left: list[str], right: list[str]) -> float:
    observed = sum(a == b for a, b in zip(left, right, strict=True)) / len(left)
    labels = set(left) | set(right)
    expected = sum(
        (left.count(label) / len(left)) * (right.count(label) / len(right))
        for label in labels
    )
    return 1.0 if expected == 1 and observed == 1 else (observed - expected) / (1 - expected)


def _krippendorff_nominal(left: list[str], right: list[str]) -> float:
    matrix = np.asarray([left, right], dtype=object)
    observed_disagreement = float((matrix[0] != matrix[1]).mean())
    values = matrix.reshape(-1).tolist()
    counts = Counter(values)
    total = len(values)
    expected_disagreement = 1 - sum((count / total) ** 2 for count in counts.values())
    if expected_disagreement == 0:
        return 1.0 if observed_disagreement == 0 else math.nan
    return 1 - observed_disagreement / expected_disagreement


def agreement_report(
    left_rows: list[dict[str, str]], right_rows: list[dict[str, str]], *, draws: int = 2000
) -> dict[str, Any]:
    left_by_id = {row["blind_pair_id"]: row for row in left_rows}
    right_by_id = {row["blind_pair_id"]: row for row in right_rows}
    ids = sorted(left_by_id)
    per_field = {}
    disagreements = set()
    rng = np.random.default_rng(12013)
    for field in JUDGMENT_FIELDS:
        left = [left_by_id[item][field] for item in ids]
        right = [right_by_id[item][field] for item in ids]
        agreement = np.asarray([a == b for a, b in zip(left, right, strict=True)], dtype=float)
        bootstrap = rng.choice(agreement, size=(draws, len(agreement)), replace=True).mean(axis=1)
        per_field[field] = {
            "percent_agreement": float(agreement.mean()),
            "cohen_kappa": _cohen(left, right),
            "krippendorff_alpha_nominal": _krippendorff_nominal(left, right),
            "bootstrap_95": [
                float(np.quantile(bootstrap, 0.025)),
                float(np.quantile(bootstrap, 0.975)),
            ],
            "disagreement_rate": float(1 - agreement.mean()),
        }
        disagreements.update(
            item for item, a, b in zip(ids, left, right, strict=True) if a != b
        )
    return {
        "schema": "certvic.cvpr2027.human_agreement.v1",
        "rows": len(ids),
        "per_field": per_field,
        "items_requiring_adjudication": sorted(disagreements),
        "adjudication_rate": len(disagreements) / len(ids),
        "confidence_distributions": {
            "rater_1": dict(Counter(left_by_id[item]["confidence"] for item in ids)),
            "rater_2": dict(Counter(right_by_id[item]["confidence"] for item in ids)),
        },
        "reason_code_distributions": {
            "rater_1": dict(Counter(left_by_id[item]["reason_code"] for item in ids)),
            "rater_2": dict(Counter(right_by_id[item]["reason_code"] for item in ids)),
        },
        "paper_evidence": False,
    }


def initialize_infrastructure(output: Path) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    qualification_rows = [
        {
            "question_id": f"Q{index}",
            "scenario": scenario,
            "rater_answer": "",
        }
        for index, scenario in enumerate(
            [
                "Remote texture patch; target and answer remain intact",
                "Patch touches target boundary",
                "Edit changes the expected answer",
                "Image is too ambiguous to answer",
                "A hidden model output disagrees with the candidate answer",
                "Pair has a conspicuous compression artifact in one arm",
                "Question names an object not visible in either image",
                "Both images are answerable and the perturbation is remote",
                "Reviewer recognizes the source image from elsewhere",
                "Coordinator requests a favorable label",
            ],
            start=1,
        )
    ]
    paths = [
        write_csv(
            output / "rater_qualification_packet.csv",
            qualification_rows,
            ["question_id", "scenario", "rater_answer"],
        ),
        write_csv(
            output / "coordinator_qualification_answer_key.csv",
            [
                {"question_id": "Q1", "answer": "ACCEPT"},
                {"question_id": "Q2", "answer": "REJECT_TARGET_CONTAMINATION"},
                {"question_id": "Q3", "answer": "REJECT_ANSWER_CHANGED"},
                {"question_id": "Q4", "answer": "REJECT_UNANSWERABLE"},
                {"question_id": "Q5", "answer": "IGNORE_MODEL_OUTPUT"},
                {"question_id": "Q6", "answer": "REJECT_ARTIFACT"},
                {"question_id": "Q7", "answer": "REJECT_PROMPT_AMBIGUITY"},
                {"question_id": "Q8", "answer": "ACCEPT"},
                {"question_id": "Q9", "answer": "DISCLOSE_AND_CONTINUE_BLIND"},
                {"question_id": "Q10", "answer": "REJECT_COORDINATOR_PRESSURE"},
            ],
            ["question_id", "answer"],
        ),
        write_json(
            output / "qualification_policy.json",
            {
                "schema": "certvic.cvpr2027.qualification_policy.v1",
                "minimum_score_fraction": 0.8,
                "two_distinct_raters_required": True,
                "outcome_blinding_required": True,
                "answer_key_separate_from_rater_packet": True,
                "paper_evidence": False,
            },
        ),
        write_csv(
            output / "review_assignment_template.csv",
            [],
            ["blind_pair_id", "rater_1_identity_sha256", "rater_2_identity_sha256"],
        ),
        write_csv(
            output / "raw_sheet_preservation_manifest.csv",
            [],
            ["role", "artifact_path", "sha256", "received_at_utc", "immutable_copy_path"],
        ),
        write_json(
            output / "review_timeline.template.json",
            {
                "schema": "certvic.cvpr2027.review_timeline.v1",
                "events": [],
                "required_order": [
                    "PACKET_FROZEN",
                    "RATER_1_RECEIVED",
                    "RATER_2_RECEIVED",
                    "ADJUDICATION_COMPLETE",
                    "FINAL_INCLUSION_COMPILED",
                    "PROVIDER_OUTCOMES_UNBLINDED",
                ],
                "paper_evidence": False,
            },
        ),
    ]
    return paths


def score_qualification(
    sheet: Path, answer_key: Path, *, rater_id: str, output: Path
) -> dict[str, Any]:
    rows = _csv(sheet)
    key = {row["question_id"]: row["answer"] for row in _csv(answer_key)}
    if not rows or set(row["question_id"] for row in rows) != set(key):
        raise ValueError("qualification row universe differs from answer key")
    correct = sum(row["rater_answer"].strip() == key[row["question_id"]] for row in rows)
    fraction = correct / len(rows)
    result = {
        "schema": "certvic.cvpr2027.rater_qualification.v1",
        "rater_identity_sha256": hashlib.sha256(rater_id.strip().encode()).hexdigest(),
        "correct": correct,
        "total": len(rows),
        "score_fraction": fraction,
        "minimum_score_fraction": 0.8,
        "passed": fraction >= 0.8,
        "source_sheet_sha256": sha256_file(sheet),
        "answer_key_sha256": sha256_file(answer_key),
        "paper_evidence": False,
    }
    write_json(output, result)
    return result


def status(review_root: Path) -> dict[str, Any]:
    template = _csv(review_root / "rater_1.template.csv")
    if not template:
        template = _csv(review_root / "rater_1.csv") if not _completed(_csv(review_root / "rater_1.csv")) else []
    expected_ids = {row.get("blind_pair_id", "") for row in template if row.get("blind_pair_id")}
    rater_1 = _csv(review_root / "rater_1.completed.csv")
    rater_2 = _csv(review_root / "rater_2.completed.csv")
    adjudication = _csv(review_root / "adjudication.completed.csv")
    q1, identity_1, q1_errors = _qualification(review_root / "rater_1_qualification.json")
    q2, identity_2, q2_errors = _qualification(review_root / "rater_2_qualification.json")
    errors = []
    if rater_1:
        errors.extend(f"rater_1: {error}" for error in _validate_sheet(rater_1, expected_ids))
        errors.extend(f"rater_1: {error}" for error in q1_errors)
    if rater_2:
        errors.extend(f"rater_2: {error}" for error in _validate_sheet(rater_2, expected_ids))
        errors.extend(f"rater_2: {error}" for error in q2_errors)
    if rater_1 and rater_2:
        if not q1 or not q2:
            errors.append("both completed sheets require passing qualifications")
        if identity_1 == identity_2:
            errors.append("same person cannot serve as both raters")
        if (review_root / "rater_1.completed.csv").read_bytes() == (
            review_root / "rater_2.completed.csv"
        ).read_bytes():
            errors.append("completed rater sheets are byte-identical; copied sheets rejected")
    agreement = None
    if not errors and _completed(rater_1) and _completed(rater_2):
        agreement = agreement_report(rater_1, rater_2)
        required = set(agreement["items_requiring_adjudication"])
        if required:
            if not _completed(adjudication):
                state = "WAITING_FOR_ADJUDICATION"
            else:
                adjudicated_ids = {row["blind_pair_id"] for row in adjudication}
                if not required <= adjudicated_ids:
                    errors.append("adjudication sheet omits required disagreements")
                    state = "INVALID_REVIEW_STATE"
                else:
                    state = "READY_FOR_SELECTION"
        else:
            state = "READY_FOR_SELECTION"
    elif errors:
        state = "INVALID_REVIEW_STATE"
    elif not _completed(rater_1):
        state = "WAITING_FOR_RATER_1"
    else:
        state = "WAITING_FOR_RATER_2"
    result = {
        "schema": "certvic.cvpr2027.human_review_status.v1",
        "state": state,
        "review_root": (
            review_root.relative_to(REPO).as_posix()
            if review_root.is_relative_to(REPO)
            else review_root.as_posix()
        ),
        "packet_present": (review_root / "packet_hash_manifest.json").is_file(),
        "template_rows": len(template),
        "rater_1_complete": _completed(rater_1),
        "rater_2_complete": _completed(rater_2),
        "adjudication_complete": _completed(adjudication),
        "rater_identities_distinct": identity_1 is not None and identity_1 != identity_2,
        "errors": errors,
        "agreement": agreement,
        "external_action": (
            "Mount licensed source bytes and build/freeze the blind packet before assigning rater 1."
            if not (review_root / "packet_hash_manifest.json").is_file()
            else "Follow the state-specific genuine human action; do not synthesize labels."
        ),
        "paper_evidence": False,
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--review-root",
        type=Path,
        default=REPO / "data/studies/specificity_confirmatory_cvpr/review",
    )
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--score-qualification", type=Path)
    parser.add_argument("--answer-key", type=Path)
    parser.add_argument("--rater-id")
    parser.add_argument("--qualification-out", type=Path)
    parser.add_argument("--status-out", type=Path, default=REPORT_ROOT / "human_review/STATUS.json")
    args = parser.parse_args(argv)
    if args.initialize:
        initialize_infrastructure(REPORT_ROOT / "human_review")
    if args.score_qualification:
        if not args.answer_key or not args.rater_id or not args.qualification_out:
            parser.error("qualification scoring needs --answer-key, --rater-id, and --qualification-out")
        result = score_qualification(
            args.score_qualification,
            args.answer_key,
            rater_id=args.rater_id,
            output=args.qualification_out,
        )
    else:
        result = status(args.review_root)
        write_json(args.status_out, result)
    print(json.dumps(result, sort_keys=True))
    return 2 if result.get("state") == "INVALID_REVIEW_STATE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
