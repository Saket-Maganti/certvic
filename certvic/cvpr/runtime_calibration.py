"""Consume real smoke manifests to calibrate runtime and peak-VRAM estimates."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


ALLOWED_REAL_CLASSES = {"NON_EVIDENCE_REAL_MODEL_SMOKE", "SCIENTIFIC_EXECUTION"}


def calibrate(manifests: list[dict[str, Any]], planned_items: list[int]) -> dict[str, Any]:
    samples: list[float] = []
    peak_vram: list[float] = []
    providers: set[str] = set()
    for manifest in manifests:
        if manifest.get("runtime_class") not in ALLOWED_REAL_CLASSES:
            raise ValueError("calibration refuses mock or unlabeled runtime manifests")
        if manifest.get("observed") is not True:
            raise ValueError("calibration requires observed=true")
        items = int(manifest.get("items", 0))
        seconds = float(manifest.get("duration_seconds", 0))
        vram = float(manifest.get("peak_vram_gib", 0))
        if items <= 0 or seconds <= 0 or vram <= 0:
            raise ValueError("calibration manifest has invalid item/time/VRAM measurements")
        samples.append(seconds / items)
        peak_vram.append(vram)
        providers.add(str(manifest.get("provider", "")))
    median = statistics.median(samples)
    return {
        "schema": "certvic.cvpr.runtime_calibration.v1",
        "status": "CALIBRATED_FROM_REAL_SMOKE",
        "providers": sorted(providers), "samples": len(samples),
        "median_seconds_per_item_variant": median,
        "maximum_observed_peak_vram_gib": max(peak_vram),
        "estimates": [{"items": count, "estimated_seconds": 2 * count * median}
                      for count in planned_items],
        "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calibrate CVPR runtime estimates from real smoke")
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument("--planned-items", type=int, action="append", default=[240, 500, 60])
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = calibrate([json.loads(Path(path).read_text()) for path in args.manifest],
                       args.planned_items)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

