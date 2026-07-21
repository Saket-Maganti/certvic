"""Filter pair scores to item-certificate-eligible rows.

This is a claim-safety step, not a scoring shortcut. Missing or incomplete item
validity certificates reject rows by default and preserve the rejection reason.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import read_jsonl, write_jsonl


def _cert_map(certificates: list[dict]) -> dict[str, dict]:
    return {str(row.get("item_id")): row for row in certificates if row.get("item_id")}


def _reject_reasons(cert: dict | None) -> list[str]:
    if cert is None:
        return ["missing_certificate"]
    reasons: list[str] = []
    if not bool(cert.get("evidence_eligible_candidate")):
        reasons.append("not_evidence_eligible_candidate")
    reasons.extend(str(reason) for reason in cert.get("blocking_reasons") or [])
    reasons.extend(f"warning:{reason}" for reason in cert.get("warnings") or [])
    return sorted(set(reasons)) or ["certificate_not_eligible"]


def filter_scores(
    scores_path: str,
    certificates_path: str,
    out_path: str,
    rejected_out_path: str,
) -> dict:
    scores = read_jsonl(scores_path)
    certificates = _cert_map(read_jsonl(certificates_path))
    accepted: list[dict] = []
    rejected: list[dict] = []

    for row in scores:
        item_id = str(row.get("item_id"))
        cert = certificates.get(item_id)
        if cert and bool(cert.get("evidence_eligible_candidate")):
            kept = dict(row)
            metadata = dict(kept.get("metadata") or {})
            metadata["validity_filter"] = {
                "passed": True,
                "certificate_version": cert.get("certificate_version"),
                "filter": "evidence_eligible_candidate_only",
            }
            kept["metadata"] = metadata
            accepted.append(kept)
        else:
            dropped = dict(row)
            metadata = dict(dropped.get("metadata") or {})
            metadata["validity_filter"] = {
                "passed": False,
                "rejection_reasons": _reject_reasons(cert),
                "filter": "evidence_eligible_candidate_only",
            }
            dropped["metadata"] = metadata
            rejected.append(dropped)

    write_jsonl(out_path, accepted)
    write_jsonl(rejected_out_path, rejected)
    return {
        "scores": scores_path,
        "certificates": certificates_path,
        "out": out_path,
        "rejected_out": rejected_out_path,
        "n_in": len(scores),
        "n_valid": len(accepted),
        "n_rejected": len(rejected),
        "claim_status": "FILTERED_NON_CLAIM_ARTIFACT",
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Filter pair scores to item-certificate-eligible rows")
    parser.add_argument("--scores", required=True)
    parser.add_argument("--certificates", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--rejected-out", required=True)
    args = parser.parse_args(argv)
    result = filter_scores(args.scores, args.certificates, args.out, args.rejected_out)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
