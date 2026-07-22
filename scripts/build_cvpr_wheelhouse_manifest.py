"""Create or verify a byte-level manifest for a pre-staged offline wheelhouse."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.cvpr.environment_lock import environment_lock_hash, verify_wheelhouse
from certvic.cvpr.wheelhouse_builder import verify_wheel_root


def build(
    wheelhouse: str | Path,
    lock_path: str | Path,
    out: str | Path,
    *,
    profile_id: str,
    requirements_root: str | Path,
) -> dict[str, object]:
    root = Path(wheelhouse)
    compatibility = verify_wheel_root(
        root, requirements_root=requirements_root, profile_id=profile_id,
        environment_lock=lock_path,
    )
    if not compatibility["passed"]:
        raise ValueError(f"wheelhouse profile validation failed: {compatibility}")
    manifest = {
        "schema": "certvic.cvpr.wheelhouse_manifest.v3",
        "environment_lock_hash": environment_lock_hash(lock_path),
        "runtime_profile_id": profile_id,
        "runtime_profile_hash": compatibility["runtime_profile_hash"],
        "required_packages": compatibility["required_packages"],
        "supported_tags": compatibility["supported_tags"],
        "files": compatibility["files"],
        "network_used": False,
        "paper_evidence": False,
    }
    Path(out).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hash or verify a pre-staged CVPR wheelhouse")
    parser.add_argument("--wheelhouse", required=True)
    parser.add_argument("--lock", default="configs/runtime/kaggle_t4x2_environment.lock.json")
    parser.add_argument("--profile", default="kaggle_cp312_2026_07")
    parser.add_argument("--requirements-root", default="requirements")
    parser.add_argument("--out")
    parser.add_argument("--verify-manifest")
    args = parser.parse_args(argv)
    if args.verify_manifest:
        result = verify_wheelhouse(args.wheelhouse, args.verify_manifest)
    else:
        if not args.out:
            parser.error("--out is required when building a manifest")
        result = build(
            args.wheelhouse, args.lock, args.out,
            profile_id=args.profile, requirements_root=args.requirements_root,
        )
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("passed", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
