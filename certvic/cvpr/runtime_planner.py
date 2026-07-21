"""Conservative pre-smoke planning and non-evidence smoke recalibration."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import median
from typing import Any

from certvic.cvpr.ceiling_common import atomic_json


PROVIDER_ESTIMATES: dict[str, dict[str, float]] = {
    "qwen2_5_vl_7b": {"seconds_per_image": 14.0, "vram_gb": 13.5, "batch_size": 1.0},
    "internvl_8b": {"seconds_per_image": 22.0, "vram_gb": 14.5, "batch_size": 1.0},
    "llava_onevision_7b": {"seconds_per_image": 16.0, "vram_gb": 13.8, "batch_size": 1.0},
}


def _calibration(manifests: list[str | Path], provider: str) -> tuple[float | None, list[str]]:
    samples: list[float] = []
    rejected: list[str] = []
    for path in manifests:
        source = Path(path)
        value = json.loads(source.read_text(encoding="utf-8"))
        if value.get("paper_evidence") is not False or value.get("runtime_class") not in {
            "REAL_MODEL_SMOKE", "SYNTHETIC_TEST", "NON_EVIDENCE_RUNTIME_CALIBRATION"
        }:
            rejected.append(str(source))
            continue
        if value.get("provider") != provider:
            continue
        seconds = value.get("elapsed_seconds")
        images = value.get("images_processed")
        if isinstance(seconds, (int, float)) and isinstance(images, int) and images > 0:
            samples.append(float(seconds) / images)
    return (median(samples) if samples else None), rejected


def plan_runtime(
    *,
    provider: str,
    items: int,
    variants: int = 2,
    runtime_manifests: list[str | Path] | None = None,
    kaggle_session_hours: float = 9.0,
) -> dict[str, Any]:
    if provider not in PROVIDER_ESTIMATES or items <= 0 or variants <= 0:
        raise ValueError("provider must be known and items/variants must be positive")
    baseline = PROVIDER_ESTIMATES[provider]
    calibrated, rejected = _calibration(runtime_manifests or [], provider)
    seconds_per_image = calibrated or baseline["seconds_per_image"]
    images = items * variants
    compute_seconds = seconds_per_image * images
    overhead_seconds = 600 + compute_seconds * 0.20
    duration_hours = (compute_seconds + overhead_seconds) / 3600
    zip_mb = max(2.0, images * 0.006 + 1.0)
    disk_gb = 35.0 + zip_mb / 1024 * 3
    review_hours = items * 2 * 1.25 / 60 + items * 0.10 / 60
    warnings: list[str] = []
    if duration_hours > kaggle_session_hours * 0.80:
        warnings.append("KAGGLE_SESSION_CHECKPOINT_RISK")
    if baseline["vram_gb"] > 14.0:
        warnings.append("T4_VRAM_MARGIN_LOW_USE_BATCH_ONE_AND_OOM_HALVING")
    if disk_gb > 60:
        warnings.append("KAGGLE_STORAGE_MARGIN_LOW")
    if rejected:
        warnings.append("UNSAFE_CALIBRATION_MANIFESTS_REJECTED")
    return {
        "schema": "certvic.cvpr.runtime_plan.v1",
        "provider": provider,
        "items": items,
        "variants": variants,
        "images": images,
        "estimate_status": "RECALIBRATED_FROM_NON_EVIDENCE_SMOKE" if calibrated else "PRE_SMOKE_ESTIMATE",
        "seconds_per_image": seconds_per_image,
        "vram_gb": baseline["vram_gb"],
        "batch_size": int(baseline["batch_size"]),
        "notebook_duration_hours": round(duration_hours, 3),
        "gpu_hours": round(compute_seconds / 3600, 3),
        "expected_zip_mb": round(zip_mb, 2),
        "required_disk_gb": math.ceil(disk_gb),
        "review_hours_two_raters_plus_adjudication": round(review_hours, 2),
        "rejected_calibration_manifests": rejected,
        "warnings": warnings,
        "checkpoint_every_items": max(5, min(50, int(1200 / seconds_per_image))),
        "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Estimate a CertVIC Kaggle/review run")
    parser.add_argument("--provider", required=True, choices=sorted(PROVIDER_ESTIMATES))
    parser.add_argument("--items", type=int, required=True)
    parser.add_argument("--variants", type=int, default=2)
    parser.add_argument("--runtime-manifest", action="append", default=[])
    parser.add_argument("--kaggle-session-hours", type=float, default=9.0)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    result = plan_runtime(
        provider=args.provider,
        items=args.items,
        variants=args.variants,
        runtime_manifests=args.runtime_manifest,
        kaggle_session_hours=args.kaggle_session_hours,
    )
    if args.out:
        atomic_json(args.out, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
