"""Build the deterministic, outcome-blind CertVIC V11 human-review packet.

The reviewer bundle contains no model outputs, provider names, source item IDs, or
coordinator keys. Human response fields are intentionally blank.  The separate
``coordinator_only`` directory maps opaque review IDs back to canonical tasks.

This script does not make any scientific-evidence claim.  In particular, the
retrospective strict-control cohort and the diagnostic 12-pair subset remain
non-evidence review material regardless of whether their templates are completed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/v11_full_ceiling_audit/human_review_packet"
DEFAULT_SEED = 110_713
ZIP_DATE = (2026, 1, 1, 0, 0, 0)

RATING_FIELDS = [
    "prompt_unambiguous",
    "image_answerable",
    "target_visible_a",
    "target_visible_b",
    "target_unaffected",
    "expected_answer_relation_valid",
    "expected_answer_unchanged",
    "perturbation_acceptable",
    "artifact_severity",
    "retention_decision",
    "confidence",
]
SHEET_COLUMNS = [
    "blind_order",
    "blind_pair_id",
    "image_a",
    "image_b",
    "question",
    *RATING_FIELDS,
    "notes",
    "reviewer_code",
    "reviewed_at_utc",
]
ADJUDICATION_COLUMNS = [
    "blind_order",
    "blind_pair_id",
    *(f"final_{field}" for field in RATING_FIELDS),
    "adjudication_notes",
    "adjudicator_code",
    "adjudicated_at_utc",
]
COORDINATOR_COLUMNS = [
    "blind_pair_id",
    "source_item_id",
    "source_manifest",
    "source_manifest_sha256",
    "source_original_path",
    "source_edited_path",
    "image_a_variant",
    "image_b_variant",
    "source_original_sha256",
    "source_edited_sha256",
    "question",
    "required_change",
]


@dataclass(frozen=True)
class TrackSpec:
    track_id: str
    source_manifest: str
    expected_count: int
    selection_manifest: str | None = None
    selection_note: str | None = None


DEFAULT_TRACKS = (
    TrackSpec(
        "intervention91",
        "data/results/main_real_200/pilot_eval_tasks_reviewed_v2.jsonl",
        91,
    ),
    TrackSpec(
        "control94",
        "data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl",
        94,
    ),
    TrackSpec(
        "strict_control30",
        "data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl",
        30,
    ),
    TrackSpec(
        "diagnostic_subset12",
        "data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl",
        12,
        selection_manifest=(
            "data/results/main_real_200/v8_1_qwen_spurious_forensics/"
            "qwen_spurious_failed_12.jsonl"
        ),
        selection_note="observed_qwen_v1_answer_flip",
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected a JSON object")
        rows.append(value)
    return rows


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, columns: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _project_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"source image escapes project root: {path}") from exc


def _resolve_image(raw_path: str, repo_root: Path, source_manifest: Path) -> Path:
    if not raw_path:
        raise ValueError(f"missing image path in {source_manifest}")
    if raw_path.startswith("__CTRL__/"):
        path = repo_root / "data/edits/spurious_flip_control" / raw_path.removeprefix(
            "__CTRL__/"
        )
    else:
        candidate = Path(raw_path)
        path = candidate if candidate.is_absolute() else repo_root / candidate
    _project_relative(path, repo_root)
    if not path.is_file():
        raise FileNotFoundError(f"source image does not exist: {path}")
    return path.resolve()


def _opaque_id(seed: int, track_id: str, item_id: str) -> str:
    payload = f"certvic-v11|{seed}|{track_id}|{item_id}".encode()
    suffix = hashlib.sha256(payload).hexdigest()[:16].upper()
    prefix = {
        "intervention91": "I",
        "control94": "C",
        "strict_control30": "S",
        "diagnostic_subset12": "D",
    }.get(track_id, "X")
    return f"CV11-{prefix}-{suffix}"


def _swapped(seed: int, track_id: str, item_id: str) -> bool:
    payload = f"certvic-v11-swap|{seed}|{track_id}|{item_id}".encode()
    return hashlib.sha256(payload).digest()[0] % 2 == 1


def _ordered(rows: list[dict[str, Any]], seed: int, track_id: str, rater: str) -> list[dict[str, Any]]:
    copy = list(rows)
    order_seed = int.from_bytes(
        hashlib.sha256(f"{seed}|{track_id}|{rater}".encode()).digest()[:8], "big"
    )
    random.Random(order_seed).shuffle(copy)
    return copy


def _select_rows(
    repo_root: Path,
    spec: TrackSpec,
) -> tuple[Path, list[dict[str, Any]], list[str]]:
    source_path = repo_root / spec.source_manifest
    if not source_path.is_file():
        raise FileNotFoundError(f"task manifest missing: {source_path}")
    rows = _jsonl(source_path)
    selection_ids: list[str] = []
    if spec.selection_manifest:
        selection_path = repo_root / spec.selection_manifest
        if not selection_path.is_file():
            raise FileNotFoundError(f"selection manifest missing: {selection_path}")
        selection_ids = [str(row["item_id"]) for row in _jsonl(selection_path)]
        if len(selection_ids) != len(set(selection_ids)):
            raise ValueError(f"selection manifest has duplicate item IDs: {selection_path}")
        by_id = {str(row["item_id"]): row for row in rows}
        missing = sorted(set(selection_ids) - set(by_id))
        if missing:
            raise ValueError(f"selection IDs absent from source manifest: {missing}")
        rows = [by_id[item_id] for item_id in selection_ids]
    if len(rows) != spec.expected_count:
        raise ValueError(
            f"{spec.track_id}: expected {spec.expected_count} rows, found {len(rows)}"
        )
    item_ids = [str(row.get("item_id", "")) for row in rows]
    if any(not item_id for item_id in item_ids) or len(item_ids) != len(set(item_ids)):
        raise ValueError(f"{spec.track_id}: missing or duplicate source item IDs")
    return source_path, rows, selection_ids


def _review_row(static: dict[str, str], blind_order: int) -> dict[str, str | int]:
    row: dict[str, str | int] = {column: "" for column in SHEET_COLUMNS}
    row.update(static)
    row["blind_order"] = blind_order
    return row


def _make_track(
    repo_root: Path,
    reviewer_root: Path,
    coordinator_root: Path,
    spec: TrackSpec,
    seed: int,
) -> dict[str, Any]:
    source_path, source_rows, selection_ids = _select_rows(repo_root, spec)
    track_root = reviewer_root / "tracks" / spec.track_id
    image_root = track_root / "images"
    image_root.mkdir(parents=True, exist_ok=True)

    static_rows: list[dict[str, str]] = []
    coordinator_rows: list[dict[str, str]] = []
    image_entries: list[dict[str, str]] = []
    source_hash = _sha256(source_path)

    for source_row in source_rows:
        item_id = str(source_row["item_id"])
        blind_id = _opaque_id(seed, spec.track_id, item_id)
        original = _resolve_image(
            str(source_row.get("original_image_path", "")), repo_root, source_path
        )
        edited = _resolve_image(
            str(source_row.get("edited_image_path", "")), repo_root, source_path
        )
        swap = _swapped(seed, spec.track_id, item_id)
        image_a_source, image_b_source = (edited, original) if swap else (original, edited)
        variant_a, variant_b = ("edited", "original") if swap else ("original", "edited")
        suffix_a = image_a_source.suffix.lower() or ".jpg"
        suffix_b = image_b_source.suffix.lower() or ".jpg"
        image_a_name = f"{blind_id}_A{suffix_a}"
        image_b_name = f"{blind_id}_B{suffix_b}"
        image_a_out = image_root / image_a_name
        image_b_out = image_root / image_b_name
        shutil.copyfile(image_a_source, image_a_out)
        shutil.copyfile(image_b_source, image_b_out)

        static_rows.append(
            {
                "blind_pair_id": blind_id,
                "image_a": f"images/{image_a_name}",
                "image_b": f"images/{image_b_name}",
                "question": str(
                    source_row.get("question_edited")
                    or source_row.get("question_original")
                    or ""
                ),
            }
        )
        coordinator_rows.append(
            {
                "blind_pair_id": blind_id,
                "source_item_id": item_id,
                "source_manifest": spec.source_manifest,
                "source_manifest_sha256": source_hash,
                "source_original_path": _project_relative(original, repo_root),
                "source_edited_path": _project_relative(edited, repo_root),
                "image_a_variant": variant_a,
                "image_b_variant": variant_b,
                "source_original_sha256": _sha256(original),
                "source_edited_sha256": _sha256(edited),
                "question": str(
                    source_row.get("question_edited")
                    or source_row.get("question_original")
                    or ""
                ),
                "required_change": str(source_row.get("required_change", "")),
            }
        )
        image_entries.extend(
            [
                {"path": f"tracks/{spec.track_id}/images/{image_a_name}", "sha256": _sha256(image_a_out)},
                {"path": f"tracks/{spec.track_id}/images/{image_b_name}", "sha256": _sha256(image_b_out)},
            ]
        )

    for rater in ("rater_1", "rater_2"):
        ordered = _ordered(static_rows, seed, spec.track_id, rater)
        _write_csv(
            track_root / f"{rater}.csv",
            SHEET_COLUMNS,
            (_review_row(row, index) for index, row in enumerate(ordered, 1)),
        )

    adjudication_order = _ordered(static_rows, seed, spec.track_id, "adjudication")
    adjudication_rows = []
    for index, static in enumerate(adjudication_order, 1):
        row: dict[str, str | int] = {column: "" for column in ADJUDICATION_COLUMNS}
        row.update({"blind_order": index, "blind_pair_id": static["blind_pair_id"]})
        adjudication_rows.append(row)
    _write_csv(track_root / "adjudication.csv", ADJUDICATION_COLUMNS, adjudication_rows)
    _write_csv(
        coordinator_root / f"{spec.track_id}_key.csv",
        COORDINATOR_COLUMNS,
        sorted(coordinator_rows, key=lambda row: row["blind_pair_id"]),
    )

    if spec.selection_manifest:
        selection_path = repo_root / spec.selection_manifest
        _write_json(
            coordinator_root / f"{spec.track_id}_selection_provenance.json",
            {
                "schema": "certvic.v11.human_review_selection_provenance.v1",
                "paper_evidence": False,
                "track_id": spec.track_id,
                "selection_manifest": spec.selection_manifest,
                "selection_manifest_sha256": _sha256(selection_path),
                "selection_basis": spec.selection_note,
                "selected_source_item_ids": selection_ids,
                "reviewer_bundle_disclosure": "none",
            },
        )

    return {
        "track_id": spec.track_id,
        "n_pairs": len(static_rows),
        "blind_pair_ids": sorted(row["blind_pair_id"] for row in static_rows),
        "images": sorted(image_entries, key=lambda entry: entry["path"]),
        "rater_1_sheet": f"tracks/{spec.track_id}/rater_1.csv",
        "rater_2_sheet": f"tracks/{spec.track_id}/rater_2.csv",
        "adjudication_sheet": f"tracks/{spec.track_id}/adjudication.csv",
    }


def _review_codebook() -> str:
    return """# CertVIC V11 blinded pair-review codebook

