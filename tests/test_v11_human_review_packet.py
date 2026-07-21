from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

from scripts.build_v11_human_review_packet import (
    ADJUDICATION_COLUMNS,
    RATING_FIELDS,
    SHEET_COLUMNS,
    TrackSpec,
    build_packet,
)
from scripts.validate_v11_human_review import validate_packet


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, tuple[TrackSpec, ...]]:
    root = tmp_path / "repo"
    rows = []
    for index in range(1, 5):
        original = root / "assets" / f"raw_item_{index}_original.jpg"
        edited = root / "assets" / f"raw_item_{index}_edited.jpg"
        original.parent.mkdir(parents=True, exist_ok=True)
        original.write_bytes(f"original-{index}".encode())
        edited.write_bytes(f"edited-{index}".encode())
        rows.append(
            {
                "item_id": f"raw_item_{index}",
                "original_image_path": f"assets/raw_item_{index}_original.jpg",
                "edited_image_path": f"assets/raw_item_{index}_edited.jpg",
                "question_edited": f"Is target {index} visible?",
                "required_change": "change" if index < 3 else "no_change",
            }
        )
    _write_jsonl(root / "inputs/intervention.jsonl", rows[:2])
    _write_jsonl(root / "inputs/control.jsonl", rows[2:])
    _write_jsonl(root / "inputs/strict.jsonl", rows[3:])
    _write_jsonl(root / "inputs/selection.jsonl", [{"item_id": "raw_item_3"}])
    tracks = (
        TrackSpec("intervention91", "inputs/intervention.jsonl", 2),
        TrackSpec("control94", "inputs/control.jsonl", 2),
        TrackSpec("strict_control30", "inputs/strict.jsonl", 1),
        TrackSpec(
            "diagnostic_subset12",
            "inputs/control.jsonl",
            1,
            selection_manifest="inputs/selection.jsonl",
            selection_note="observed_qwen_v1_answer_flip",
        ),
    )
    return root, tracks


def _rewrite_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _complete_rater_sheets(packet: Path, disagree: bool = False) -> str | None:
    disagreement_id = None
    for track_dir in sorted((packet / "reviewer_bundle/tracks").iterdir()):
        for filename, reviewer_code in (("rater_1.csv", "RATER_A"), ("rater_2.csv", "RATER_B")):
            path = track_dir / filename
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            for row in rows:
                row.update(
                    {
                        "prompt_unambiguous": "yes",
                        "image_answerable": "yes",
                        "target_visible_a": "yes",
                        "target_visible_b": "no",
                        "target_unaffected": (
                            "not_applicable" if track_dir.name == "intervention91" else "yes"
                        ),
                        "expected_answer_relation_valid": "yes",
                        "expected_answer_unchanged": (
                            "not_applicable" if track_dir.name == "intervention91" else "yes"
                        ),
                        "perturbation_acceptable": "yes",
                        "artifact_severity": "none",
                        "retention_decision": "retain",
                        "confidence": "high",
                        "reviewer_code": reviewer_code,
                        "reviewed_at_utc": "2026-07-12T00:00:00Z",
                    }
                )
            if disagree and filename == "rater_2.csv" and track_dir.name == "intervention91":
                rows[0]["retention_decision"] = "exclude"
                disagreement_id = rows[0]["blind_pair_id"]
            _rewrite_csv(path, rows, SHEET_COLUMNS)
    return disagreement_id


def test_build_is_deterministic_portable_and_outcome_blind(tmp_path: Path) -> None:
    root, tracks = _fixture(tmp_path)
    first = root / "packet_a"
    second = root / "packet_b"
    manifest_a = build_packet(root, first, seed=1234, tracks=tracks)
    manifest_b = build_packet(root, second, seed=1234, tracks=tracks)

    assert manifest_a["n_tracks"] == 4
    assert manifest_a["n_unique_review_rows"] == 6
    assert manifest_a["n_copied_images"] == 12
    assert manifest_a["reviewer_zip_sha256"] == manifest_b["reviewer_zip_sha256"]
    assert {
        "target_unaffected",
        "expected_answer_unchanged",
        "perturbation_acceptable",
        "prompt_unambiguous",
        "image_answerable",
        "retention_decision",
        "confidence",
    }.issubset(RATING_FIELDS)
    assert (first / manifest_a["reviewer_zip"]).read_bytes() == (
        second / manifest_b["reviewer_zip"]
    ).read_bytes()

    with zipfile.ZipFile(first / manifest_a["reviewer_zip"]) as archive:
        names = archive.namelist()
        assert names
        assert not any("coordinator" in name.lower() or "key.csv" in name.lower() for name in names)
        text = "\n".join(
            archive.read(name).decode()
            for name in names
            if Path(name).suffix.lower() in {".csv", ".json", ".md"}
        ).lower()
    assert "raw_item_" not in text
    assert "/users/" not in text
    assert "qwen2_5_vl_7b" not in text
    assert "observed_qwen_v1_answer_flip" not in text
    reviewer_manifest = json.loads(
        (first / "reviewer_bundle/reviewer_manifest.json").read_text(encoding="utf-8")
    )
    assert reviewer_manifest["public_release_allowed"] is False
    assert reviewer_manifest["distribution_status"] == "PRIVATE_COORDINATED_REVIEW_ONLY"
    coordinator_manifest = json.loads(
        (first / "coordinator_only/coordinator_manifest.json").read_text(encoding="utf-8")
    )
    assert "disjoint rater pools" in coordinator_manifest["overlap_control"][
        "permitted_alternative"
    ]


