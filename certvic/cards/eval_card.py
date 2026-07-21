"""Generate eval cards from local run directories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_eval_card(run_dir: str) -> dict:
    root = Path(run_dir)
    files = [p.name for p in root.iterdir() if p.is_file()] if root.exists() else []
    has_predictions = any(name.endswith(".jsonl") and "pred" in name for name in files)
    has_scores = any("score" in name for name in files)
    return {
        "run_dir": run_dir,
        "exists": root.exists(),
        "tasks": "declared in run manifest when available",
        "model_card": "required before claim drafting",
        "predictions_present": has_predictions,
        "scoring_present": has_scores,
        "parser": "CertVIC strict parser",
        "claim_status": "incomplete_eval_card_no_evidence" if not (has_predictions and has_scores) else "review_required",
        "provenance": "run ledger required for claims",
        "evidence_status": "EVAL_CARD_ONLY",
    }


def render_eval_card(card: dict) -> str:
    return "\n".join(
        [
            "# Eval Card",
            "",
            f"Run dir: `{card['run_dir']}`",
            f"Predictions present: {card['predictions_present']}",
            f"Scoring present: {card['scoring_present']}",
            f"Claim status: {card['claim_status']}",
            f"Provenance: {card['provenance']}",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write a CertVIC eval card")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    card = build_eval_card(args.run_dir)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_eval_card(card), encoding="utf-8")
    print(json.dumps({"out": args.out, "claim_status": card["claim_status"]}, sort_keys=True))


if __name__ == "__main__":
    main()

