"""Portable, byte-verified task bundles for CertVIC scientific runtimes.

The manifest content lock intentionally excludes ``tasks.jsonl`` to avoid a
hash cycle: every task binds that lock, then the final bundle hash binds the
resulting task file plus all payload files.  Both hashes are rebase invariant.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.task_schema import require_task_matrix, with_task_hash
from certvic.cvpr.transactional import read_jsonl


BUNDLE_SCHEMA = "certvic.cvpr.task_bundle.v1"
PATH_CONTRACT = "BUNDLE_RELATIVE"
TASKS_PATH = "tasks.jsonl"
MANIFEST_NAME = "task_bundle_manifest.json"

PATH_SPECS: dict[str, tuple[str, str, str | None]] = {
    "source_image_path": ("images/source", "SOURCE_IMAGE", "source_image_hash"),
    "original_image_path": ("images/original", "ORIGINAL_IMAGE", None),
    "edited_image_path": ("images/edited", "EDITED_IMAGE", None),
    "target_mask_path": ("masks/target", "TARGET_MASK", "target_mask_hash"),
    "protected_scene_mask_path": (
        "masks/protected", "PROTECTED_SCENE_MASK", "protected_scene_mask_hash"
    ),
    "insertion_asset_path": ("assets/insertion", "INSERTION_ASSET", "insertion_asset_sha256"),
    "candidate_asset": ("assets/candidate", "CANDIDATE_ASSET", None),
}


class TaskBundleError(ValueError):
    """A bundle is unsafe, incomplete, or differs from its content lock."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_identifier(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._")
    return text[:120] or "task"


def _relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise TaskBundleError(f"unsafe bundle-relative path: {value}")
    return path


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _content_lock(*, study: str, task_ids: list[str], files: list[dict[str, Any]]) -> str:
    payload = {
        "schema": BUNDLE_SCHEMA,
        "study": study,
        "task_schema": "certvic.cvpr.task.v1",
        "task_ids": sorted(task_ids),
        "payload_files": sorted(files, key=lambda row: row["path"]),
    }
    return sha256_bytes(canonical_json_bytes(payload))


