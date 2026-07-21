"""Audit the proof TODO and native confidence-sequence bridge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = (
    "bounded variable",
    "estimand",
    "optional stopping",
    "certvic/metrics/anytime_cs.py",
    "proof-required",
)


def audit_proof_bridge(paper_dir: str | Path = "paper") -> dict:
    root = Path(paper_dir)
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in sorted((root / "supp").glob("*.tex"))).lower()
    missing = [term for term in REQUIRED if term not in text]
    overclaim = "theorem complete" in text or "fully proven" in text
    return {"audit": "proof_bridge", "passed": not missing and not overclaim, "missing": missing, "overclaim": overclaim}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit proof bridge")
    parser.add_argument("--paper-dir", default="paper")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = audit_proof_bridge(args.paper_dir)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": args.out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()
