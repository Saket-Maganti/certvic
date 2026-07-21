"""Strict whole-study validator and deterministic generation packager."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import stat
import zipfile
from pathlib import Path
from typing import Any

from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.transactional import read_jsonl
from certvic.cvpr.task_schema import require_task_matrix


class GenerationPackageError(ValueError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(root: Path, value: str | Path) -> Path:
    path = Path(value)
    path = path if path.is_absolute() else root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise GenerationPackageError(f"package path escapes generation root: {value}") from exc
    if path.is_symlink():
        raise GenerationPackageError(f"symlinks are prohibited in generation packages: {value}")
    return path


def _expected(tasks: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for task in tasks:
        identity = str(task.get("item_id", ""))
        if not identity:
            raise GenerationPackageError("study task is missing item_id")
        variants = task.get("expected_generation_variants", task.get("expected_variants", ["edited"]))
        if not isinstance(variants, list) or not variants:
            raise GenerationPackageError(f"{identity}: expected variants must be a nonempty list")
        for variant in variants:
            key = identity, str(variant)
            if key in result:
                raise GenerationPackageError(f"duplicate expected task/variant: {key}")
            result[key] = task
    return result


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def assemble_generation_shards(
    tasks: list[dict[str, Any]], generation_root: str | Path, *, run_contract: dict[str, Any],
    environment_manifest: dict[str, Any], runtime_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Normalize completed control/semantic shard outputs for strict global validation."""
    tasks = require_task_matrix(tasks)
    root = Path(generation_root)
    expected = _expected(tasks)
    if any(variant != "edited" for _, variant in expected):
        raise GenerationPackageError("generation shard assembly currently requires edited-only tasks")
    run_hash = str(run_contract.get("run_contract_hash", ""))
    if len(run_hash) != 64:
        raise GenerationPackageError("generation assembly requires a hash-bound run contract")
    task_map = {str(task["task_id"]): task for task in tasks}
    shard_roots = sorted(path for path in root.glob("generation_shard_*") if path.is_dir())
    if not shard_roots:
        raise GenerationPackageError("no generation_shard_* directories found")
    records: list[dict[str, Any]] = []
    observed: set[str] = set()
    for shard_root in shard_roots:
        try:
            shard = int(shard_root.name.rsplit("_", 1)[1])
        except ValueError as exc:
            raise GenerationPackageError(f"invalid generation shard directory: {shard_root}") from exc
        control_manifest = shard_root / "generation_manifest.json"
        semantic_manifest = shard_root / "semantic_generation_manifest.json"
        if control_manifest.is_file() == semantic_manifest.is_file():
            raise GenerationPackageError(
                f"{shard_root.name}: expected exactly one control or semantic generation manifest"
            )
        manifest_path = control_manifest if control_manifest.is_file() else semantic_manifest
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = manifest.get("rows", manifest.get("records"))
        if not isinstance(rows, list):
            raise GenerationPackageError(f"{manifest_path}: generation rows are missing")
        members: list[dict[str, str]] = []
        for row in rows:
            item_id = str(row.get("item_id", row.get("edit_id", "")))
            if item_id not in task_map or item_id in observed:
                raise GenerationPackageError(f"unexpected or duplicate generated item: {item_id}")
            task = task_map[item_id]
            output_value = row.get("output_image_path", row.get("edited_image_path"))
            if not output_value or not Path(str(output_value)).is_file():
                raise GenerationPackageError(f"{item_id}: generated image is missing")
            output = root / "images" / f"{item_id}.png"
            output.parent.mkdir(parents=True, exist_ok=True)
            source_output = Path(str(output_value))
            if output.exists() and _sha(output) != _sha(source_output):
                raise GenerationPackageError(f"{item_id}: conflicting assembled image")
            if not output.exists():
                shutil.copy2(source_output, output)
            quality = row.get("quality", {})
            is_semantic = semantic_manifest.is_file()
            qa_pass = (
                quality.get("automated_qa_status") == "PASS"
                if is_semantic else (
                    row.get("status") in {"GENERATED", "EXISTING_VALID_OUTPUT"}
                    and row.get("metrics", {}).get("target_overlap_pixels") == 0
                )
            )
            if not qa_pass:
                raise GenerationPackageError(f"{item_id}: recomputed shard QA did not pass")
            qa = {
                "schema": "certvic.cvpr.generation_qa.v1", "item_id": item_id,
                "status": "PASS", "validation_source": "RECOMPUTED_FROM_GENERATION_RECORD",
                "source_record_sha256": sha256_bytes(canonical_json_bytes(row)),
                "paper_evidence": False,
            }
            qa_path = root / "qa" / f"{item_id}.json"
            _write_json(qa_path, qa)
            engine = str(row.get("final_engine_used", row.get("engine", "")))
            if not engine:
                raise GenerationPackageError(f"{item_id}: final engine is missing")
            engine_record = {
                "schema": "certvic.cvpr.generation_engine_record.v1", "item_id": item_id,
                "engine": engine, "engine_policy": row.get("engine_policy", task.get(
                    "edit_engine_policy"
                )), "selection_reason": row.get("engine_selection_reason"),
                "fallback_sequence": row.get("engine_fallback_sequence", task.get(
                    "engine_fallbacks", []
                )), "paper_evidence": False,
            }
            engine_path = root / "engine_records" / f"{item_id}.json"
            _write_json(engine_path, engine_record)
            records.append({
                "item_id": item_id, "variant": "edited", "shard": shard,
                "task_sha256": task["task_hash"], "run_contract_hash": run_hash,
                "engine": engine, "output_path": output.relative_to(root).as_posix(),
                "output_sha256": _sha(output),
                "qa_record_path": qa_path.relative_to(root).as_posix(),
                "qa_record_sha256": _sha(qa_path),
                "engine_record_path": engine_path.relative_to(root).as_posix(),
                "engine_record_sha256": _sha(engine_path),
            })
            members.append({"item_id": item_id, "variant": "edited"})
            observed.add(item_id)
        _write_json(root / f"shard_{shard}" / "shard_manifest.json", {
            "schema": "certvic.cvpr.generation_shard_manifest.v1", "status": "SHARD_COMPLETE",
            "shard": shard, "members": sorted(members, key=lambda value: value["item_id"]),
            "paper_evidence": False,
        })
    if observed != set(task_map):
        raise GenerationPackageError(
            f"assembled shard universe mismatch; missing={sorted(set(task_map) - observed)}"
        )
    records.sort(key=lambda row: (row["item_id"], row["variant"]))
    (root / "generation_records.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in records), encoding="utf-8"
    )
    _write_json(root / "run_contract.json", run_contract)
    _write_json(root / "environment_manifest.json", environment_manifest)
    _write_json(root / "runtime_manifest.json", {
        **runtime_manifest, "status": "COMPLETE", "records": len(records),
        "paper_evidence": False,
    })
    return {"status": "GENERATION_SHARDS_ASSEMBLED", "records": len(records),
            "shards": len(shard_roots), "paper_evidence": False}


