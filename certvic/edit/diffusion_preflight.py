"""Diffusion / Kaggle edit-generation readiness preflight (V2.2).

Companion to ``certvic.eval.vlm_preflight`` (which preflights *inference*). This
module preflights the *edit-generation* stage: it verifies that photorealistic
diffusion-inpainting edits could run on a free Kaggle/Colab GPU before any heavy
work begins. It runs no diffusion, downloads no weights, and makes no claims.

Crucially it enforces the zero-cost / no-download rule: heavy diffusion edits are
only "ready" when the optional deps are importable AND model weights are present
in a *local/cached* directory the user supplies. The preflight never triggers a
download and never enables paid services.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from pathlib import Path

import yaml

from certvic.edit.engines import ALL_ENGINES, HEAVY_ENGINES, SIMPLE_ENGINES
from certvic.io import read_jsonl

# Rough VRAM envelope for SD-style inpainting at modest resolution in fp16/4-bit.
DEFAULT_EXPECTED_VRAM_GB = 6.0
FREE_TIER_VRAM_GB = 16.0
# Conservative per-edit wall-clock seconds on a single free-tier GPU.
DEFAULT_SECONDS_PER_EDIT_GPU = 8.0
DEFAULT_SECONDS_PER_EDIT_CPU = 1.0


def _dep(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def environment_summary(check_gpu: bool = False) -> dict:
    have_torch = _dep("torch")
    summary = {
        "torch_available": have_torch,
        "diffusers_available": _dep("diffusers"),
        "opencv_available": _dep("cv2"),
        "pillow_available": _dep("PIL"),
        "gpu_checked": check_gpu,
        "gpu_available": None,
        "gpu_name": None,
        "gpu_vram_gb": None,
    }
    if check_gpu and have_torch:
        try:
            import torch

            if torch.cuda.is_available():
                summary["gpu_available"] = True
                summary["gpu_name"] = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                summary["gpu_vram_gb"] = round(props.total_memory / (1024 ** 3), 1)
            else:
                summary["gpu_available"] = False
        except Exception:
            summary["gpu_available"] = False
    return summary


def diffusion_preflight(
    edit_plan_path: str,
    engine: str = "diffusers_inpaint_optional",
    config_path: str | None = None,
    weights_dir: str | None = None,
    out_path: str | None = None,
    check_gpu: bool = False,
    max_check_items: int = 25,
    seconds_per_edit: float | None = None,
) -> dict:
    checks: list[dict] = []

    def add(name: str, ok: bool, **detail):
        checks.append({"check": name, "ok": bool(ok), **detail})

    heavy = engine in HEAVY_ENGINES

    plan_exists = Path(edit_plan_path).exists()
    add("edit_plan_exists", plan_exists, path=edit_plan_path)
    rows = read_jsonl(edit_plan_path)[:max_check_items] if plan_exists else []
    add("edit_plan_nonempty", bool(rows), checked=len(rows))

    missing_sources = 0
    missing_masks = 0
    for row in rows:
        src = row.get("image_path") or row.get("original_image_path")
        if src and not str(src).startswith(("http", "planned://", "simulated://")) and not Path(str(src)).exists():
            missing_sources += 1
        mask = (row.get("mask") or {}).get("mask_path") if isinstance(row.get("mask"), dict) else row.get("mask_path")
        if mask and not str(mask).startswith(("http", "planned://", "simulated://")) and not Path(str(mask)).exists():
            missing_masks += 1
    if rows:
        add("source_images_present", missing_sources == 0, missing=missing_sources, checked=len(rows))
        add("masks_present", missing_masks == 0, missing=missing_masks, checked=len(rows))

    add("engine_known", engine in ALL_ENGINES, engine=engine, simple=engine in SIMPLE_ENGINES, heavy=heavy)

    env = environment_summary(check_gpu=check_gpu)
    if heavy:
        deps_ok = env["torch_available"] and env["diffusers_available"]
        add("diffusion_dependencies", deps_ok, **{k: env[k] for k in ("torch_available", "diffusers_available", "opencv_available")})
        weights_ok = bool(weights_dir) and Path(weights_dir).exists() and any(Path(weights_dir).iterdir())
        add(
            "local_weights_present",
            weights_ok,
            weights_dir=weights_dir,
            note="weights must be pre-downloaded to a local/cached dir; preflight never downloads",
        )
    else:
        add("simple_engine_cpu_ready", True, note="simple engines run on CPU with no heavy deps or weights")

    cfg = {}
    if config_path and Path(config_path).exists():
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    add("zero_cost_policy", cfg.get("paid_services_enabled") is not True, paid_services_enabled=cfg.get("paid_services_enabled"))
    if heavy and cfg:
        add(
            "diffusers_explicitly_enabled",
            cfg.get("optional_diffusers_enabled") is True,
            optional_diffusers_enabled=cfg.get("optional_diffusers_enabled"),
            note="heavy diffusion edits require explicit opt-in in the config",
        )

    if check_gpu:
        vram = env.get("gpu_vram_gb")
        add(
            "gpu_available",
            bool(env.get("gpu_available")),
            gpu_name=env.get("gpu_name"),
            gpu_vram_gb=vram,
            fits_expected=(vram is None or vram >= DEFAULT_EXPECTED_VRAM_GB),
        )

    writable = True
    if out_path:
        try:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            writable = shutil.disk_usage(Path(out_path).parent).free > 0
        except Exception:
            writable = False
        add("output_path_writable", writable, path=out_path)

    n_plan = len(read_jsonl(edit_plan_path)) if plan_exists else 0
    spe = seconds_per_edit if seconds_per_edit is not None else (
        DEFAULT_SECONDS_PER_EDIT_GPU if heavy else DEFAULT_SECONDS_PER_EDIT_CPU
    )
    est_seconds = n_plan * spe
    add(
        "runtime_estimate",
        True,
        n_planned_edits=n_plan,
        seconds_per_edit=spe,
        estimated_minutes=round(est_seconds / 60.0, 1),
        estimated_hours=round(est_seconds / 3600.0, 2),
        expected_vram_gb=DEFAULT_EXPECTED_VRAM_GB if heavy else 0.0,
        fits_free_tier=(DEFAULT_EXPECTED_VRAM_GB <= FREE_TIER_VRAM_GB),
    )

    blocking_names = {"edit_plan_exists", "zero_cost_policy"}
    if heavy:
        blocking_names |= {"diffusion_dependencies", "local_weights_present"}
    blocking = [c for c in checks if not c["ok"] and c["check"] in blocking_names]

    result = {
        "preflight": "diffusion_edit_generation",
        "engine": engine,
        "heavy": heavy,
        "edit_plan": edit_plan_path,
        "config": config_path,
        "checks": checks,
        "ready": not blocking,
        "blocking_failures": [c["check"] for c in blocking],
        "environment": env,
        "downloads_attempted": False,
        "diffusion_run": False,
        "paid_services": False,
        "evidence_claims_made": False,
    }
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC diffusion/Kaggle edit-generation preflight (V2.2)")
    parser.add_argument("--edit-plan", required=True)
    parser.add_argument("--engine", default="diffusers_inpaint_optional", choices=sorted(ALL_ENGINES))
    parser.add_argument("--config")
    parser.add_argument("--weights-dir")
    parser.add_argument("--out")
    parser.add_argument("--check-gpu", action="store_true")
    parser.add_argument("--seconds-per-edit", type=float)
    args = parser.parse_args(argv)
    result = diffusion_preflight(
        args.edit_plan,
        engine=args.engine,
        config_path=args.config,
        weights_dir=args.weights_dir,
        out_path=args.out,
        check_gpu=args.check_gpu,
        seconds_per_edit=args.seconds_per_edit,
    )
    print(json.dumps({"engine": args.engine, "ready": result["ready"], "blocking_failures": result["blocking_failures"]}, sort_keys=True))


if __name__ == "__main__":
    main()
