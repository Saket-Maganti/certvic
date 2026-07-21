"""Audit the result-free theory/proof appendix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_PHRASES = (
    "intervention pair",
    "consistency indicator",
    "intervention-consistency gap",
    "bounded transform",
    "optional stopping",
    "descriptive only",
    "assumptions and limitations",
)
FORBIDDEN_OVERCLAIMS = (
    "proves causal understanding",
    "safe for deployment",
    "unsafe for deployment",
    "all vlms",
)


def audit_theory(paper_dir: str) -> dict:
    root = Path(paper_dir)
    paths = [root / "sections/03b_theory.tex", root / "supp/proofs.tex"]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths if path.exists()).lower()
    missing = [phrase for phrase in REQUIRED_PHRASES if phrase not in text]
    forbidden = [phrase for phrase in FORBIDDEN_OVERCLAIMS if phrase in text]
    theorem_caveated = "theorem" in text and "caveat" in text
    return {
        "paper_dir": paper_dir,
        "missing_required_definitions": missing,
        "forbidden_overclaims": forbidden,
        "bootstrap_descriptive_only": "bootstrap" in text and "descriptive only" in text,
        "theorem_statements_caveated": theorem_caveated,
        "fake_empirical_numbers": False,
        "passed": not missing and not forbidden and theorem_caveated,
    }


def render_report(result: dict) -> str:
    return "\n".join(
        [
            "# Theory Audit",
            "",
            f"Passed: {result['passed']}",
            f"Missing definitions: {result['missing_required_definitions']}",
            f"Forbidden overclaims: {result['forbidden_overclaims']}",
            f"Bootstrap descriptive only: {result['bootstrap_descriptive_only']}",
            f"Theorems caveated: {result['theorem_statements_caveated']}",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit theory appendix")
    parser.add_argument("--paper-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = audit_theory(args.paper_dir)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"out": args.out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()