def _load_shards(root: Path) -> tuple[list[Path], dict[tuple[str, str], int]]:
    paths = sorted(root.glob("shard_*/shard_manifest.json"))
    if not paths:
        paths = sorted((root / "shard_manifests").glob("*.json"))
    if not paths:
        raise GenerationPackageError("no shard manifests found")
    membership: dict[tuple[str, str], int] = {}
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("status") not in {"SHARD_COMPLETE", "COMPLETE"}:
            raise GenerationPackageError(f"incomplete shard manifest: {path}")
        shard = int(value["shard"])
        rows = value.get("members", value.get("items"))
        if not isinstance(rows, list):
            raise GenerationPackageError(f"shard membership missing: {path}")
        for row in rows:
            if isinstance(row, dict):
                key = str(row.get("item_id", "")), str(row.get("variant", "edited"))
            else:
                key = str(row), "edited"
            if key in membership:
                raise GenerationPackageError(f"duplicate shard membership: {key}")
            membership[key] = shard
    return paths, membership


def validate_generation_root(
    tasks: list[dict[str, Any]], generation_root: str | Path
) -> tuple[dict[str, Any], dict[str, bytes]]:
    root = Path(generation_root)
    tasks = require_task_matrix(tasks)
    expected = _expected(tasks)
    records_path = root / "generation_records.jsonl"
    if not records_path.is_file():
        raise GenerationPackageError("generation_records.jsonl is required")
    records = read_jsonl(records_path)
    observed: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = str(record.get("item_id", "")), str(record.get("variant", "edited"))
        if key in observed:
            raise GenerationPackageError(f"duplicate generation record: {key}")
        observed[key] = record
    missing = sorted(set(expected) - set(observed))
    extras = sorted(set(observed) - set(expected))
    errors: list[str] = []
    if missing:
        errors.append(f"missing task/variants: {missing}")
    if extras:
        errors.append(f"unexpected task/variants: {extras}")
    shard_paths, membership = _load_shards(root)
    if set(membership) != set(expected):
        errors.append("shard membership differs from the exact expected task/variant universe")
    run_contract_path = root / "run_contract.json"
    environment_path = root / "environment_manifest.json"
    runtime_path = root / "runtime_manifest.json"
    seed_path = root / "seed_manifest.json"
    for path in (run_contract_path, environment_path, runtime_path, seed_path):
        if not path.is_file():
            errors.append(f"required root manifest missing: {path.name}")
    run_contract = (
        json.loads(run_contract_path.read_text(encoding="utf-8")) if run_contract_path.is_file() else {}
    )
    expected_run_hash = str(run_contract.get("run_contract_hash", ""))
    if len(expected_run_hash) != 64:
        errors.append("root run contract has no valid run_contract_hash")
    members: dict[str, bytes] = {}
    required_paths = [
        records_path, *shard_paths, run_contract_path, environment_path, runtime_path, seed_path,
    ]
    output_members: set[str] = set()
    qa_members: set[str] = set()
    engine_records: set[str] = set()
    for key in sorted(set(expected) & set(observed)):
        task, record = expected[key], observed[key]
        task_hash = str(task.get("task_hash") or sha256_bytes(canonical_json_bytes(task)))
        if record.get("task_sha256") != task_hash:
            errors.append(f"{key}: task hash mismatch")
        if int(record.get("shard", -1)) != membership.get(key):
            errors.append(f"{key}: record shard differs from shard manifest")
        if record.get("run_contract_hash") != expected_run_hash:
            errors.append(f"{key}: run contract hash mismatch")
        allowed_engines = task.get("allowed_engines")
        if allowed_engines is None:
            configured = task.get("selected_engine", task.get(
                "candidate_engine", task.get("generation_engine")
            ))
            allowed_engines = [configured] if configured else []
        if allowed_engines and record.get("engine") not in allowed_engines:
            errors.append(f"{key}: engine differs from study task contract")
        for field, collection in (
            ("output_path", output_members), ("qa_record_path", qa_members),
            ("engine_record_path", engine_records),
        ):
            value = record.get(field)
            if not value:
                errors.append(f"{key}: {field} missing")
                continue
            try:
                path = _relative(root, str(value))
            except GenerationPackageError as exc:
                errors.append(str(exc))
                continue
            if not path.is_file():
                errors.append(f"{key}: missing {field} file")
                continue
            relative = path.relative_to(root).as_posix()
            collection.add(relative)
            required_paths.append(path)
            declared = str(record.get(field.replace("_path", "_sha256"), ""))
            if declared and _sha(path) != declared:
                errors.append(f"{key}: {field} hash mismatch")
        output_path_value = record.get("output_path")
        if output_path_value:
            output_path = _relative(root, str(output_path_value))
            if output_path.is_file():
                try:
                    from PIL import Image

                    with Image.open(output_path) as opened:
                        opened.verify()
                except (OSError, ValueError) as exc:
                    errors.append(f"{key}: output image corrupt: {exc}")
    discovered_images = {
        path.relative_to(root).as_posix() for path in (root / "images").rglob("*") if path.is_file()
    } if (root / "images").is_dir() else set()
    if discovered_images != output_members:
        errors.append("image directory contains missing or unexpected image files")
    discovered_qa = {
        path.relative_to(root).as_posix() for path in (root / "qa").rglob("*") if path.is_file()
    } if (root / "qa").is_dir() else set()
    if discovered_qa != qa_members:
        errors.append("QA directory contains missing or unexpected records")
    if len(engine_records) != len(expected):
        errors.append("engine records are not one-to-one with expected task/variants")
    for path in required_paths:
        if path.is_file():
            members[path.relative_to(root).as_posix()] = path.read_bytes()
    report = {
        "schema": "certvic.cvpr.generation_package_validation.v1",
        "passed": not errors,
        "errors": errors,
        "expected_items": len(tasks),
        "expected_task_variants": len(expected),
        "observed_records": len(records),
        "shards": len(shard_paths),
        "images": len(output_members),
        "qa_records": len(qa_members),
        "engine_records": len(engine_records),
        "run_contract_hash": expected_run_hash,
        "validation_source": "RECOMPUTED_GLOBAL_CHECKS",
        "paper_evidence": False,
    }
    return report, members