## Independence and blinding

- Complete only the sheet assigned to you. Do not inspect another rater's sheet.
- Do not discuss ratings until both signed sheets have been returned to the coordinator.
- Pair IDs and A/B order are randomized. Do not infer which image was changed.
- The packet contains no system outputs or prior ratings. Rate only visible content.
- Never review more than one track containing the same pixels. By default the coordinator
  obtains ratings once on `control94` and derives its subset decisions only after both
  sheets are locked. Direct subset review requires a completely disjoint rater pool.
- Leave no required field blank. Use `uncertain` when the image does not support a firm call.
- Use an assigned non-identifying reviewer code and an ISO-8601 UTC completion time.

## Allowed values

| Field | Allowed values | Meaning |
|---|---|---|
| `prompt_unambiguous` | `yes`, `no`, `uncertain` | The question has one clear visual interpretation. |
| `image_answerable` | `yes`, `no`, `uncertain` | The pair contains enough visible evidence to answer the question. |
| `target_visible_a` | `yes`, `no`, `uncertain` | The questioned target is visibly present in image A. |
| `target_visible_b` | `yes`, `no`, `uncertain` | The questioned target is visibly present in image B. |
| `target_unaffected` | `yes`, `no`, `uncertain`, `not_applicable` | For control tracks, whether the questioned target itself is unaffected. Use `not_applicable` only for the intentional intervention track. |
| `expected_answer_relation_valid` | `yes`, `no`, `uncertain` | Whether the visible pair supports the track's intended changed-or-unchanged answer relation. |
| `expected_answer_unchanged` | `yes`, `no`, `uncertain`, `not_applicable` | For control tracks, whether the expected answer should remain unchanged. Use `not_applicable` only for the intentional intervention track. |
| `perturbation_acceptable` | `yes`, `no`, `uncertain` | The change is localized, plausible, and free of a material scene confound. |
| `artifact_severity` | `none`, `minor`, `major`, `uncertain` | Visible editing or patch artifact severity. |
| `retention_decision` | `retain`, `exclude`, `uncertain` | Explicit visual-quality retain/exclude recommendation. |
| `confidence` | `high`, `medium`, `low` | Confidence in the row-level ratings. |

