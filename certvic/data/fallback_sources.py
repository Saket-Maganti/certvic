"""Fallback dataset option reporting for V4."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.data.openimages_adapter_stub import adapter_summary as openimages_summary
from certvic.data.wikimedia_adapter_stub import adapter_summary as wikimedia_summary


def fallback_options() -> list[dict]:
    return [
        {
            "dataset": "ADE20K",
            "role": "primary",
            "pointer_only_default": True,
            "downloads_attempted": False,
            "license_risks": ["non-redistributable pixels by default"],
        },
        openimages_summary(),
        wikimedia_summary(),
    ]


def render_report(options: list[dict]) -> str:
    lines = [
        "# Fallback Dataset Options",
        "",
        "ADE20K remains primary. Fallback adapters are pointer-only plans and do not download data.",
        "",
        "| Dataset | Role/status | Pointer-only | Risks |",
        "| --- | --- | --- | --- |",
    ]
    for option in options:
        role = option.get("role") or option.get("status")
        risks = "; ".join(option.get("license_risks", []))
        lines.append(f"| {option['dataset']} | {role} | {option.get('pointer_only', option.get('pointer_only_default'))} | {risks} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write fallback dataset options")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    options = fallback_options()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(options), encoding="utf-8")
    print(json.dumps({"out": args.out, "n_options": len(options), "downloads_attempted": False}, sort_keys=True))


if __name__ == "__main__":
    main()

