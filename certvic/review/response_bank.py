"""Author-response bank for likely CVPR reviews."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

TOPICS = (
    "edit_realism",
    "not_causal",
    "small_scale",
    "open_only_models",
    "optional_stopping",
    "label_ambiguity",
    "artifact_release",
    "human_review",
    "no_frontier_models",
    "zero_cost_constraint",
    "statistical_conservatism",
)


def response_for(topic: str) -> str:
    return (
        f"## {topic.replace('_', ' ').title()}\n\n"
        "Response draft: We will answer using the locked analysis plan, item validity "
        "certificates, human review artifacts, and result lockfile. We will not add "
        "unsupported numerical claims; any missing empirical artifact remains marked "
        "`RESULT REQUIRED`.\n"
    )


def write_response_bank(out: str) -> dict:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = ["# CertVIC Author Response Bank", "", *[response_for(topic) for topic in TOPICS]]
    path.write_text("\n".join(body), encoding="utf-8")
    return {"out": out, "topics": list(TOPICS), "fake_results": False}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write author response bank")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(write_response_bank(args.out), sort_keys=True))


if __name__ == "__main__":
    main()