Free-text notes must not contain names or other personal information. Human review verifies
visual validity; it does not by itself turn a diagnostic cohort into paper evidence.
"""


def _reviewer_readme(track_counts: dict[str, int]) -> str:
    lines = [
        "# CertVIC V11 independent blinded review packet",
        "",
        "This portable packet contains paired images and blank review sheets. It contains no",
        "system outcomes, prior labels, source item IDs, or coordinator mapping keys.",
        "",
        "**PRIVATE REVIEW MATERIAL — DO NOT PUBLISH.** The ADE-derived images have not been",
        "cleared for public redistribution. Portability is for controlled review only.",
        "",
        "Read `REVIEW_CODEBOOK.md` before rating. Each rater receives only their assigned CSV.",
        "Return the signed CSV to the coordinator; do not exchange sheets between raters.",
        "Do not issue this complete staging archive to a rater. Give each rater only their",
        "assigned sheet and corresponding images.",
        "",
        "## Tracks",
        "",
    ]
    for track_id, count in track_counts.items():
        lines.append(f"- `{track_id}`: {count} image pairs")
    lines.extend(
        [
            "",
            "The neutral 12-pair diagnostic subset must be reviewed exactly like every other",
            "track. Its selection rationale is intentionally withheld from reviewers.",
            "The 30- and 12-pair tracks reuse pixels from `control94`. Default operations rate",
            "`control94` once and derive subset judgments only after both sheets are locked.",
            "If direct subset review is necessary, use disjoint rater pools; no reviewer may",
            "see the same pair under two anonymous IDs.",
            "",
        ]
    )
    return "\n".join(lines)


def _zip_reviewer_bundle(reviewer_root: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in reviewer_root.rglob("*") if p.is_file()):
            relative = path.relative_to(reviewer_root).as_posix()
            info = zipfile.ZipInfo(f"reviewer_bundle/{relative}", ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build_packet(
    repo_root: Path = ROOT,
    out_dir: Path = DEFAULT_OUT,
    seed: int = DEFAULT_SEED,
    tracks: tuple[TrackSpec, ...] = DEFAULT_TRACKS,
) -> dict[str, Any]:
    """Build and return the top-level packet manifest."""

    repo_root = repo_root.resolve()
    out_dir = out_dir.resolve()
    if out_dir == repo_root or repo_root not in out_dir.parents:
        raise ValueError("output directory must be a dedicated directory inside the project root")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    reviewer_root = out_dir / "reviewer_bundle"
    coordinator_root = out_dir / "coordinator_only"
    reviewer_root.mkdir(parents=True)
    coordinator_root.mkdir(parents=True)

    track_manifests = [
        _make_track(repo_root, reviewer_root, coordinator_root, spec, seed) for spec in tracks
    ]
    counts = {track["track_id"]: track["n_pairs"] for track in track_manifests}
    (reviewer_root / "README.md").write_text(_reviewer_readme(counts), encoding="utf-8")
    (reviewer_root / "REVIEW_CODEBOOK.md").write_text(_review_codebook(), encoding="utf-8")

    reviewer_manifest = {
        "schema": "certvic.v11.blinded_human_review_reviewer_manifest.v1",
        "evidence_status": "HUMAN_REVIEW_PENDING",
        "paper_evidence": False,
        "blinded": True,
        "human_fields_blank": True,
        "contains_system_outcomes": False,
        "contains_source_item_ids": False,
        "contains_coordinator_keys": False,
        "public_release_allowed": False,
        "distribution_status": "PRIVATE_COORDINATED_REVIEW_ONLY",
        "distribution_reason": "ADE-derived image redistribution has not been cleared",
        "seed": seed,
        "rating_fields": RATING_FIELDS,
        "tracks": track_manifests,
    }
    _write_json(reviewer_root / "reviewer_manifest.json", reviewer_manifest)

    coordinator_manifest = {
        "schema": "certvic.v11.blinded_human_review_coordinator_manifest.v1",
        "evidence_status": "HUMAN_REVIEW_PENDING",
        "paper_evidence": False,
        "public_release_allowed": False,
        "distribution_status": "PRIVATE_COORDINATED_REVIEW_ONLY",
        "seed": seed,
        "reviewer_bundle": "reviewer_bundle",
        "reviewer_zip": "certvic_v11_blinded_reviewer_bundle.zip",
        "tracks": [
            {
                "track_id": track["track_id"],
                "n_pairs": track["n_pairs"],
                "key": f"coordinator_only/{track['track_id']}_key.csv",
            }
            for track in track_manifests
        ],
        "instructions": (
            "Keep this directory private. Issue rater_1.csv and rater_2.csv independently; "
            "do not disclose mapping keys or the diagnostic-subset selection provenance."
        ),
        "overlap_control": {
            "overlap": "strict_control30 and diagnostic_subset12 reuse control94 pixel pairs",
            "preferred_operation": (
                "Review control94 once; after both independent sheets are locked, derive "
                "strict_control30 and diagnostic_subset12 judgments through coordinator keys."
            ),
            "permitted_alternative": (
                "Direct subset review requires disjoint rater pools and no reviewer access "
                "to another track containing the same pixels."
            ),
        },
    }
    _write_json(coordinator_root / "coordinator_manifest.json", coordinator_manifest)

    zip_path = out_dir / "certvic_v11_blinded_reviewer_bundle.zip"
    _zip_reviewer_bundle(reviewer_root, zip_path)
    manifest = {
        "schema": "certvic.v11.blinded_human_review_packet.v1",
        "evidence_status": "HUMAN_REVIEW_PENDING",
        "paper_evidence": False,
        "public_release_allowed": False,
        "distribution_status": "PRIVATE_COORDINATED_REVIEW_ONLY",
        "distribution_reason": "ADE-derived image redistribution has not been cleared",
        "deterministic": True,
        "portable": True,
        "seed": seed,
        "n_tracks": len(track_manifests),
        "n_unique_review_rows": sum(track["n_pairs"] for track in track_manifests),
        "n_copied_images": sum(len(track["images"]) for track in track_manifests),
        "track_counts": counts,
        "reviewer_zip": zip_path.name,
        "reviewer_zip_sha256": _sha256(zip_path),
        "reviewer_zip_bytes": zip_path.stat().st_size,
        "human_fields_blank": True,
        "agreement_computed": False,
        "warning": "No human labels are present. Run validate_v11_human_review.py after two independent reviews.",
    }
    _write_json(out_dir / "packet_manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)
    manifest = build_packet(args.repo_root, args.out_dir, args.seed)
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
