"""Modular, replayable edit engine registry.

Engines turn a planned edit + source image + mask into an edited image plus
deterministic replay metadata. Simple engines run locally (CPU, no downloads).
Heavy engines (diffusers) import lazily and require explicit local/cached
weights; nothing here downloads weights or uses paid services.

This module never runs VLM inference and never makes evidence claims. Generated
rows remain GENERATED_EDIT_ONLY until quality + human review pass.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from certvic.edit.generate_edits import (
    EditGenerationError,
    _load_mask_for_plan,
    _simple_control,
    _simple_displace,
    _simple_occlude,
    _simple_remove,
    _validate_plan_for_generation,
)
from certvic.edit.quality_gates import DEFAULT_QUALITY_CONFIG, evaluate_edit_quality
from certvic.hashing import sha256_bytes, sha256_file, stable_json_dumps
from certvic.io import read_jsonl, write_json, write_jsonl
from certvic.schema import EditType

ENGINE_VERSION = "certvic.edit.engines.v2"

# Engines that run locally with no heavy dependencies.
SIMPLE_ENGINES = {
    "simple_fill",
    "simple_occlude",
    "simple_displace",
    "simple_control",
    "composite_occluder",
    "no_op_debug",
}
HEAVY_ENGINES = {"diffusers_inpaint_optional"}
ALL_ENGINES = SIMPLE_ENGINES | HEAVY_ENGINES

# Maps an edit type to its default simple engine.
EDIT_TYPE_DEFAULT_ENGINE = {
    EditType.REMOVE.value: "simple_fill",
    EditType.OCCLUDE.value: "simple_occlude",
    EditType.DISPLACE.value: "simple_displace",
    EditType.CONTROL_IRRELEVANT.value: "simple_control",
}


def available_engines() -> list[str]:
    return sorted(ALL_ENGINES)


def default_engine_for_edit_type(edit_type: str) -> str:
    return EDIT_TYPE_DEFAULT_ENGINE.get(edit_type, "simple_fill")


def _composite_occluder(image: Image.Image, mask: np.ndarray, plan: dict, rng: random.Random, seed: int):
    """A less-degenerate occluder: a tiled noisy patch over the bbox rather than a flat fill."""
    arr = np.asarray(image).copy()
    bbox = plan.get("bbox") or (plan.get("planned_params") or {}).get("bbox")
    if not bbox:
        ys, xs = np.where(mask)
        if len(xs) == 0:
            raise EditGenerationError("composite_occluder needs a bbox or non-empty mask")
        bbox = [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]
    x1, y1, x2, y2 = [int(v) for v in bbox]
    h, w = max(1, y2 - y1), max(1, x2 - x1)
    base = np.array([90, 90, 95], dtype=int)
    noise = np.asarray(
        [[[rng.randrange(-20, 20) for _ in range(3)] for _ in range(w)] for _ in range(h)], dtype=int
    )
    patch = np.clip(base + noise, 0, 255).astype("uint8")
    arr[y1:y2, x1:x2] = patch
    return Image.fromarray(arr), {
        "operation": "composite_noisy_occluder",
        "occluder_bbox": [x1, y1, x2, y2],
        "seed": seed,
    }


def _diffusers_inpaint(image, mask, plan, rng, seed):
    raise EditGenerationError(
        "diffusers_inpaint_optional requires optional local/cached diffusion weights and a GPU. "
        "It is disabled by default and never downloads weights; use a simple engine for tests/CPU."
    )


def run_engine(engine: str, image: Image.Image, mask: np.ndarray, plan: dict, seed: int, index: int = 0):
    """Dispatch to an engine, returning (edited_image, actual_params)."""
    edit_id = str(plan.get("edit_id", index))
    rng = random.Random(f"{seed}|{index}|{edit_id}|{engine}")
    if engine == "no_op_debug":
        return image.copy(), {"operation": "no_op_debug", "seed": seed}
    if engine == "simple_fill":
        return _simple_remove(image, mask, plan, seed)
    if engine == "simple_occlude":
        return _simple_occlude(image, mask, plan, rng, seed)
    if engine == "simple_displace":
        return _simple_displace(image, mask, plan, seed)
    if engine == "simple_control":
        return _simple_control(image, mask, plan, seed)
    if engine == "composite_occluder":
        return _composite_occluder(image, mask, plan, rng, seed)
    if engine == "diffusers_inpaint_optional":
        return _diffusers_inpaint(image, mask, plan, rng, seed)
    raise EditGenerationError(f"unknown engine: {engine}")


def build_replay_metadata(plan: dict, engine: str, actual_params: dict, mask_source_info: dict, seed: int) -> dict:
    image_path = str(plan.get("image_path") or plan.get("original_image_path") or "")
    source_sha = sha256_file(image_path) if image_path and Path(image_path).exists() else None
    return {
        "engine": engine,
        "engine_version": ENGINE_VERSION,
        "seed": seed,
        "source_image_sha256": source_sha,
        "mask_spec_hash": sha256_bytes(stable_json_dumps(mask_source_info).encode("utf-8")),
        "edit_plan_hash": sha256_bytes(stable_json_dumps(_canonical_plan(plan)).encode("utf-8")),
        "generation_config_hash": sha256_bytes(
            stable_json_dumps({"engine": engine, "engine_version": ENGINE_VERSION, "seed": seed}).encode("utf-8")
        ),
        "actual_params": actual_params,
    }


def _canonical_plan(plan: dict) -> dict:
    keys = ["edit_id", "source_id", "mask_id", "label_id", "edit_type", "required_change", "task_family", "domain", "bbox", "planned_params"]
    return {key: plan.get(key) for key in keys}


def generate_with_engine(plan: dict, out_dir: Path, seed: int, index: int, quality_config: dict, engine: str | None = None, overwrite: bool = False) -> dict:
    _validate_plan_for_generation(plan)
    image_path = Path(str(plan.get("image_path") or plan.get("original_image_path")))
    if not image_path.exists():
        raise EditGenerationError(f"original image path does not exist: {image_path}")
    edit_type = str(plan.get("edit_type"))
    chosen = engine or default_engine_for_edit_type(edit_type)
    if chosen not in ALL_ENGINES:
        raise EditGenerationError(f"unknown engine: {chosen}")
    image = Image.open(image_path).convert("RGB")
    mask, mask_source_info = _load_mask_for_plan(plan, image.size)
    edit_id = str(plan["edit_id"])
    out_path = out_dir / f"{edit_id}.png"
    if out_path.exists() and not overwrite:
        raise EditGenerationError(f"refusing to overwrite existing edit (use overwrite): {out_path}")

    edited, actual_params = run_engine(chosen, image, mask, plan, seed=seed, index=index)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    edited.save(out_path)
    edited_sha256 = sha256_file(out_path)
    quality = evaluate_edit_quality(
        str(image_path),
        str(out_path),
        mask,
        edit_type=edit_type,
        planned_params=plan.get("planned_params") or {},
        actual_params=actual_params,
        config=quality_config,
    )
    replay = build_replay_metadata(plan, chosen, actual_params, mask_source_info, seed)
    return {
        "edit_id": edit_id,
        "source_id": plan.get("source_id"),
        "mask_id": plan.get("mask_id"),
        "label_id": plan.get("label_id"),
        "task_family": plan.get("task_family"),
        "domain": plan.get("domain"),
        "split": plan.get("split", "pilot"),
        "edit_type": edit_type,
        "required_change": plan.get("required_change"),
        "original_image_path": str(image_path),
        "edited_image_path": str(out_path),
        "mask_source_info": mask_source_info,
        "engine": chosen,
        "replay_metadata": replay,
        "planned_params": plan.get("planned_params") or {},
        "actual_params": actual_params,
        "generation_status": "generated",
        "evidence_status": "GENERATED_EDIT_ONLY",
        "generator_mode": chosen,
        "seed": seed,
        "edited_sha256": edited_sha256,
        "quality_gate_status": quality["quality_gate_status"],
        "quality": quality,
        "rejection_reason": None,
        "zero_cost": chosen in SIMPLE_ENGINES,
        "vlm_inference_run": False,
        "paper_evidence": False,
    }


def batch_generate(
    edit_plan_path: str,
    out_dir: str,
    out_manifest: str,
    rejected_out: str,
    summary_out: str,
    engine: str | None = None,
    max_items: int | None = None,
    allow_full_run: bool = False,
    seed: int = 0,
    resume: bool = False,
    fail_fast: bool = False,
    overwrite: bool = False,
    quality_config: dict | None = None,
) -> dict:
    """Batch edit generation with resume, no-overwrite, and duplicate detection."""
    if max_items is None and not allow_full_run:
        raise EditGenerationError("max_items is required unless --allow-full-run is set")
    plans = read_jsonl(edit_plan_path)
    if max_items is not None:
        plans = plans[:max_items]
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cfg = {**DEFAULT_QUALITY_CONFIG, **(quality_config or {})}

    existing: list[dict] = []
    done_ids: set[str] = set()
    if resume and Path(out_manifest).exists():
        existing = read_jsonl(out_manifest)
        done_ids = {str(row.get("edit_id")) for row in existing}
    existing_rejected: list[dict] = []
    if resume and Path(rejected_out).exists():
        existing_rejected = read_jsonl(rejected_out)

    generated: list[dict] = list(existing)
    rejected: list[dict] = list(existing_rejected)
    seen_sha: dict[str, str] = {row.get("edited_sha256"): str(row.get("edit_id")) for row in existing if row.get("edited_sha256")}
    duplicate_count = 0

    for index, plan in enumerate(plans):
        edit_id = str(plan.get("edit_id", index))
        if edit_id in done_ids:
            continue
        try:
            record = generate_with_engine(plan, output_dir, seed=seed, index=index, quality_config=cfg, engine=engine, overwrite=overwrite)
            sha = record.get("edited_sha256")
            if sha and sha in seen_sha:
                duplicate_count += 1
                record.setdefault("quality", {}).setdefault("warnings", []).append(
                    f"duplicate_edited_image: identical to {seen_sha[sha]}"
                )
                record["duplicate_of"] = seen_sha[sha]
            elif sha:
                seen_sha[sha] = edit_id
            generated.append(record)
            done_ids.add(edit_id)
        except Exception as exc:
            rejected.append({"edit_id": edit_id, "source_id": plan.get("source_id"), "rejection_reason": str(exc), "engine": engine, "evidence_status": "GENERATED_EDIT_ONLY"})
            if fail_fast:
                break

    write_jsonl(out_manifest, generated)
    write_jsonl(rejected_out, rejected)
    summary = {
        "edit_plan_path": edit_plan_path,
        "out_dir": out_dir,
        "engine": engine or "per_edit_type_default",
        "engine_version": ENGINE_VERSION,
        "seed": seed,
        "max_items": max_items,
        "allow_full_run": allow_full_run,
        "resume": resume,
        "input_plans": len(plans),
        "generated": len(generated),
        "rejected": len(rejected),
        "duplicates_detected": duplicate_count,
        "quality_passed": sum(1 for row in generated if row.get("quality_gate_status") == "pass"),
        "quality_failed": sum(1 for row in generated if row.get("quality_gate_status") != "pass"),
        "by_engine": dict(sorted(Counter(row.get("engine", "unknown") for row in generated).items())),
        "by_edit_type": dict(sorted(Counter(row.get("edit_type", "unknown") for row in generated).items())),
        "evidence_status": "GENERATED_EDIT_ONLY",
        "zero_cost": True,
        "vlm_inference_run": False,
        "paper_evidence": False,
    }
    write_json(summary_out, summary)
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC V2 modular edit engine batch generation")
    parser.add_argument("--edit-plan", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--out-manifest", required=True)
    parser.add_argument("--rejected-out", required=True)
    parser.add_argument("--summary-out", required=True)
    parser.add_argument("--engine", choices=sorted(ALL_ENGINES))
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--allow-full-run", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--quality-config-json")
    args = parser.parse_args(argv)
    quality_config = json.loads(args.quality_config_json) if args.quality_config_json else None
    try:
        summary = batch_generate(
            args.edit_plan,
            args.out_dir,
            args.out_manifest,
            args.rejected_out,
            args.summary_out,
            engine=args.engine,
            max_items=args.max_items,
            allow_full_run=args.allow_full_run,
            seed=args.seed,
            resume=args.resume,
            fail_fast=args.fail_fast,
            overwrite=args.overwrite,
            quality_config=quality_config,
        )
    except EditGenerationError as exc:
        raise SystemExit(f"Batch edit generation failed: {exc}") from None
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
