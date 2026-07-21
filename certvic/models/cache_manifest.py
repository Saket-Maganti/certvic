"""Create user-managed model-cache manifests without downloading weights."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.hashing import sha256_file
from certvic.io import write_json
from certvic.providers.registry import provider_metadata


def build_cache_manifest(provider: str, cache_root: str, *, hash_files: bool = False) -> dict:
    root = Path(cache_root).expanduser()
    files: list[dict] = []
    if root.exists():
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            rel = path.relative_to(root).as_posix()
            entry = {"path": rel, "size_bytes": path.stat().st_size}
            if hash_files:
                entry["sha256"] = sha256_file(path)
            files.append(entry)
    total_size = sum(int(f["size_bytes"]) for f in files)
    return {
        "manifest": "certvic_model_cache_manifest",
        "provider": provider,
        "provider_metadata": provider_metadata(provider),
        "cache_root": str(root),
        "cache_root_exists": root.exists(),
        "files": files,
        "n_files": len(files),
        "total_size_bytes": total_size,
        "downloads_attempted": False,
        "evidence_status": "CACHE_MANIFEST_ONLY",
        "missing": [] if root.exists() else ["cache_root_missing"],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build a model-cache manifest")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--hash-files", action="store_true")
    args = parser.parse_args(argv)
    manifest = build_cache_manifest(args.provider, args.cache_root, hash_files=args.hash_files)
    write_json(args.out, manifest)
    print(json.dumps({"out": args.out, "n_files": manifest["n_files"], "missing": manifest["missing"]}, sort_keys=True))


if __name__ == "__main__":
    main()