def create_bundle(
    tasks: list[dict[str, Any]], bundle_root: str | Path, *, replace: bool = False,
) -> dict[str, Any]:
    """Copy task payloads and write a portable bundle plus final manifest."""
    if not tasks:
        raise TaskBundleError("cannot create an empty task bundle")
    root = Path(bundle_root)
    if root.exists() and any(root.iterdir()):
        if not replace:
            raise TaskBundleError(f"bundle root is not empty: {root}")
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    studies = {str(row.get("study")) for row in tasks}
    if len(studies) != 1:
        raise TaskBundleError("one task bundle must contain exactly one study")
    study = studies.pop()
    task_ids = [str(row.get("task_id", row.get("item_id", ""))) for row in tasks]
    if not all(task_ids) or len(task_ids) != len(set(task_ids)):
        raise TaskBundleError("task IDs must be unique and nonblank")

    copied: dict[tuple[str, str], str] = {}
    file_roles: dict[str, set[str]] = defaultdict(set)
    file_tasks: dict[str, set[str]] = defaultdict(set)
    portable: list[dict[str, Any]] = []
    for row, task_id in zip(tasks, task_ids, strict=True):
        result = dict(row)
        bindings: list[dict[str, Any]] = []
        for field, (directory, role, declared_hash_field) in PATH_SPECS.items():
            value = row.get(field)
            if value in {None, ""}:
                continue
            source = Path(str(value))
            if not source.is_file():
                raise TaskBundleError(f"{task_id}: missing {field}: {source}")
            digest = _sha(source)
            declared = row.get(declared_hash_field) if declared_hash_field else None
            if declared not in {None, ""} and declared != digest:
                raise TaskBundleError(f"{task_id}: {field} differs from declared hash")
            key = (str(source.resolve()), directory)
            logical = copied.get(key)
            if logical is None:
                suffix = source.suffix.lower() or ".bin"
                name = f"{_safe_identifier(task_id)}-{digest[:16]}{suffix}"
                logical = f"{directory}/{name}"
                destination = root / _relative(logical)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                copied[key] = logical
            result[field] = logical
            if declared_hash_field:
                result[declared_hash_field] = digest
            size = (root / logical).stat().st_size
            bindings.append({
                "field": field, "path": logical, "sha256": digest, "size": size, "role": role,
            })
            file_roles[logical].add(role)
            file_tasks[logical].add(task_id)
        result["path_contract"] = PATH_CONTRACT
        result["bundle_files"] = sorted(bindings, key=lambda value: value["field"])
        portable.append(result)

    payload_files = []
    for logical in sorted(file_roles):
        path = root / logical
        payload_files.append({
            "path": logical,
            "size": path.stat().st_size,
            "sha256": _sha(path),
            "role": sorted(file_roles[logical]),
            "task_ids": sorted(file_tasks[logical]),
        })
    manifest_content_hash = _content_lock(
        study=study, task_ids=task_ids, files=payload_files,
    )
    portable = [with_task_hash({
        **row,
        "task_bundle_manifest_hash": manifest_content_hash,
        "bundle_manifest_content_hash": manifest_content_hash,
    }) for row in portable]
    require_task_matrix(portable, verify_files=True, bundle_root=root)
    tasks_path = root / TASKS_PATH
    tasks_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in portable), encoding="utf-8"
    )
    files = [*payload_files, {
        "path": TASKS_PATH, "size": tasks_path.stat().st_size, "sha256": _sha(tasks_path),
        "role": ["TASK_MANIFEST"], "task_ids": sorted(task_ids),
    }]
    manifest = {
        "schema": BUNDLE_SCHEMA,
        "study": study,
        "task_schema": "certvic.cvpr.task.v1",
        "path_contract": PATH_CONTRACT,
        "tasks_path": TASKS_PATH,
        "task_ids": sorted(task_ids),
        "task_count": len(task_ids),
        "manifest_content_hash": manifest_content_hash,
        "files": sorted(files, key=lambda value: value["path"]),
        "paper_evidence": False,
    }
    manifest["bundle_hash"] = sha256_bytes(canonical_json_bytes(manifest))
    _atomic_json(root / MANIFEST_NAME, manifest)
    return verify_bundle(root, root / MANIFEST_NAME)


