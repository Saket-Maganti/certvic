"""Compare naive all-item scores against certificate-validity-gated scores."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from certvic.io import read_jsonl, write_json
from certvic.validity.load_bearing import score_gap


def _fmt(value) -> str:
    if value is None:
        return "RESULT REQUIRED"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _non_evidence(rows: list[dict]) -> bool:
    if not rows:
        return True
    joined = " ".join(str((row.get("metadata") or {}).get("evidence_status", "unknown")).lower() for row in rows)
    return any(token in joined for token in ("mock", "smoke", "simulated", "planned", "unknown"))


def compare(naive_path: str, valid_path: str, certificates_path: str) -> dict:
    naive = read_jsonl(naive_path)
    valid = read_jsonl(valid_path)
    valid_ids = {str(row.get("item_id")) for row in valid}
    rejected = [row for row in naive if str(row.get("item_id")) not in valid_ids]
    certs = {str(row.get("item_id")): row for row in read_jsonl(certificates_path)}
    rejection_reasons = Counter()
    for row in rejected:
        cert = certs.get(str(row.get("item_id")))
        if cert is None:
            rejection_reasons["missing_certificate"] += 1
        else:
            reasons = cert.get("blocking_reasons") or cert.get("warnings") or ["not_evidence_eligible_candidate"]
            for reason in reasons:
                rejection_reasons[str(reason)] += 1
    naive_gap = score_gap(naive)
    valid_gap = score_gap(valid)
    rejected_gap = score_gap(rejected)
    shift = None
    if naive_gap["intervention_consistency_gap"] is not None and valid_gap["intervention_consistency_gap"] is not None:
        shift = valid_gap["intervention_consistency_gap"] - naive_gap["intervention_consistency_gap"]
    return {
        "analysis": "naive_vs_validity_gated",
        "analysis_status": "NON_EVIDENCE_ANALYSIS_ONLY" if _non_evidence(naive) else "REAL_RUN_ANALYSIS_PENDING_CLAIM_GATES",
        "naive": naive_gap,
        "validity_gated": valid_gap,
        "rejected_items": rejected_gap,
        "gap_shift": shift,
        "rejection_distribution": dict(sorted(rejection_reasons.items())),
        "claim_status": "NO_CERTIFIED_CLAIMS_EMITTED",
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# Naive vs Validity-Gated Result Story",
        "",
        f"Status: {result['analysis_status']}",
        "",
        "| Slice | n | Gap |",
        "| --- | ---: | ---: |",
        f"| Naive all items | {result['naive']['n']} | {_fmt(result['naive']['intervention_consistency_gap'])} |",
        f"| Validity gated | {result['validity_gated']['n']} | {_fmt(result['validity_gated']['intervention_consistency_gap'])} |",
        f"| Rejected items | {result['rejected_items']['n']} | {_fmt(result['rejected_items']['intervention_consistency_gap'])} |",
        "",
        f"Gap shift: {_fmt(result['gap_shift'])}",
        "",
        "Paper-safe draft: CertVIC will report whether item-validity filtering changes the visual decision-update gap once real evidence exists: [RESULT REQUIRED].",
        "",
    ]
    if result["rejection_distribution"]:
        lines += ["## Rejection Distribution", ""]
        lines.extend(f"- {key}: {value}" for key, value in result["rejection_distribution"].items())
        lines.append("")
    return "\n".join(lines)


def write_report(naive: str, valid: str, certificates: str, out_dir: str) -> dict:
    result = compare(naive, valid, certificates)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "naive_vs_validity_gated_summary.json", result)
    with (out / "naive_vs_validity_gated_table.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["slice", "n", "intervention_consistency_gap"])
        writer.writeheader()
        for key, label in (("naive", "naive"), ("validity_gated", "validity_gated"), ("rejected_items", "rejected_items")):
            writer.writerow(
                {
                    "slice": label,
                    "n": result[key]["n"],
                    "intervention_consistency_gap": result[key]["intervention_consistency_gap"],
                }
            )
    (out / "naive_vs_validity_gated_report.md").write_text(render_markdown(result), encoding="utf-8")
    return {"out_dir": str(out), "passed": True, "analysis_status": result["analysis_status"]}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare naive and validity-gated scores")
    parser.add_argument("--naive", required=True)
    parser.add_argument("--valid", required=True)
    parser.add_argument("--certificates", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(write_report(args.naive, args.valid, args.certificates, args.out_dir), sort_keys=True))


if __name__ == "__main__":
    main()
