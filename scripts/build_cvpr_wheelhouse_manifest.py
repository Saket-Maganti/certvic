"""Create or verify a byte-level manifest for a pre-staged offline wheelhouse."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from certvic.cvpr.environment_lock import WHEEL_RE, environment_lock_hash, verify_wheelhouse


def _metadata(path: Path, packages: dict[str, str]) -> dict[str, object]:
    stem = path.name[:-4]
    parts = stem.rsplit("-", 4)
    if len(parts) != 5:
        raise ValueError(f"wheel filename cannot be parsed: {path.name}")
    distribution, version, python_tag, _abi_tag, platform_tag = parts
    normalized = re.sub(r"[-_.]+", "-", distribution).lower()
    matching = [name for name in packages if re.sub(r"[-_.]+", "-", name).lower() == normalized]
    if len(matching) != 1 or packages[matching[0]] != version:
        raise ValueError(f"wheel does not match environment lock: {path.name}")
    return {
        "filename": path.name,
        "package": matching[0],
        "version": version,
        "python_tag": python_tag,
        "platform_tag": platform_tag,
        "size": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "dependency_role": "LOCKED_RUNTIME_DEPENDENCY",
    }


def build(wheelhouse: str | Path, lock_path: str | Path, out: str | Path) -> dict[str, object]:
    root = Path(wheelhouse)
    wheels = sorted(path for path in root.iterdir() if path.is_file() and WHEEL_RE.fullmatch(path.name))
    if not wheels:
        raise ValueError("wheelhouse contains no wheel files; this command never downloads them")
    lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    manifest = {
        "schema": "certvic.cvpr.wheelhouse_manifest.v1",
        "environment_lock_hash": environment_lock_hash(lock_path),
        "files": {path.name: _metadata(path, lock["packages"]) for path in wheels},
        "network_used": False,
        "paper_evidence": False,
    }
    Path(out).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hash or verify a pre-staged CVPR wheelhouse")
    parser.add_argument("--wheelhouse", required=True)
    parser.add_argument("--lock", default="configs/runtime/kaggle_t4x2_environment.lock.json")
    parser.add_argument("--out")
    parser.add_argument("--verify-manifest")
    args = parser.parse_args(argv)
    if args.verify_manifest:
        result = verify_wheelhouse(args.wheelhouse, args.verify_manifest)
    else:
        if not args.out:
            parser.error("--out is required when building a manifest")
        result = build(args.wheelhouse, args.lock, args.out)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("passed", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
