"""Draft certification claim language only from eligible artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import read_json


def interpret_certification(cert_report: str, claim_ledger: str) -> dict:
    cert = read_json(cert_report) if Path(cert_report).exists() else {}
    ledger = read_json(claim_ledger) if Path(claim_ledger).exists() else {}
    reasons: list[str] = []
    cs = cert.get("confidence_sequence") or {}
    if not cs.get("available"):
        reasons.append("anytime_valid_cs_unavailable")
    if cert.get("bootstrap_only"):
        reasons.append("bootstrap_only_blocked")
    text = json.dumps({"cert": cert, "ledger": ledger}).upper()
    if "MOCK" in text or "SIMULATED" in text:
        reasons.append("mock_or_simulated_blocked")
    eligible = not reasons and bool(cert.get("claim_eligible"))
    draft = (
        "Certified claim draft: [RESULT REQUIRED after eligible CS and claim ledger pass]."
        if eligible
        else "Descriptive-only draft: certification is not available for the current artifacts."
    )
    return {
        "cert_report": cert_report,
        "claim_ledger": claim_ledger,
        "eligible": eligible,
        "rejection_reasons": reasons,
        "draft": draft,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Draft certification claim text")
    parser.add_argument("--cert-report", required=True)
    parser.add_argument("--claim-ledger", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = interpret_certification(args.cert_report, args.claim_ledger)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("# Certification Claim Draft\n\n" + result["draft"] + "\n", encoding="utf-8")
    print(json.dumps({"out": args.out, "eligible": result["eligible"], "reasons": result["rejection_reasons"]}, sort_keys=True))


if __name__ == "__main__":
    main()