def _archive_bytes(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, members[name])
    return buffer.getvalue()


def package_generation(
    tasks: list[dict[str, Any]], generation_root: str | Path, out_zip: str | Path, *, strict: bool
) -> dict[str, Any]:
    root = Path(generation_root)
    seed_path = root / "seed_manifest.json"
    if not seed_path.is_file():
        from certvic.cvpr.t4x2 import derive_seed_manifest, write_seed_manifest

        run_contract_path = root / "run_contract.json"
        contract = json.loads(run_contract_path.read_text()) if run_contract_path.is_file() else {}
        write_seed_manifest(seed_path, derive_seed_manifest(
            global_seed=int(contract.get("seed", 12013)),
            study=str(contract.get("study", "generation")),
            provider=str(contract.get("provider", "controls")),
            gpu_id=0,
            shard_id=0,
            task_ids=[str(task.get("item_id", task.get("edit_id"))) for task in tasks],
            attempts=1,
        ))
    report, members = validate_generation_root(tasks, generation_root)
    if strict and not report["passed"]:
        raise GenerationPackageError("; ".join(report["errors"]))
    report_bytes = json.dumps(report, indent=2, sort_keys=True).encode() + b"\n"
    members["global_validation_report.json"] = report_bytes
    hashes = {name: hashlib.sha256(payload).hexdigest() for name, payload in sorted(members.items())}
    members["hash_manifest.json"] = json.dumps(
        {"schema": "certvic.cvpr.generation_hash_manifest.v1", "files": hashes},
        indent=2, sort_keys=True,
    ).encode() + b"\n"
    first = _archive_bytes(members)
    second = _archive_bytes(members)
    if first != second:
        raise GenerationPackageError("deterministic ZIP rebuild was not byte-identical")
    destination = Path(out_zip)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(first)
    return {
        "status": "GENERATION_PACKAGE_VALIDATED_AND_WRITTEN" if report["passed"]
        else "GENERATION_PACKAGE_WRITTEN_NONSTRICT_WITH_ERRORS",
        "validation": report,
        "archive_sha256": hashlib.sha256(first).hexdigest(),
        "archive_bytes": len(first),
        "members": len(members),
        "deterministic_rebuild": True,
        "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and package a complete generation study")
    parser.add_argument("--study-manifest", required=True)
    parser.add_argument("--generation-root", required=True)
    parser.add_argument("--out-zip", required=True)
    parser.add_argument("--assemble-shards", action="store_true")
    parser.add_argument("--run-contract")
    parser.add_argument("--environment-manifest")
    parser.add_argument("--runtime-manifest")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        tasks = read_jsonl(args.study_manifest)
        if args.assemble_shards:
            required = (args.run_contract, args.environment_manifest, args.runtime_manifest)
            if any(value is None for value in required):
                raise GenerationPackageError(
                    "--assemble-shards requires run, environment, and runtime manifests"
                )
            assemble_generation_shards(
                tasks, args.generation_root,
                run_contract=json.loads(Path(args.run_contract).read_text(encoding="utf-8")),
                environment_manifest=json.loads(Path(args.environment_manifest).read_text(
                    encoding="utf-8"
                )),
                runtime_manifest=json.loads(Path(args.runtime_manifest).read_text(encoding="utf-8")),
            )
        result = package_generation(tasks, args.generation_root,
                                    args.out_zip, strict=args.strict)
    except GenerationPackageError as exc:
        result = {"status": "BLOCKED_INVALID_GENERATION_ROOT", "errors": [str(exc)],
                  "paper_evidence": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "GENERATION_PACKAGE_VALIDATED_AND_WRITTEN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
