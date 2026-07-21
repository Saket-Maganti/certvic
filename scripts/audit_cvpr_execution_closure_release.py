"""Audit the sealed CVPR closure ZIP against its byte manifest and exclusion policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import PurePosixPath


FORBIDDEN_SUFFIXES = {".safetensors", ".pt", ".pth", ".ckpt", ".onnx"}


def audit(path: str) -> dict[str, object]:
    errors: list[str] = []
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        if len(names) != len(set(names)):
            errors.append("duplicate ZIP members")
        if archive.testzip() is not None:
            errors.append("corrupt ZIP member")
        unsafe = [name for name in names if PurePosixPath(name).is_absolute()
                  or ".." in PurePosixPath(name).parts]
        if unsafe:
            errors.append(f"unsafe member paths: {unsafe[:5]}")
        manifests = [name for name in names if name.endswith(
            "release/cvpr_execution_closure/RELEASE_FILE_MANIFEST.json"
        )]
        if len(manifests) != 1:
            errors.append("expected exactly one closure release manifest")
            manifest = {"files": {}}
        else:
            manifest = json.loads(archive.read(manifests[0]))
        expected = manifest.get("files", {})
        if not isinstance(expected, dict):
            expected = {}
            errors.append("release manifest files mapping is invalid")
        expected_members = set(expected) | set(manifests)
        if set(names) != expected_members:
            errors.append("ZIP membership differs from release manifest")
        for name, expected_hash in expected.items():
            if name in names and hashlib.sha256(archive.read(name)).hexdigest() != expected_hash:
                errors.append(f"hash mismatch: {name}")
        weights = [name for name in names if PurePosixPath(name).suffix.lower() in FORBIDDEN_SUFFIXES]
        if weights:
            errors.append(f"model-weight-like members forbidden: {weights[:5]}")
        image_members = [name for name in names
                         if PurePosixPath(name).suffix.lower() in {".png", ".jpg", ".jpeg"}]
        unexpected_images = [name for name in image_members
                             if "release/cvpr_execution_closure/synthetic_fixtures/" not in name]
        if unexpected_images:
            errors.append(f"unexpected image pixels: {unexpected_images[:5]}")
    return {
        "schema": "certvic.cvpr.execution_closure_release_audit.v1",
        "passed": not errors, "errors": errors, "members": len(names),
        "manifested_files": len(expected), "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit the CVPR execution-closure release")
    parser.add_argument("--archive", default="release/certvic_cvpr_execution_closure.zip")
    parser.add_argument("--out", default="reports/cvpr_execution_closure/release_audit.json")
    args = parser.parse_args(argv)
    result = audit(args.archive)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

