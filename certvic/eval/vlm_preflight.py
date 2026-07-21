"""Open-local VLM preflight checks (no inference, no downloads).

Verifies a reviewed-task run can proceed on free compute before any model is
loaded: manifest exists, images exist, provider is importable, optional deps,
optional GPU, memory estimate, output path writable, zero-cost policy.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from pathlib import Path

import yaml

from certvic.io import read_jsonl
from certvic.providers.registry import is_evidence_eligible_provider, provider_metadata


def environment_summary(check_gpu: bool = False) -> dict:
    have_torch = importlib.util.find_spec("torch") is not None
    have_transformers = importlib.util.find_spec("transformers") is not None
    gpu_available = None
    gpu_name = None
    if check_gpu and have_torch:
        try:
            import torch

            gpu_available = bool(torch.cuda.is_available())
            gpu_name = torch.cuda.get_device_name(0) if gpu_available else None
        except Exception:
            gpu_available = False
    return {
        "torch_available": have_torch,
        "transformers_available": have_transformers,
        "gpu_checked": check_gpu,
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
    }


def vlm_preflight(provider: str, config_path: str | None, tasks_path: str, out_path: str | None = None, check_gpu: bool = False, max_check_images: int = 25) -> dict:
    checks: list[dict] = []

    def add(name: str, ok: bool, **detail):
        checks.append({"check": name, "ok": bool(ok), **detail})

    tasks_exist = Path(tasks_path).exists()
    add("task_manifest_exists", tasks_exist, path=tasks_path)
    images_ok = True
    missing_images = 0
    if tasks_exist:
        rows = read_jsonl(tasks_path)[:max_check_images]
        for row in rows:
            for key in ("original_image_path", "edited_image_path"):
                p = row.get(key)
                if p and not str(p).startswith(("http://", "https://", "planned://")) and not Path(str(p)).exists():
                    images_ok = False
                    missing_images += 1
        add("images_exist", images_ok, checked=len(rows), missing=missing_images)

    meta = provider_metadata(provider)
    add("provider_known", meta.get("provider_type") is not None, metadata=meta)
    add("provider_evidence_eligible", is_evidence_eligible_provider(provider), note="mock/baseline providers cannot produce evidence")

    cfg = {}
    if config_path and Path(config_path).exists():
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    add("zero_cost_policy", cfg.get("paid_services_enabled") is not True, paid_services_enabled=cfg.get("paid_services_enabled"))

    env = environment_summary(check_gpu=check_gpu)
    add("optional_dependencies", env["torch_available"] and env["transformers_available"], **env)
    if check_gpu:
        add("gpu_available", bool(env.get("gpu_available")), gpu_name=env.get("gpu_name"))

    writable = True
    if out_path:
        try:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            writable = shutil.disk_usage(Path(out_path).parent).free > 0
        except Exception:
            writable = False
        add("output_path_writable", writable, path=out_path)

    # Memory estimate vs a typical free GPU (e.g. 16 GB).
    est = meta.get("expected_gpu_memory_gb", 0)
    add("memory_estimate", True, expected_gpu_memory_gb=est, fits_16gb=est <= 16, supports_4bit=meta.get("supports_4bit"))

    blocking = [c for c in checks if not c["ok"] and c["check"] in {"task_manifest_exists", "zero_cost_policy"}]
    result = {
        "provider": provider,
        "config": config_path,
        "tasks": tasks_path,
        "checks": checks,
        "ready": not blocking,
        "blocking_failures": [c["check"] for c in blocking],
        "provider_metadata": meta,
        "environment": env,
        "downloads_attempted": False,
        "inference_run": False,
        "paid_services": False,
    }
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Open-local VLM preflight (no inference)")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--config")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--out")
    parser.add_argument("--check-gpu", action="store_true")
    args = parser.parse_args(argv)
    result = vlm_preflight(args.provider, args.config, args.tasks, out_path=args.out, check_gpu=args.check_gpu)
    print(json.dumps({"provider": args.provider, "ready": result["ready"], "blocking_failures": result["blocking_failures"]}, sort_keys=True))


if __name__ == "__main__":
    main()
