"""Storage planner for CertVIC studies (V3 prompt 02).

Estimates disk usage for masks, edits, rejected edits, review galleries,
predictions, reports, release artifacts, and weight caches at a target scale,
then warns about free-tier limits and path-policy problems. Estimates are
deliberately conservative (realistic, not optimistic). No real dataset scanning
unless a root is explicitly supplied; no downloads, no paid services.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from certvic.io import ensure_parent
from certvic.storage.path_policy import audit_paths, collect_output_paths

GB = 1024 ** 3
MB = 1024 ** 2

# Conservative per-item byte estimates (photorealistic edits dominate).
DEFAULT_BYTES = {
    "source_pointer_record": 1_500,      # pointer-only metadata row
    "mask_png": 30_000,                  # exported binary mask (if enabled)
    "edited_image": 350_000,             # one photorealistic diffusion edit
    "review_gallery_item": 60_000,       # side-by-side thumbnail
    "prediction_record": 2_500,          # one JSONL prediction row
    "report_fixed": 1 * MB,              # fixed report/figure overhead
    "release_record": 1_500,             # recipe-first manifest row (no pixels)
}

# Free-tier working-disk envelopes (approximate, conservative).
KAGGLE_WORKING_GB = 20.0
COLAB_DISK_GB = 70.0

# A typical diffusion-inpaint weight cache the user pre-downloads (not counted in
# the working total; reported separately as a one-time cache requirement).
DEFAULT_WEIGHTS_CACHE_GB = 6.0

DEFAULTS = {
    "overgeneration_factor": 2.5,  # candidates generated per kept item
    "num_models": 3,               # open VLMs evaluated
    "variants_per_item": 2,        # original + edited
    "ablation_multiplier": 1.0,    # prompt/caption/etc. ablation variants
    "export_binary_masks": False,  # config may flip this on
    "keep_rejected_pixels": True,  # rejected edits kept on disk during the run
}


def _from_config(config: dict | None) -> dict:
    cfg = dict(DEFAULTS)
    if not config:
        return cfg
    if "export_binary_masks" in config:
        cfg["export_binary_masks"] = bool(config["export_binary_masks"])
    teg = config.get("tiny_edit_generation") or {}
    if "overgeneration_factor" in teg:
        cfg["overgeneration_factor"] = float(teg["overgeneration_factor"])
    return cfg


def estimate_storage(
    scale: int,
    *,
    config: dict | None = None,
    bytes_per: dict | None = None,
    weights_cache_gb: float = DEFAULT_WEIGHTS_CACHE_GB,
) -> dict:
    params = _from_config(config)
    b = {**DEFAULT_BYTES, **(bytes_per or {})}
    n = int(scale)
    over = params["overgeneration_factor"]
    candidates = int(round(n * over))
    rejected = max(candidates - n, 0)

    categories: dict[str, int] = {}
    categories["sources"] = n * b["source_pointer_record"]
    categories["masks"] = (n * b["mask_png"]) if params["export_binary_masks"] else 0
    categories["kept_edits"] = n * b["edited_image"]
    categories["rejected_edits"] = (rejected * b["edited_image"]) if params["keep_rejected_pixels"] else 0
    categories["review_gallery"] = n * b["review_gallery_item"]
    categories["predictions"] = int(
        n * params["num_models"] * params["variants_per_item"] * params["ablation_multiplier"] * b["prediction_record"]
    )
    categories["reports"] = b["report_fixed"]
    categories["release_artifact"] = n * b["release_record"]

    working_bytes = sum(categories.values())
    working_gb = working_bytes / GB

    warnings: list[str] = []
    if working_gb > KAGGLE_WORKING_GB:
        warnings.append(
            f"working set ~{working_gb:.1f} GB exceeds Kaggle /kaggle/working (~{KAGGLE_WORKING_GB:.0f} GB); "
            "shard the study and offload finished shards"
        )
    if params["keep_rejected_pixels"] and categories["rejected_edits"] > categories["kept_edits"]:
        warnings.append(
            "rejected-edit pixels exceed kept-edit pixels; record hashes then delete rejected pixels to reclaim disk"
        )
    if weights_cache_gb >= KAGGLE_WORKING_GB:
        warnings.append(
            f"weights cache (~{weights_cache_gb:.1f} GB) is large; load from a Kaggle input dataset, not /kaggle/working"
        )

    return {
        "plan": "certvic_storage_plan",
        "scale": n,
        "overgeneration_factor": over,
        "candidates_generated": candidates,
        "rejected_edits": rejected,
        "num_models": params["num_models"],
        "category_bytes": categories,
        "category_gb": {k: round(v / GB, 4) for k, v in categories.items()},
        "working_bytes": working_bytes,
        "working_gb": round(working_gb, 3),
        "weights_cache_gb": weights_cache_gb,
        "fits_kaggle_working": working_gb <= KAGGLE_WORKING_GB,
        "fits_colab_disk": working_gb <= COLAB_DISK_GB,
        "warnings": warnings,
        "evidence_claims_made": False,
        "downloads_attempted": False,
        "paid_services": False,
    }


def plan_storage(config_path: str | None, scale: int, *, weights_cache_gb: float = DEFAULT_WEIGHTS_CACHE_GB) -> dict:
    config = {}
    if config_path and Path(config_path).exists():
        config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    estimate = estimate_storage(scale, config=config, weights_cache_gb=weights_cache_gb)
    path_audit = audit_paths(collect_output_paths(config), expect_kaggle_safe=True) if config else audit_paths([])
    estimate["config"] = config_path
    estimate["path_audit"] = path_audit
    estimate["path_policy_ok"] = path_audit["ok"]
    return estimate


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC storage planner")
    parser.add_argument("--config")
    parser.add_argument("--scale", type=int, required=True)
    parser.add_argument("--weights-cache-gb", type=float, default=DEFAULT_WEIGHTS_CACHE_GB)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    plan = plan_storage(args.config, args.scale, weights_cache_gb=args.weights_cache_gb)
    ensure_parent(args.out)
    Path(args.out).write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "scale": plan["scale"],
        "working_gb": plan["working_gb"],
        "fits_kaggle_working": plan["fits_kaggle_working"],
        "n_warnings": len(plan["warnings"]),
        "path_policy_ok": plan["path_policy_ok"],
        "out": args.out,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
