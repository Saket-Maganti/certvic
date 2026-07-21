"""CLI for building source manifests."""

from __future__ import annotations

import argparse
import json

from certvic.data.source_manifest import enrich_source_record, summarize_sources
from certvic.io import read_jsonl, write_jsonl
from certvic.schema import SourceImageRecord


def build_source_manifest(input_path: str, out_path: str, split: str) -> dict:
    records = []
    for row in read_jsonl(input_path):
        record = SourceImageRecord.model_validate(row)
        records.append(enrich_source_record(record, split=split))
    write_jsonl(out_path, records)
    return summarize_sources(records)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--split", default="pilot")
    args = parser.parse_args(argv)
    summary = build_source_manifest(args.input, args.out, args.split)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
