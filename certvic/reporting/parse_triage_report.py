"""Markdown report for model output / parse triage (V3 prompt 09)."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from certvic.io import ensure_parent

_FLAG_LABELS = {
    "answer_prior_flag": "answer prior / mode collapse",
    "degenerate_repeat_flag": "degenerate repeated output",
    "high_parse_failure_flag": "high parse-failure rate",
    "high_refusal_flag": "high refusal rate",
}


def render_report(result: dict) -> str:
    lines = [
        "# Model Output / Parse Triage",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Predictions: `{result['preds_path']}`",
        f"Total predictions: {result['n_predictions']}  |  parse failures: {result['n_parse_failures']}  |  suspicious: {result['n_suspicious']}",
        "",
        "Descriptive post-run diagnostic. No inference run; makes no evidence claim.",
        "",
        f"Flagged providers: {result['flagged_providers'] or 'none'}",
        "",
        "## Per-provider stats",
        "",
        "| Provider | n | parse_ok | refusal | mean chars | unique raw | top repeat | mode answer | mode frac | flags |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for s in result["provider_stats"]:
        flags = [_FLAG_LABELS[k] for k in _FLAG_LABELS if s.get(k)]
        lines.append(
            f"| `{s['provider']}` | {s['n']} | {s['parse_ok_rate']} | {s['refusal_rate']} | {s['mean_output_chars']} | "
            f"{s['n_unique_raw']} | {s['top_repeat_fraction']} | {s['mode_answer']} | {s['mode_answer_fraction']} | "
            f"{', '.join(flags) or 'ok'} |"
        )
    lines += [
        "",
        "## What the flags mean",
        "",
        "- **answer prior / mode collapse**: one answer dominates → the model may ignore the image.",
        "- **degenerate repeated output**: the same raw string repeats → broken decoding/prompt.",
        "- **high parse-failure rate**: outputs don't fit the answer format → fix prompt/parser before trusting scores.",
        "- **high refusal rate**: many refusals → re-prompt or exclude; refusals are not evidence of a gap.",
        "",
        "See `provider_output_stats.csv`, `answer_distribution.csv`, `suspicious_outputs.csv`,",
        "and `parse_failure_examples.jsonl` for the underlying rows.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Render the parse-triage markdown report from a summary JSON")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    ensure_parent(args.out)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"out": args.out}, sort_keys=True))


if __name__ == "__main__":
    main()