def verify_bundle(bundle_root: str | Path, manifest_path: str | Path) -> dict[str, Any]:
    """Verify every declared byte and every task under an arbitrary bundle root."""
    root, path = Path(bundle_root), Path(manifest_path)
    if not path.is_file():
        raise TaskBundleError("task bundle manifest is missing")
    if path.resolve() != (root / MANIFEST_NAME).resolve():
        raise TaskBundleError("task bundle manifest must be rooted at bundle_root")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != BUNDLE_SCHEMA or manifest.get("path_contract") != PATH_CONTRACT:
        raise TaskBundleError("task bundle schema/path contract mismatch")
    expected_bundle_hash = sha256_bytes(canonical_json_bytes(
        {key: value for key, value in manifest.items() if key != "bundle_hash"}
    ))
    if manifest.get("bundle_hash") != expected_bundle_hash:
        raise TaskBundleError("task bundle hash mismatch")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise TaskBundleError("task bundle file inventory is empty")
    observed_paths: set[str] = set()
    for entry in files:
        logical = str(_relative(str(entry.get("path", ""))))
        if logical in observed_paths:
            raise TaskBundleError(f"duplicate bundle member: {logical}")
        observed_paths.add(logical)
        member = root / logical
        if not member.is_file():
            raise TaskBundleError(f"missing bundle member: {logical}")
        if member.stat().st_size != entry.get("size") or _sha(member) != entry.get("sha256"):
            raise TaskBundleError(f"bundle member bytes differ: {logical}")
    actual_paths = {
        member.relative_to(root).as_posix() for member in root.rglob("*")
        if member.is_file() and member.resolve() != path.resolve()
    }
    if actual_paths != observed_paths:
        raise TaskBundleError(
            f"bundle inventory mismatch: missing={sorted(observed_paths - actual_paths)}, "
            f"unmanifested={sorted(actual_paths - observed_paths)}"
        )
    payload_files = [entry for entry in files if entry.get("path") != manifest.get("tasks_path")]
    content_hash = _content_lock(
        study=str(manifest.get("study")),
        task_ids=[str(value) for value in manifest.get("task_ids", [])],
        files=payload_files,
    )
    if content_hash != manifest.get("manifest_content_hash"):
        raise TaskBundleError("task bundle manifest content hash mismatch")
    tasks_path = root / str(_relative(str(manifest.get("tasks_path", ""))))
    tasks = read_jsonl(tasks_path)
    require_task_matrix(tasks, verify_files=True, bundle_root=root)
    if sorted(str(row["task_id"]) for row in tasks) != sorted(manifest.get("task_ids", [])):
        raise TaskBundleError("task universe differs from bundle manifest")
    if any(row.get("task_bundle_manifest_hash") != content_hash for row in tasks):
        raise TaskBundleError("task does not bind the bundle manifest content hash")
    for row in tasks:
        declared = {binding["path"]: binding for binding in row.get("bundle_files", [])}
        for logical, binding in declared.items():
            member = root / str(_relative(logical))
            if member.stat().st_size != binding.get("size") or _sha(member) != binding.get("sha256"):
                raise TaskBundleError(f"task file binding differs: {row['task_id']}:{logical}")
    return {
        "status": "TASK_BUNDLE_VALID",
        "study": manifest["study"],
        "tasks": len(tasks),
        "files": len(files),
        "bundle_hash": manifest["bundle_hash"],
        "manifest_content_hash": content_hash,
        "task_hashes": [row["task_hash"] for row in tasks],
        "tasks_path": str(tasks_path),
        "paper_evidence": False,
    }


def bundle_diff(left_manifest: str | Path, right_manifest: str | Path) -> dict[str, Any]:
    left = json.loads(Path(left_manifest).read_text(encoding="utf-8"))
    right = json.loads(Path(right_manifest).read_text(encoding="utf-8"))
    left_files = {row["path"]: (row["sha256"], row["size"]) for row in left.get("files", [])}
    right_files = {row["path"]: (row["sha256"], row["size"]) for row in right.get("files", [])}
    return {
        "schema": "certvic.cvpr.task_bundle_diff.v1",
        "identical": left.get("bundle_hash") == right.get("bundle_hash"),
        "added": sorted(set(right_files) - set(left_files)),
        "removed": sorted(set(left_files) - set(right_files)),
        "changed": sorted(name for name in set(left_files) & set(right_files)
                          if left_files[name] != right_files[name]),
        "left_bundle_hash": left.get("bundle_hash"),
        "right_bundle_hash": right.get("bundle_hash"),
        "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create, migrate, verify, or diff task bundles")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("create", "migrate"):
        item = sub.add_parser(name)
        item.add_argument("--tasks", required=True)
        item.add_argument("--bundle-root", required=True)
        item.add_argument("--replace", action="store_true")
    verify = sub.add_parser("verify")
    verify.add_argument("--bundle-root", required=True)
    verify.add_argument("--manifest", required=True)
    diff = sub.add_parser("diff")
    diff.add_argument("--left-manifest", required=True)
    diff.add_argument("--right-manifest", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in {"create", "migrate"}:
            result = create_bundle(
                read_jsonl(args.tasks), args.bundle_root, replace=args.replace,
            )
        elif args.command == "verify":
            result = verify_bundle(args.bundle_root, args.manifest)
        else:
            result = bundle_diff(args.left_manifest, args.right_manifest)
    except (TaskBundleError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "TASK_BUNDLE_BLOCKED", "reason": str(exc),
                          "paper_evidence": False}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
