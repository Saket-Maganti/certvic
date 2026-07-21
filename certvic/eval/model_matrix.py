"""Model run orchestration matrix (V3 prompt 08).

Plans future open-model evaluation runs as a matrix of providers × prompt
variants × shards over a task set, emitting resumable `run_eval` commands, memory
estimates, and the sidecars each run will write. Planning only: no inference, no
downloads, no GPU, no paid providers.
"""

from __future__ import annotations


from certvic.providers.registry import (
    PAID_PROVIDER_NAMES,
    is_evidence_eligible_provider,
    provider_metadata,
)

DEFAULT_PRED_ROOT = "data/predictions"
DEFAULT_CONFIG = "configs/kaggle_open_vlm.yaml"

# Sidecars run_eval writes next to each predictions file.
EXPECTED_SIDECAR_SUFFIXES = (".run_manifest.json", ".provider_metadata.json", ".environment.json")


def _run_id(provider: str, prompt_variant: str, shard_index: int, num_shards: int) -> str:
    base = f"{provider}_{prompt_variant}_s{shard_index}of{num_shards}"
    return base.replace("/", "_")


def _memory_estimate(meta: dict) -> dict:
    full = float(meta.get("expected_gpu_memory_gb") or 0.0)
    return {
        "expected_gpu_memory_gb": full,
        "expected_gpu_memory_gb_4bit": round(full * 0.45, 1) if meta.get("supports_4bit") else full,
        "supports_4bit": bool(meta.get("supports_4bit")),
        "supports_batching": bool(meta.get("supports_batching")),
    }


def _command(cell: dict, config: str, tasks_path: str) -> str:
    return (
        "python3 -m certvic.eval.run_eval "
        f"--config {config} --tasks {tasks_path} --out {cell['expected_output_path']} "
        f"--provider {cell['provider']} --run-id {cell['run_id']} "
        f"--max-items {cell['max_items']} --shard-index {cell['shard_index']} --num-shards {cell['num_shards']} "
        "--evidence-run"
    )


def build_matrix(
    tasks_path: str,
    providers: list[str],
    *,
    max_items: int = 200,
    num_shards: int = 4,
    prompt_variants: list[str] | None = None,
    config: str = DEFAULT_CONFIG,
    pred_root: str = DEFAULT_PRED_ROOT,
) -> dict:
    if num_shards <= 0:
        raise ValueError("num_shards must be positive")
    if not providers:
        raise ValueError("at least one provider is required")
    paid = sorted(p for p in providers if p in PAID_PROVIDER_NAMES)
    if paid:
        raise ValueError(f"paid providers are not allowed in the run matrix: {paid}")

    prompt_variants = prompt_variants or ["default"]
    cells: list[dict] = []
    provider_summaries: dict[str, dict] = {}
    for provider in providers:
        meta = provider_metadata(provider)
        mem = _memory_estimate(meta)
        provider_summaries[provider] = {
            "provider_type": meta.get("provider_type"),
            "cost_status": meta.get("cost_status"),
            "tested_status": meta.get("tested_status"),
            "evidence_eligible": is_evidence_eligible_provider(provider),
            "memory_estimate": mem,
        }
        for variant in prompt_variants:
            for shard in range(num_shards):
                run_id = _run_id(provider, variant, shard, num_shards)
                out_path = f"{pred_root}/{provider}/{run_id}.jsonl"
                cell = {
                    "provider": provider,
                    "provider_type": meta.get("provider_type"),
                    "evidence_eligible": is_evidence_eligible_provider(provider),
                    "prompt_variant": variant,
                    "shard_index": shard,
                    "num_shards": num_shards,
                    "max_items": max_items,
                    "run_id": run_id,
                    "expected_output_path": out_path,
                    "expected_sidecars": [out_path + suffix for suffix in EXPECTED_SIDECAR_SUFFIXES],
                    "memory_estimate": mem,
                }
                cell["command"] = _command(cell, config, tasks_path)
                cells.append(cell)

    return {
        "matrix": "certvic_model_run_matrix",
        "tasks_path": tasks_path,
        "config": config,
        "pred_root": pred_root,
        "providers": providers,
        "prompt_variants": prompt_variants,
        "num_shards": num_shards,
        "max_items": max_items,
        "n_cells": len(cells),
        "provider_summaries": provider_summaries,
        "any_evidence_eligible": any(s["evidence_eligible"] for s in provider_summaries.values()),
        "cells": cells,
        "paid_providers": False,
        "downloads_attempted": False,
        "vlm_inference_run": False,
        "evidence_claims_made": False,
    }


def commands_sh(matrix: dict) -> str:
    lines = ["#!/usr/bin/env bash", "set -euo pipefail", "# Generated CertVIC model run matrix commands.", ""]
    for cell in matrix["cells"]:
        lines.append(f"# {cell['run_id']} (mem ~{cell['memory_estimate']['expected_gpu_memory_gb_4bit']} GB 4-bit)")
        lines.append(cell["command"])
    lines.append("")
    return "\n".join(lines)
