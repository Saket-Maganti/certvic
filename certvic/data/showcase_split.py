"""Build a small CC0/public-domain showcase split without copying pixels by default."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import read_jsonl, write_json, write_jsonl

ALLOWED_LICENSES = {"cc0", "public_domain", "pd", "public domain"}


def build_showcase_split(sources: str, out: str, *, max_items: int = 50) -> dict:
    rows = read_jsonl(sources)
    accepted: list[dict] = []
    rejected: list[dict] = []
    for row in rows:
        license_name = str(row.get("license") or row.get("license_id") or "").lower()
        redistributable = bool(row.get("redistributable") or row.get("release_mode") == "redistributable")
        if license_name in ALLOWED_LICENSES and redistributable:
            item = dict(row)
            item["showcase_use"] = True
            item["figure_use_ok"] = True
            item["pixels_copied"] = False
            accepted.append(item)
        else:
            rejected.append({"source_id": row.get("source_id"), "reason": "not_cc0_pd_or_not_redistributable"})
        if len(accepted) >= max_items:
            break
    write_jsonl(out, accepted)
    summary = {
        "sources": sources,
        "out": out,
        "accepted": len(accepted),
        "rejected": len(rejected),
        "pixels_copied": False,
        "evidence_status": "SHOWCASE_SPLIT_ONLY",
    }
    write_json(str(Path(out).with_suffix(".summary.json")), summary)
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build CC0/PD showcase split")
    parser.add_argument("--sources", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-items", type=int, default=50)
    args = parser.parse_args(argv)
    print(json.dumps(build_showcase_split(args.sources, args.out, max_items=args.max_items), sort_keys=True))


if __name__ == "__main__":
    main()

