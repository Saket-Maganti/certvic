"""CLI wrapper for the detectability-first tiny-pilot gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import write_json
from certvic.validation.detectability_gate import (
    evaluate_gate,
    load_detectability_summary,
    load_quality_summary,
    render_gate_report,
)


def build_go_no_go(detectability: str, quality: str, out: str, json_out: str) -> dict:
    result = evaluate_gate(load_detectability_summary(detectability), load_quality_summary(quality))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(render_gate_report(result), encoding="utf-8")
    write_json(json_out, result)
    return {"out": out, "json_out": json_out, "status": result["status"], "passed": result["status"] == "GO"}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build tiny-pilot detectability go/no-go decision")
    parser.add_argument("--detectability", required=True)
    parser.add_argument("--quality", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(build_go_no_go(args.detectability, args.quality, args.out, args.json_out), sort_keys=True))


if __name__ == "__main__":
    main()
