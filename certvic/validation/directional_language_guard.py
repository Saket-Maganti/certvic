"""Guard against drifting back to benchmark-only V6 framing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

BAD_PATTERNS = (
    "certvic is a benchmark",
    "robustness benchmark",
    "benchmark paper",
    "dataset paper",
    "vlms are inconsistent",
    "prove vlms reason",
    "prove vlms fail to reason",
    "causal understanding",
)
REQUIRED_FRAMING = ("visual decision update", "confound-controlled", "item-validity")
NEGATED_CONTEXT = (
    "not a",
    "not another",
    "avoid",
    "against",
    "attack",
    "reviewer",
    "forbidden",
    "risk",
    "no ",
    "no claims",
    "does not",
    "do not",
)


def _allowed_line(line: str) -> bool:
    lower = line.lower()
    return any(marker in lower for marker in NEGATED_CONTEXT)


def scan_directional_language(roots: list[str]) -> dict:
    findings: list[dict] = []
    framing_seen = False
    for raw in roots:
        root = Path(raw)
        paths = [root] if root.is_file() else sorted(root.rglob("*")) if root.exists() else []
        for path in paths:
            if not path.is_file() or path.suffix.lower() not in {".md", ".tex"}:
                continue
            if "certvic_codex_v" in path.as_posix() or "/audit_prompts/" in path.as_posix():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            lower_text = text.lower()
            if all(term in lower_text for term in REQUIRED_FRAMING):
                framing_seen = True
            for lineno, line in enumerate(text.splitlines(), start=1):
                lower = line.lower()
                for pattern in BAD_PATTERNS:
                    if pattern in lower and not _allowed_line(line):
                        findings.append({"file": path.as_posix(), "line": lineno, "pattern": pattern})
    return {"roots": roots, "findings": findings, "framing_seen": framing_seen, "passed": not findings and framing_seen}


def render_report(result: dict) -> str:
    lines = ["# V6 Directional Language Guard", "", f"Passed: {result['passed']}", f"Framing seen: {result['framing_seen']}", ""]
    if result["findings"]:
        lines += ["| File | Line | Pattern |", "| --- | ---: | --- |"]
        for row in result["findings"]:
            lines.append(f"| `{row['file']}` | {row['line']} | `{row['pattern']}` |")
    else:
        lines.append("No benchmark-only or unsupported directional-claim patterns found.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Scan V6 directional language")
    parser.add_argument("--root", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = scan_directional_language(args.root)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"out": args.out, "passed": result["passed"], "n_findings": len(result["findings"])}, sort_keys=True))


if __name__ == "__main__":
    main()
