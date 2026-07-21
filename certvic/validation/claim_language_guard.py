"""Enhanced claim-language guard for paper/docs/reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FORBIDDEN_PATTERNS = {
    "causal_overclaim": ["proves causal understanding", "cannot reason causally"],
    "deployment_safety": ["safe for deployment", "unsafe for deployment"],
    "universal_vlm": ["all vlms"],
    "frontier_model": ["frontier models fail"],
    "benchmark_first": ["state of the art benchmark"],
    "bootstrap_certification": ["bootstrap-certified", "bootstrap certification"],
    "novelty_first": ["first to prove"],
    "phase_c_scientific_overclaim": [
        "large gap proves responsiveness",
        "primary responsiveness gap",
        "universal specificity",
        "prospective confirmatory evidence is complete",
        "genuine human validation is complete",
    ],
}
ALLOWLIST_PARTS = ("prompt_pack", "CLAIM_LANGUAGE_GUARD", "V5_CLAIM_LANGUAGE")


def scan_claim_language(roots: list[str]) -> dict:
    findings: list[dict] = []
    for raw in roots:
        root = Path(raw)
        paths = [root] if root.is_file() else sorted(root.rglob("*")) if root.exists() else []
        for path in paths:
            if not path.is_file() or path.suffix.lower() not in {".md", ".tex"}:
                continue
            display = path.as_posix()
            if any(part in display for part in ALLOWLIST_PARTS):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for category, patterns in FORBIDDEN_PATTERNS.items():
                for pattern in patterns:
                    if pattern in text:
                        findings.append({"file": display, "category": category, "pattern": pattern})
    return {"roots": roots, "findings": findings, "passed": not findings}


def render_report(result: dict) -> str:
    lines = ["# Claim Language Guard Report", "", f"Passed: {result['passed']}", ""]
    if result["findings"]:
        lines += ["| File | Category | Pattern |", "| --- | --- | --- |"]
        for row in result["findings"]:
            lines.append(f"| `{row['file']}` | {row['category']} | `{row['pattern']}` |")
    else:
        lines.append("No forbidden claim-language patterns found.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan claim language")
    parser.add_argument("--root", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = scan_claim_language(args.root)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"out": args.out, "passed": result["passed"], "n_findings": len(result["findings"])}, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
