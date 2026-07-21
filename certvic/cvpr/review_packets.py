"""Blinded visual review packet and immutable hash-manifest construction."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import random
import shutil
from pathlib import Path
from typing import Any

from certvic.cvpr.human_review import TRACKS, blind_id, judgment_fields


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _image_paths(item: dict[str, Any]) -> tuple[Path, Path]:
    original = Path(str(item.get("original_image_path", "")))
    edited = Path(str(item.get("edited_image_path", "")))
    if not original.is_file() or not edited.is_file():
        raise ValueError(f"missing review pair images for {item.get('item_id')}")
    return original, edited


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_visual_packet(
    items: list[dict[str, Any]],
    track: str,
    out_dir: str | Path,
    *,
    seed: int,
) -> dict[str, Any]:
    if track not in TRACKS:
        raise ValueError(f"unknown review track: {track}")
    out = Path(out_dir)
    fields_for_track = judgment_fields(track)
    if out.exists() and any(out.iterdir()):
        raise ValueError("review packet directory must be new or empty")
    images_dir = out / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    coordinator: list[dict[str, Any]] = []
    for item in items:
        item_id = str(item["item_id"])
        pair_id = blind_id(track, item_id, seed)
        original, edited = _image_paths(item)
        order = "AB" if random.Random(f"{seed}:{item_id}:order").randrange(2) == 0 else "BA"
        sources = (original, edited) if order == "AB" else (edited, original)
        destinations: list[Path] = []
        for label, source in zip(("A", "B"), sources, strict=True):
            destination = images_dir / f"{pair_id}_{label}{source.suffix.lower()}"
            shutil.copyfile(source, destination)
            destinations.append(destination)
        records.append({
            "blind_pair_id": pair_id,
            "image_a": destinations[0].relative_to(out).as_posix(),
            "image_b": destinations[1].relative_to(out).as_posix(),
            "question": str(item.get("question", item.get("prompt", ""))),
            "candidate_expected_answer": str(item.get("expected_answer", "")),
            "expected_transition": (
                f"{item.get('original_expected_answer')} -> {item.get('edited_expected_answer')}"
                if item.get("required_change") is True else "answer should remain unchanged"
            ),
        })
        coordinator.append({
            "blind_pair_id": pair_id,
            "item_id": item_id,
            "pair_order": order,
            "original_sha256": _hash(original),
            "edited_sha256": _hash(edited),
        })
    random.Random(seed).shuffle(records)
    fields = ["blind_pair_id", *fields_for_track]
    blank_rows = [{"blind_pair_id": row["blind_pair_id"],
                   **{field: "" for field in fields_for_track}} for row in records]
    _write_csv(out / "rater_1.csv", fields, blank_rows)
    _write_csv(out / "rater_2.csv", fields, blank_rows)
    _write_csv(out / "adjudication.csv", fields, blank_rows)
    _write_csv(out / "coordinator_key.csv", list(coordinator[0]) if coordinator else ["blind_pair_id"],
               coordinator)
    cards = []
    for row in records:
        questions = "".join(f"<li>{html.escape(field.replace('_', ' '))}</li>"
                            for field in fields_for_track)
        cards.append(
            '<section class="pair">'
            f"<h2>{html.escape(row['blind_pair_id'])}</h2>"
            '<div class="images">'
            f"<figure><img src=\"{html.escape(row['image_a'])}\"><figcaption>Image A</figcaption></figure>"
            f"<figure><img src=\"{html.escape(row['image_b'])}\"><figcaption>Image B</figcaption></figure>"
            "</div>"
            f"<p><b>Task question:</b> {html.escape(row['question'])}</p>"
            f"<p><b>Candidate expected answer:</b> {html.escape(row['candidate_expected_answer'])}</p>"
            f"<p><b>Expected semantic relation:</b> {html.escape(row['expected_transition'])}</p>"
            f"<ol>{questions}</ol></section>"
        )
    packet = (
        "<!doctype html><meta charset='utf-8'><title>CertVIC blinded review</title>"
        "<style>body{font-family:system-ui;max-width:1100px;margin:auto}.pair{page-break-after:always;}"
        ".images{display:flex;gap:1rem}.images figure{width:48%;margin:0}.images img{max-width:100%;"
        "max-height:520px;object-fit:contain;border:1px solid #777}</style>"
        f"<h1>CertVIC blinded visual review: {html.escape(track)}</h1>"
        "<p>Model outputs and original/edited identities are intentionally hidden.</p>"
        + "".join(cards)
    )
    (out / "review_packet.html").write_text(packet, encoding="utf-8")
    (out / "REVIEW_CODEBOOK.md").write_text(
        "# CertVIC Review Codebook\n\n"
        "Judge the visible pair and task only. Do not infer model behavior. Mark target unaffected "
        "only when the named target is unchanged; mark expected answer unchanged only when both "
        "images support the candidate answer; reject target contamination, conspicuous artifacts, "
        "ambiguity, or an unanswerable image.\n\n"
        "Examples: a remote texture patch that leaves the target intact is normally acceptable; "
        "a patch touching the target is invalid; an edit that introduces/removes answer-relevant "
        "content is invalid; ambiguous cases require a reason code and later adjudication.\n",
        encoding="utf-8",
    )
    (out / "qualification_quiz.csv").write_text(
        "question_id,scenario,decision\n"
        "Q1,Remote texture patch with intact target,\n"
        "Q2,Patch overlaps target boundary,\n"
        "Q3,Edit changes the expected answer,\n"
        "Q4,Ambiguous low-resolution target,\n"
        "Q5,Model outcome disagrees with candidate answer,\n",
        encoding="utf-8",
    )
    answer_key = out / "coordinator_qualification_answer_key.csv"
    answer_key.write_text(
        "question_id,answer,rationale\n"
        "Q1,ACCEPT,Target and answer remain intact\n"
        "Q2,REJECT,Target contamination\n"
        "Q3,REJECT,Answer invariance violated\n"
        "Q4,REJECT,Image not reliably answerable\n"
        "Q5,IGNORE_MODEL_OUTCOME,Review must remain outcome blind\n",
        encoding="utf-8",
    )
    policy = {"minimum_score_fraction": 0.8, "completion_status": "HUMAN_REVIEW_PENDING",
              "fabricated_completion": False}
    (out / "qualification_policy.json").write_text(json.dumps(policy, indent=2) + "\n")
    hash_paths = sorted(path for path in out.rglob("*") if path.is_file())
    hashes = {path.relative_to(out).as_posix(): _hash(path) for path in hash_paths}
    (out / "packet_hash_manifest.json").write_text(
        json.dumps({"schema": "certvic.cvpr.review_packet_hashes.v1", "files": hashes,
                    "track": track, "judgment_fields": list(fields_for_track),
                    "paper_evidence": False}, indent=2, sort_keys=True) + "\n"
    )
    return {"status": "HUMAN_REVIEW_PENDING", "track": track, "items": len(records),
            "packet": str(out / "review_packet.html"), "hashes": len(hashes),
            "answer_key_separate": True, "paper_evidence": False}
