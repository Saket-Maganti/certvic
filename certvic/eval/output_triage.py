"""Post-run triage of VLM raw outputs (V3 prompt 09).

After a tiny/main VLM run, this triages the raw outputs for the failure modes
that quietly wreck a consistency study: parse failures, degenerate repeated
outputs, answer priors / mode collapse, refusals, over-long rationales, and
invalid formats. Descriptive diagnostics only; no inference, no downloads, no
heavy imports.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from certvic.io import ensure_parent, read_jsonl

# Substrings that indicate a refusal / non-answer (lowercased match).
REFUSAL_MARKERS = (
    "i cannot", "i can't", "i can not", "i'm sorry", "i am sorry", "as an ai",
    "unable to", "i'm unable", "cannot determine", "can't determine",
    "i do not have", "i don't have", "no information", "not possible to",
    "i'm not able", "i am not able", "cannot answer", "can't answer",
)

DEFAULT_THRESHOLDS = {
    "long_output_chars": 200,       # a yes/no answer should be short
    "answer_prior_fraction": 0.9,   # one answer dominating -> prior/mode collapse
    # Near-total identical raw output -> broken decoding. Set high so a healthy
    # ~50/50 yes/no split on a binary task does not trip it.
    "degenerate_repeat_fraction": 0.9,
    "parse_ok_min": 0.8,            # below this, parse failure is high
    "refusal_max": 0.2,             # above this, refusals are high
}


def _is_refusal(raw: str) -> bool:
    low = raw.lower()
    return any(m in low for m in REFUSAL_MARKERS)


def _flag_reasons(pred: dict, thresholds: dict) -> list[str]:
    reasons: list[str] = []
    raw = str(pred.get("raw_output", ""))
    if not pred.get("parse_ok", True) or pred.get("parsed_answer") in (None, ""):
        reasons.append("parse_failure")
    if _is_refusal(raw):
        reasons.append("refusal")
    if len(raw) > thresholds["long_output_chars"]:
        reasons.append("long_rationale")
    return reasons


def triage_outputs(preds_path: str, tasks_path: str | None = None, *, thresholds: dict | None = None) -> dict:
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    preds = read_jsonl(preds_path)

    by_provider: dict[str, list[dict]] = defaultdict(list)
    for p in preds:
        by_provider[str(p.get("provider_name") or p.get("model_name") or "unknown")].append(p)

    parse_failures: list[dict] = []
    suspicious: list[dict] = []
    answer_rows: list[dict] = []
    provider_stats: list[dict] = []

    for provider, rows in sorted(by_provider.items()):
        n = len(rows)
        raw_counter = Counter(str(r.get("raw_output", "")) for r in rows)
        answers = [r.get("parsed_answer") for r in rows if r.get("parse_ok", True) and r.get("parsed_answer") not in (None, "")]
        answer_counter = Counter(str(a) for a in answers)
        n_parse_ok = sum(1 for r in rows if r.get("parse_ok", True) and r.get("parsed_answer") not in (None, ""))
        n_refusal = sum(1 for r in rows if _is_refusal(str(r.get("raw_output", ""))))
        lengths = [len(str(r.get("raw_output", ""))) for r in rows]
        latencies = [float(r["latency_s"]) for r in rows if r.get("latency_s") is not None]

        top_raw, top_raw_count = (raw_counter.most_common(1)[0] if raw_counter else ("", 0))
        mode_answer, mode_answer_count = (answer_counter.most_common(1)[0] if answer_counter else ("", 0))
        parse_ok_rate = n_parse_ok / n if n else 0.0
        refusal_rate = n_refusal / n if n else 0.0
        top_repeat_fraction = top_raw_count / n if n else 0.0
        mode_answer_fraction = (mode_answer_count / len(answers)) if answers else 0.0

        provider_stats.append({
            "provider": provider,
            "n": n,
            "parse_ok_rate": round(parse_ok_rate, 4),
            "refusal_rate": round(refusal_rate, 4),
            "mean_output_chars": round(sum(lengths) / n, 1) if n else 0.0,
            "mean_latency_s": round(sum(latencies) / len(latencies), 3) if latencies else None,
            "n_unique_raw": len(raw_counter),
            "top_repeat_fraction": round(top_repeat_fraction, 4),
            "mode_answer": mode_answer,
            "mode_answer_fraction": round(mode_answer_fraction, 4),
            "answer_prior_flag": mode_answer_fraction >= th["answer_prior_fraction"] and len(answers) > 0,
            "degenerate_repeat_flag": top_repeat_fraction >= th["degenerate_repeat_fraction"] and n > 1,
            "high_parse_failure_flag": parse_ok_rate < th["parse_ok_min"],
            "high_refusal_flag": refusal_rate > th["refusal_max"],
        })

        for ans, count in sorted(answer_counter.items()):
            answer_rows.append({"provider": provider, "parsed_answer": ans, "count": count, "fraction": round(count / len(answers), 4) if answers else 0.0})

        for r in rows:
            reasons = _flag_reasons(r, th)
            # Mark a row degenerate if it is the dominant repeated output.
            if n > 1 and str(r.get("raw_output", "")) == top_raw and top_repeat_fraction >= th["degenerate_repeat_fraction"]:
                reasons.append("degenerate_repeat")
            rec = {
                "run_id": r.get("run_id"),
                "item_id": r.get("item_id"),
                "provider": provider,
                "image_variant": r.get("image_variant"),
                "parse_ok": r.get("parse_ok", True),
                "parsed_answer": r.get("parsed_answer"),
                "raw_output": str(r.get("raw_output", ""))[:300],
            }
            if "parse_failure" in reasons:
                parse_failures.append(rec)
            if reasons:
                suspicious.append({**rec, "reasons": ";".join(sorted(set(reasons)))})

    flagged_providers = [s["provider"] for s in provider_stats if any(s[f] for f in ("answer_prior_flag", "degenerate_repeat_flag", "high_parse_failure_flag", "high_refusal_flag"))]
    return {
        "triage": "model_output_triage",
        "preds_path": preds_path,
        "tasks_path": tasks_path,
        "n_predictions": len(preds),
        "thresholds": th,
        "provider_stats": provider_stats,
        "answer_distribution": answer_rows,
        "parse_failures": parse_failures,
        "suspicious_outputs": suspicious,
        "n_parse_failures": len(parse_failures),
        "n_suspicious": len(suspicious),
        "flagged_providers": flagged_providers,
        "any_flags": bool(flagged_providers),
        "evidence_claims_made": False,
        "downloads_attempted": False,
        "vlm_inference_run": False,
    }


def _write_csv(path: str, rows: list[dict], columns: list[str]) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=columns)
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in columns})


def write_outputs(result: dict, out_dir: str) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary": str(out / "triage_summary.json"),
        "parse_failures": str(out / "parse_failure_examples.jsonl"),
        "answer_distribution": str(out / "answer_distribution.csv"),
        "provider_stats": str(out / "provider_output_stats.csv"),
        "suspicious": str(out / "suspicious_outputs.csv"),
        "report": str(out / "parse_triage_report.md"),
    }
    summary = {k: v for k, v in result.items() if k not in {"parse_failures", "suspicious_outputs"}}
    Path(paths["summary"]).write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    with Path(paths["parse_failures"]).open("w", encoding="utf-8") as h:
        for r in result["parse_failures"]:
            h.write(json.dumps(r, sort_keys=True) + "\n")
    _write_csv(paths["answer_distribution"], result["answer_distribution"], ["provider", "parsed_answer", "count", "fraction"])
    _write_csv(paths["provider_stats"], result["provider_stats"], [
        "provider", "n", "parse_ok_rate", "refusal_rate", "mean_output_chars", "mean_latency_s",
        "n_unique_raw", "top_repeat_fraction", "mode_answer", "mode_answer_fraction",
        "answer_prior_flag", "degenerate_repeat_flag", "high_parse_failure_flag", "high_refusal_flag",
    ])
    _write_csv(paths["suspicious"], result["suspicious_outputs"], [
        "run_id", "item_id", "provider", "image_variant", "parse_ok", "parsed_answer", "reasons", "raw_output",
    ])

    from certvic.reporting.parse_triage_report import render_report

    Path(paths["report"]).write_text(render_report(result), encoding="utf-8")
    return paths


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC model output / parse triage")
    parser.add_argument("--preds", required=True)
    parser.add_argument("--tasks")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    result = triage_outputs(args.preds, args.tasks)
    ensure_parent(Path(args.out_dir) / "x")
    paths = write_outputs(result, args.out_dir)
    print(json.dumps({
        "n_predictions": result["n_predictions"],
        "n_parse_failures": result["n_parse_failures"],
        "n_suspicious": result["n_suspicious"],
        "flagged_providers": result["flagged_providers"],
        **paths,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
