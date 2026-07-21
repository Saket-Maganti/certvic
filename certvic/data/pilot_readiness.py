"""Dry-run pilot readiness reports for user-provided ADE20K roots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.config import load_config
from certvic.data.ade20k_adapter import ADE20KLayoutError, inspect_ade20k_layout
from certvic.data.license_policy import release_mode_for_source
from certvic.io import write_json
from certvic.schema import LicenseCategory, SourceImageRecord


def build_pilot_readiness_report(
    config_path: str,
    ade20k_root: str,
    out_dir: str,
    dry_run: bool = True,
) -> dict:
    if not dry_run:
        raise ADE20KLayoutError("V1.2 pilot readiness supports --dry-run only.")

    config = load_config(config_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    inspection = inspect_ade20k_layout(ade20k_root)
    candidate_summary = _candidate_summary(inspection, config)
    license_summary = _license_summary()

    write_json(out / "dataset_inspection.json", inspection)
    write_json(out / "candidate_summary.json", candidate_summary)
    write_json(out / "license_summary.json", license_summary)
    (out / "readiness_report.md").write_text(
        _readiness_markdown(inspection, candidate_summary, license_summary, config_path),
        encoding="utf-8",
    )

    return {
        "passed": candidate_summary["ready_for_source_manifest"],
        "ready_for_mask_manifest": candidate_summary["ready_for_mask_manifest"],
        "ready_for_pilot_selection": candidate_summary["ready_for_pilot_selection"],
        "out_dir": str(out),
        "blockers": candidate_summary["blockers"],
    }


def _candidate_summary(inspection: dict, config: dict) -> dict:
    target = int(config.get("target_items", 200))
    blockers: list[str] = []
    if inspection["candidate_image_count"] < target:
        blockers.append(
            f"candidate image count {inspection['candidate_image_count']} is below target {target}"
        )
    if inspection["candidate_annotation_count"] == 0:
        blockers.append("no candidate annotation files found")
    if inspection.get("unmatched_image_count", 0):
        blockers.append(f"{inspection['unmatched_image_count']} image files lack matching annotation stems")
    if inspection["layout_status"] != "supported_layout":
        blockers.append(f"layout status is {inspection['layout_status']}")
    if inspection.get("candidate_mask_count", 0) < target:
        blockers.append(
            f"candidate mask count {inspection.get('candidate_mask_count', 0)} is below target {target}"
        )
    return {
        "target_items": target,
        "candidate_image_count": inspection["candidate_image_count"],
        "candidate_annotation_count": inspection["candidate_annotation_count"],
        "train_image_count": inspection["train_image_count"],
        "val_image_count": inspection["val_image_count"],
        "train_annotation_count": inspection["train_annotation_count"],
        "val_annotation_count": inspection["val_annotation_count"],
        "matched_pair_count": inspection.get("matched_pair_count", 0),
        "unmatched_image_count": inspection.get("unmatched_image_count", 0),
        "candidate_mask_count": inspection.get("candidate_mask_count", 0),
        "mask_area_statistics": inspection.get("mask_area_statistics", {}),
        "top_label_ids_by_frequency": inspection.get("top_label_ids_by_frequency", []),
        "layout_status": inspection["layout_status"],
        "ready_for_source_manifest": inspection["candidate_image_count"] > 0,
        "ready_for_mask_manifest": inspection["layout_status"] == "supported_layout"
        and inspection.get("candidate_mask_count", 0) > 0,
        "ready_for_pilot_selection": inspection["layout_status"] == "supported_layout"
        and inspection.get("candidate_mask_count", 0) >= target
        and not inspection.get("unmatched_image_count", 0),
        "blockers": blockers,
        "dry_run_only": True,
    }


def _license_summary() -> dict:
    record = SourceImageRecord(
        source_id="ade20k_policy_template",
        source_name="ADE20K",
        source_url_or_pointer="user-provided-local-root",
        local_path=None,
        sha256=None,
        license_category=LicenseCategory.POINTER_ONLY.value,
        license_text=None,
        redistribution_allowed=False,
        notes="Policy template only; pixels are pointer-only unless redistribution is explicitly verified.",
    )
    return {
        "default_license_category": record.license_category,
        "redistribution_allowed_by_default": record.redistribution_allowed,
        "default_release_mode": release_mode_for_source(record),
        "pixels_rehostable_by_default": False,
        "policy": "recipe_first_pointer_aware",
        "paid_services_used": False,
    }


def _readiness_markdown(
    inspection: dict,
    candidate_summary: dict,
    license_summary: dict,
    config_path: str,
) -> str:
    blockers = candidate_summary["blockers"] or ["None"]
    return "\n".join(
        [
            "# CertVIC ADE20K Pilot Readiness Dry Run",
            "",
            "Status: dry-run only. No edits generated yet. No model inference run yet. No evidence claims.",
            "",
            "Zero paid services were used. The command inspected a local dataset root only and did not download data.",
            "",
            "## Dataset Inspection",
            "",
            f"- root: `{inspection['root']}`",
            f"- layout status: `{inspection['layout_status']}`",
            f"- candidate images: {inspection['candidate_image_count']}",
            f"- candidate annotations: {inspection['candidate_annotation_count']}",
            f"- matched image/annotation pairs: {inspection.get('matched_pair_count', 0)}",
            f"- candidate label masks: {inspection.get('candidate_mask_count', 0)}",
            f"- train images: {inspection['train_image_count']}",
            f"- val images: {inspection['val_image_count']}",
            f"- missing annotation pairs: {inspection.get('missing_annotation_count', 0)}",
            f"- mask area stats: `{inspection.get('mask_area_statistics', {})}`",
            f"- top label IDs: `{inspection.get('top_label_ids_by_frequency', [])}`",
            "",
            "## Candidate Readiness",
            "",
            f"- ready for source manifest: {candidate_summary['ready_for_source_manifest']}",
            f"- ready for mask manifest: {candidate_summary['ready_for_mask_manifest']}",
            f"- ready for pilot selection: {candidate_summary['ready_for_pilot_selection']}",
            "",
            "Blockers:",
            *[f"- {blocker}" for blocker in blockers],
            "",
            "## License Policy",
            "",
            f"- default license category: `{license_summary['default_license_category']}`",
            f"- default release mode: `{license_summary['default_release_mode']}`",
            "- pixels are not rehostable by default",
            "",
            "## Next Commands Once Root Is Confirmed",
            "",
            "```bash",
            f"python3 -m certvic.data.pilot_readiness --config {config_path} --ade20k-root /path/to/ADE20K --out-dir data/results/pilot_readiness_ade20k --dry-run",
            "python3 -m certvic.data.ade20k_adapter --ade20k-root /path/to/ADE20K --out-sources data/manifests/ade20k_sources.jsonl --out-masks data/manifests/ade20k_masks.jsonl --inspection-out data/results/pilot_readiness_ade20k/dataset_inspection.json --max-items 500",
            "python3 -m certvic.data.select_pilot_items --sources data/manifests/ade20k_sources.jsonl --masks data/manifests/ade20k_masks.jsonl --out data/manifests/pilot_selection.jsonl --target 200 --seed 0 --min-mask-area-fraction 0.01 --max-mask-area-fraction 0.40",
            "```",
            "",
            "Binary mask PNG export is disabled by default; use --export-binary-masks only when a local inspection artifact is explicitly needed.",
        ]
    ) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--ade20k-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build_pilot_readiness_report(
            args.config,
            args.ade20k_root,
            args.out_dir,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, sort_keys=True))
    except ADE20KLayoutError as exc:
        raise SystemExit(f"Pilot readiness failed: {exc}") from None


if __name__ == "__main__":
    main()
