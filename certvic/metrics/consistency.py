"""Compatibility CLI for smoke consistency scoring."""

from __future__ import annotations

import argparse
import json

from certvic.io import write_json
from certvic.metrics.score_predictions import score_predictions
from certvic.metrics.summary import summarize_pair_scores


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--preds", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    scores = score_predictions(args.tasks, args.preds)
    summary = summarize_pair_scores(scores)
    write_json(args.out, summary)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
