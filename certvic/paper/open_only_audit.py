"""Audit the open-only evaluation scope language."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = (
    "zero-cost",
    "open vlms actually run",
    "model-agnostic",
    "limitation",
)
CLOSED_MODEL_NAMES = ("gpt", "gemini", "claude")


def audit_open_only(paper_dir: str | Path = "paper") -> dict:
    root = Path(paper_dir)
    raw_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in sorted(root.rglob("*.tex"))).lower()
    text = " ".join(raw_text.split())
    missing = [term for term in REQUIRED if term not in text]
    closed_claims = []
    for name in CLOSED_MODEL_NAMES:
        if name in text and "optional" not in text and "non-core" not in text and "future" not in text:
            closed_claims.append(name)
    return {
        "audit": "open_only_scope",
        "passed": not missing and not closed_claims,
        "missing_required_terms": missing,
        "closed_model_claims": closed_claims,
    }


def render_report(result: dict) -> str:
    return "\n".join(
        [
            "# V6 Open-Only Audit",
            "",
            f"Passed: {result['passed']}",
            f"Missing required terms: {result['missing_required_terms']}",
            f"Closed-model claims: {result['closed_model_claims']}",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit open-only paper scope")
    parser.add_argument("--paper-dir", default="paper")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = audit_open_only(args.paper_dir)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"out": args.out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()
