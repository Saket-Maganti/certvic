"""Batch/resume evaluation runner."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from certvic.config import load_config
from certvic.eval.parse import parse_answer
from certvic.eval.prompts import build_prompt
from certvic.eval.resume import load_completed_keys
from certvic.eval.sharding import item_in_shard
from certvic.hashing import sha256_file, stable_record_hash
from certvic.io import append_jsonl, load_model_jsonl, write_json
from certvic.providers.registry import get_provider
from certvic.schema import ImageVariant, PredictionRecord, RunManifest, TaskItem
from certvic.validation.leakage import validate_task_no_leakage


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_run_manifest(out_path: str, args: argparse.Namespace, config: dict) -> None:
    task_hash = sha256_file(args.tasks) if args.tasks and Path(args.tasks).exists() else None
    manifest = RunManifest(
        run_id=args.run_id,
        provider=args.provider,
        config_hash=stable_record_hash(config),
        task_manifest_hash=task_hash,
        timestamp_utc=_utc_now(),
        command_args=vars(args),
        zero_cost_policy_ack=True,
        paid_services_used=False,
    )
    write_json(f"{out_path}.run_manifest.json", manifest)


def _write_provider_sidecars(out_path: str, provider, provider_name: str) -> None:
    """Write provider-metadata and environment sidecars next to the predictions."""
    from certvic.eval.vlm_preflight import environment_summary
    from certvic.providers.registry import provider_metadata

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    meta = provider_metadata(provider_name)
    meta["provider_type_runtime"] = getattr(provider, "provider_type", "unknown")
    meta["cost_policy_runtime"] = getattr(provider, "cost_policy", "unknown")
    write_json(f"{out_path}.provider_metadata.json", meta)
    write_json(f"{out_path}.environment.json", environment_summary(check_gpu=False))


def run_eval(
    config_path: str,
    tasks_path: str,
    out_path: str,
    provider_name: str,
    run_id: str,
    max_items: int | None = None,
    shard_index: int = 0,
    num_shards: int = 1,
    dry_run: bool = False,
    strict_leakage: bool = False,
    overwrite: bool = False,
    fail_fast: bool = False,
    evidence_run: bool = False,
) -> dict:
    config = load_config(config_path)
    tasks = load_model_jsonl(tasks_path, TaskItem)

    if evidence_run:
        from certvic.providers.registry import is_evidence_eligible_provider

        if not is_evidence_eligible_provider(provider_name):
            raise ValueError(
                f"evidence_run blocked: provider '{provider_name}' is not an evidence-eligible open-local provider"
            )
        statuses = {str(task.metadata.get("evidence_status", "UNKNOWN")).upper() for task in tasks}
        if not statuses <= {"HUMAN_REVIEWED_NON_EVIDENCE", "EVIDENCE", "CERTIFIED"}:
            raise ValueError(f"evidence_run blocked: tasks must be reviewed; found {sorted(statuses)}")

    if num_shards > 1:
        tasks = [task for task in tasks if item_in_shard(task.item_id, shard_index, num_shards)]
    if max_items is not None:
        tasks = tasks[:max_items]

    provider = get_provider(provider_name, config)
    if hasattr(provider, "set_task_context"):
        provider.set_task_context(tasks)

    _write_provider_sidecars(out_path, provider, provider_name)

    if overwrite and Path(out_path).exists():
        Path(out_path).unlink()
    if overwrite and Path(f"{out_path}.run_manifest.json").exists():
        Path(f"{out_path}.run_manifest.json").unlink()
    completed = set() if overwrite else load_completed_keys(out_path)
    written = 0
    skipped = 0
    errors = 0

    ns = argparse.Namespace(
        config=config_path,
        tasks=tasks_path,
        out=out_path,
        provider=provider_name,
        run_id=run_id,
        max_items=max_items,
        shard_index=shard_index,
        num_shards=num_shards,
        dry_run=dry_run,
        strict_leakage=strict_leakage,
        overwrite=overwrite,
    )
    _write_run_manifest(out_path, ns, config)

    if dry_run:
        return {"tasks": len(tasks), "written": 0, "skipped": 0, "errors": 0, "dry_run": True}

    for task in tasks:
        leakage = validate_task_no_leakage(task)
        if leakage and strict_leakage:
            raise ValueError(f"Leakage validation failed for {task.item_id}: {leakage}")
        for variant, image_path in [
            (ImageVariant.ORIGINAL.value, task.original_image_path),
            (ImageVariant.EDITED.value, task.edited_image_path),
        ]:
            key = (run_id, task.item_id, variant)
            if key in completed:
                skipped += 1
                continue
            prompt = build_prompt(task, variant)
            start = time.time()
            try:
                raw = provider.answer(image_path, prompt)
                parsed = parse_answer(raw, task.answer_format, strict=True)
                metadata = {
                    "evidence_status": task.metadata.get("evidence_status", "UNKNOWN"),
                    "provider_evidence_status": getattr(provider, "evidence_status", "UNKNOWN"),
                    "provider_non_evidence": bool(getattr(provider, "non_evidence", False)),
                }
            except Exception as exc:
                if fail_fast:
                    raise
                raw = ""
                parsed = parse_answer("", task.answer_format, strict=True)
                metadata = {
                    "error": repr(exc),
                    "evidence_status": task.metadata.get("evidence_status", "UNKNOWN"),
                    "provider_evidence_status": getattr(provider, "evidence_status", "UNKNOWN"),
                    "provider_non_evidence": bool(getattr(provider, "non_evidence", False)),
                }
                errors += 1
            pred = PredictionRecord(
                run_id=run_id,
                item_id=task.item_id,
                provider_name=getattr(provider, "provider_name", provider_name),
                provider_type=getattr(provider, "provider_type", "mock"),
                model_name=getattr(provider, "model_name", provider_name),
                model_version=getattr(provider, "model_version", "v1"),
                image_variant=variant,
                prompt=prompt,
                raw_output=raw,
                parsed_answer=parsed.parsed_answer,
                parse_confidence=parsed.parse_confidence,
                parse_ok=parsed.parse_ok,
                latency_s=time.time() - start,
                timestamp_utc=_utc_now(),
                metadata=metadata,
            )
            append_jsonl(out_path, pred)
            completed.add(key)
            written += 1
    return {"tasks": len(tasks), "written": written, "skipped": skipped, "errors": errors}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict-leakage", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--evidence-run", action="store_true")
    args = parser.parse_args(argv)
    summary = run_eval(
        config_path=args.config,
        tasks_path=args.tasks,
        out_path=args.out,
        provider_name=args.provider,
        run_id=args.run_id,
        max_items=args.max_items,
        shard_index=args.shard_index,
        num_shards=args.num_shards,
        dry_run=args.dry_run,
        strict_leakage=args.strict_leakage,
        overwrite=args.overwrite,
        fail_fast=args.fail_fast,
        evidence_run=args.evidence_run,
    )
    print(json.dumps(summary, sort_keys=True))
    if summary["errors"]:
        print(f"completed with {summary['errors']} item errors", file=sys.stderr)


if __name__ == "__main__":
    main()
