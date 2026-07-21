"""Freeze result files into a hash lockfile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.hashing import sha256_file
from certvic.io import write_json

NON_EVIDENCE_MARKERS = ("MOCK", "SIMULATED", "NON_EVIDENCE", "PLANNED")


def freeze_results(results_root: str, out: str) -> dict:
    root = Path(results_root)
    files = sorted(p for p in root.rglob("*") if p.is_file()) if root.exists() else []
    entries: list[dict] = []
    claim_eligible = True
    for path in files:
        rel = path.relative_to(root).as_posix()
        text = ""
        if path.stat().st_size < 1_000_000:
            text = path.read_text(encoding="utf-8", errors="ignore")
        if any(marker in text.upper() for marker in NON_EVIDENCE_MARKERS):
            claim_eligible = False
        entries.append({"path": rel, "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    lockfile = {
        "results_root": results_root,
        "n_files": len(entries),
        "files": entries,
        "claim_eligible": claim_eligible and bool(entries),
        "git_required": False,
        "posthoc_change_lock": True,
    }
    write_json(out, lockfile)
    return lockfile


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Freeze result files")
    parser.add_argument("--results-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = freeze_results(args.results_root, args.out)
    print(json.dumps({"out": args.out, "n_files": result["n_files"], "claim_eligible": result["claim_eligible"]}, sort_keys=True))


if __name__ == "__main__":
    main()

