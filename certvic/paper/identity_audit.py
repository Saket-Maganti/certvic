"""Audit the V6 paper identity rewrite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_TERMS = (
    "visual decision update",
    "intervention-consistency gap",
    "item-validity certificate",
    "confound-controlled",
    "edit detectability",
    "anytime-valid certification",
)
FORBIDDEN_PHRASES = (
    "proves causal understanding",
    "all vlms",
    "frontier models fail",
    "safe for deployment",
    "state-of-the-art benchmark",
)


def _paper_text(paper_dir: str | Path) -> str:
    root = Path(paper_dir)
    paths = sorted(root.rglob("*.tex")) if root.exists() else []
    return "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in paths)


def audit_identity(paper_dir: str | Path = "paper") -> dict:
    text = _paper_text(paper_dir)
    lower = text.lower()
    missing_terms = [term for term in REQUIRED_TERMS if term not in lower]
    forbidden = [phrase for phrase in FORBIDDEN_PHRASES if phrase in lower]
    leading = lower[:1500]
    benchmark_lead = "benchmark" in leading and "not a benchmark" not in leading
    placeholders_intact = "[result required]" in lower
    checks = [
        {"name": "required_identity_terms_present", "passed": not missing_terms, "missing": missing_terms},
        {"name": "benchmark_not_lead_identity", "passed": not benchmark_lead},
        {"name": "forbidden_claims_absent", "passed": not forbidden, "findings": forbidden},
        {"name": "result_placeholders_intact", "passed": placeholders_intact},
    ]
    return {
        "audit": "v6_paper_identity",
        "paper_dir": str(paper_dir),
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def render_report(result: dict) -> str:
    lines = [
        "# V6 Paper Identity Audit",
        "",
        f"Passed: {result['passed']}",
        "",
        "| Check | Passed |",
        "| --- | --- |",
    ]
    for check in result["checks"]:
        lines.append(f"| {check['name']} | {check['passed']} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit V6 paper identity")
    parser.add_argument("--paper-dir", default="paper")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = audit_identity(args.paper_dir)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"out": args.out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()
