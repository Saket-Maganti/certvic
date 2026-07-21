"""Compare current result files against a result lockfile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.hashing import sha256_file
from certvic.io import read_json


def compare_lockfile(lockfile: str) -> dict:
    lock = read_json(lockfile)
    root = Path(lock["results_root"])
    changed: list[str] = []
    missing: list[str] = []
    for entry in lock.get("files", []):
        path = root / entry["path"]
        if not path.exists():
            missing.append(entry["path"])
        elif sha256_file(path) != entry["sha256"]:
            changed.append(entry["path"])
    return {"lockfile": lockfile, "changed": changed, "missing": missing, "passed": not changed and not missing}


def render_diff(result: dict) -> str:
    return "\n".join(
        [
            "# Result Lock Diff",
            "",
            f"Passed: {result['passed']}",
            f"Changed: {result['changed']}",
            f"Missing: {result['missing']}",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare a result lockfile")
    parser.add_argument("--lockfile", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = compare_lockfile(args.lockfile)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_diff(result), encoding="utf-8")
    print(json.dumps({"out": args.out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()