def test_blank_templates_are_allowed_only_explicitly(tmp_path: Path) -> None:
    root, tracks = _fixture(tmp_path)
    packet = root / "packet"
    build_packet(root, packet, tracks=tracks)

    permitted = validate_packet(packet, allow_blank=True, write_report=False)
    refused = validate_packet(packet, allow_blank=False, write_report=False)
    assert permitted["valid"] is True
    assert permitted["status"] == "PENDING_BLANK_TEMPLATES"
    assert permitted["agreement_computed"] is False
    assert all(track["agreement"] is None for track in permitted["tracks"])
    assert refused["valid"] is False
    assert any("human review is blank" in error for error in refused["errors"])


def test_completed_independent_sheets_compute_agreement(tmp_path: Path) -> None:
    root, tracks = _fixture(tmp_path)
    packet = root / "packet"
    build_packet(root, packet, tracks=tracks)
    _complete_rater_sheets(packet)

    report = validate_packet(packet, write_report=False)
    assert report["valid"] is True
    assert report["review_complete"] is True
    assert report["agreement_computed"] is True
    assert report["paper_evidence"] is False
    assert all(track["independent_reviewer_codes"] for track in report["tracks"])
    assert all(
        metric["percent_agreement"] == 100.0
        for track in report["tracks"]
        for metric in track["agreement"].values()
    )


def test_disagreement_requires_completed_adjudication(tmp_path: Path) -> None:
    root, tracks = _fixture(tmp_path)
    packet = root / "packet"
    build_packet(root, packet, tracks=tracks)
    disagreement_id = _complete_rater_sheets(packet, disagree=True)

    pending = validate_packet(packet, write_report=False)
    assert pending["valid"] is False
    assert pending["agreement_computed"] is True
    assert disagreement_id is not None

    path = packet / "reviewer_bundle/tracks/intervention91/adjudication.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    row = next(row for row in rows if row["blind_pair_id"] == disagreement_id)
    row.update(
        {
            "final_prompt_unambiguous": "yes",
            "final_image_answerable": "yes",
            "final_target_visible_a": "yes",
            "final_target_visible_b": "no",
            "final_target_unaffected": "not_applicable",
            "final_expected_answer_relation_valid": "yes",
            "final_expected_answer_unchanged": "not_applicable",
            "final_perturbation_acceptable": "yes",
            "final_artifact_severity": "none",
            "final_retention_decision": "retain",
            "final_confidence": "high",
            "adjudicator_code": "ADJUDICATOR_C",
            "adjudicated_at_utc": "2026-07-12T01:00:00+00:00",
        }
    )
    _rewrite_csv(path, rows, ADJUDICATION_COLUMNS)

    complete = validate_packet(packet, write_report=False)
    assert complete["valid"] is True
    assert complete["review_complete"] is True
    assert complete["agreement_computed"] is True


def test_same_reviewer_code_is_rejected_without_iaa(tmp_path: Path) -> None:
    root, tracks = _fixture(tmp_path)
    packet = root / "packet"
    build_packet(root, packet, tracks=tracks)
    _complete_rater_sheets(packet)
    for path in (packet / "reviewer_bundle/tracks").glob("*/rater_2.csv"):
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            row["reviewer_code"] = "RATER_A"
        _rewrite_csv(path, rows, SHEET_COLUMNS)

    report = validate_packet(packet, write_report=False)
    assert report["valid"] is False
    assert report["agreement_computed"] is False
    assert any("distinct reviewer codes" in error for error in report["errors"])
    assert all(field in RATING_FIELDS for field in report["tracks"][0]["agreement"] or [])
