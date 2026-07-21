"""Outcome-blind CPU candidate census and mining for the confirmatory set."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from certvic.cvpr.contracts import load_yaml, sha256_bytes, validate_study_config
from certvic.cvpr.task_schema import convert_legacy_task, require_task


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}: line {index} is not an object")
        rows.append(value)
    return rows


def mine_candidates(
    source_manifest: str | Path,
    config_path: str | Path,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    config = load_yaml(config_path)
    freeze = validate_study_config(config, require_frozen=not dry_run)
    rows = _read_jsonl(Path(source_manifest))
    exclusion_path = Path(str(config.get("exclusions", {}).get("frozen_inventory", "")))
    if not exclusion_path.is_file():
        candidate = Path(config_path).parent / exclusion_path.name
        exclusion_path = candidate if candidate.is_file() else exclusion_path
    inventory = json.loads(exclusion_path.read_text(encoding="utf-8")) if exclusion_path.is_file() else {}
    prior_ids = set(inventory.get("item_ids", [])) | set(inventory.get("source_ids", []))
    prior_image_ids = set(inventory.get("source_image_ids", []))
    prior_hashes = set(inventory.get("original_image_sha256", []))
    seen_sources: set[str] = set()
    seen_hashes: set[str] = set()
    eligible: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda value: str(value.get("source_id", ""))):
        reasons: list[str] = []
        source_id = str(row.get("source_id", ""))
        image_path = Path(str(row.get("image_path", "")))
        if not source_id:
            reasons.append("missing_source_id")
        source_image_id = str(row.get("source_image_id", source_id))
        if source_id in prior_ids or source_image_id in prior_image_ids:
            reasons.append("prior_control_overlap")
        if source_id in seen_sources:
            reasons.append("duplicate_source_id")
        seen_sources.add(source_id)
        if not image_path.is_file():
            reasons.append("missing_image")
            image_sha = None
        else:
            image_sha = sha256_bytes(image_path.read_bytes())
            if image_sha in prior_hashes:
                reasons.append("prior_control_pixel_overlap")
            if image_sha in seen_hashes:
                reasons.append("duplicate_image_sha256")
            seen_hashes.add(image_sha)
        if not row.get("category"):
            reasons.append("missing_category")
        if config.get("source_rules", {}).get("license_eligible_required", True) and row.get(
            "license_eligible"
        ) is not True:
            reasons.append("license_not_verified_eligible")
        if not row.get("target_bbox") and not row.get("target_mask_path"):
            reasons.append("missing_target_geometry")
        enriched: dict[str, Any] = {
            **row,
            "item_id": row.get("item_id", f"confirmatory-{source_id}"),
            "source_image_path": str(image_path),
            "source_image_hash": image_sha,
            "source_dataset": row.get("source_dataset", row.get("dataset", "ADE20K")),
            "source_split": row.get("source_split", row.get("split", "validation")),
            "question": row.get("question", f"Is there a {row.get('category')} in the image?"),
            "original_expected_answer": row.get("expected_answer", "yes"),
            "edited_expected_answer": row.get("expected_answer", "yes"),
            "required_change": False, "semantic_edit_family": None,
            "control_edit_family": row.get("control_edit_family", "structured_texture_patch"),
            "selected_engine": row.get("selected_engine", "structured_texture_patch"),
            "license_status": row.get("license_status", "VERIFIED_ELIGIBLE"),
            "image_sha256": image_sha,
            "outcome_blind": True,
            "model_outputs_used": False,
            "rejection_reasons": reasons,
        }
        mask_path = Path(str(row.get("target_mask_path", "")))
        if mask_path.is_file():
            enriched["target_mask_hash"] = sha256_bytes(mask_path.read_bytes())
        if not reasons:
            enriched = require_task(convert_legacy_task(
                enriched, study="specificity_confirmatory_cvpr"
            ), verify_files=True)
        (rejected if reasons else eligible).append(enriched)
    status = "DRY_RUN_CENSUS_ONLY" if dry_run else "READY_FOR_BALANCED_SELECTION"
    if not freeze["passed"]:
        status = "BLOCKED_CONFIG_NOT_FROZEN"
    return {
        "schema": "certvic.cvpr.candidate_mining.v1",
        "status": status,
        "dry_run": dry_run,
        "config_validation": freeze,
        "source_count": len(rows),
        "eligible_count": len(eligible),
        "rejected_count": len(rejected),
        "rejection_counts": dict(Counter(r for row in rejected for r in row["rejection_reasons"])),
        "eligible": eligible,
        "rejected": rejected,
        "paper_evidence": False,
        "provider_outputs_used": False,
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Outcome-blind confirmatory candidate mining")
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--config", default="configs/studies/specificity_confirmatory_cvpr.yaml")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--seed", type=int, default=12013)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--status-out")
    args = parser.parse_args(argv)
    result = mine_candidates(args.source_manifest, args.config, dry_run=args.dry_run)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    status_path = Path(args.status_out) if args.status_out else out / "status.json"
    status_path.write_text(
        json.dumps({key: value for key, value in result.items() if key not in {"eligible", "rejected"}},
                   indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if result["status"] != "BLOCKED_CONFIG_NOT_FROZEN" and not args.dry_run:
        _write_jsonl(out / "eligible_candidates.jsonl", result["eligible"])
        _write_jsonl(out / "rejected_candidates.jsonl", result["rejected"])
    print(json.dumps({"status": result["status"], "status_out": str(status_path)}, sort_keys=True))
    return 0 if result["status"] != "BLOCKED_CONFIG_NOT_FROZEN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
