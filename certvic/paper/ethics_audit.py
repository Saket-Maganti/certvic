"""Audit ethics and artifact appendix scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_TOPICS = (
    "zero-cost",
    "public datasets",
    "paid annotation",
    "pointer-only",
    "non-rehostable pixels",
    "human review",
    "deployment claims",
    "model limitations",
)


def audit_ethics(paper_dir: str, docs_path: str = "docs/ETHICS_AND_ARTIFACTS.md") -> dict:
    paths = [Path(paper_dir) / "supp/ethics_reproducibility.tex", Path(docs_path)]
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in paths if path.exists()).lower()
    missing = [topic for topic in REQUIRED_TOPICS if topic not in text]
    privacy_leak = "/" + "Users/" in text
    deployment_claim = "safe for deployment" in text or "unsafe for deployment" in text
    return {
        "missing_topics": missing,
        "privacy_leak": privacy_leak,
        "deployment_claim": deployment_claim,
        "artifact_caveats_included": "non-rehostable pixels" in text and "pointer-only" in text,
        "passed": not missing and not privacy_leak and not deployment_claim,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit ethics appendix")
    parser.add_argument("--paper-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = audit_ethics(args.paper_dir)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        "# Ethics Audit\n\n"
        f"Passed: {result['passed']}\n\n"
        f"Missing topics: {result['missing_topics']}\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": args.out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()

