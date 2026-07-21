"""Trace paper claims back to the runs that produced their evidence (V3 prompt 01).

For each claim in the claim ledger, find the run-ledger entries whose outputs
include the claim's evidence files, then re-hash those artifacts on disk and
check the producing run's evidence status. This is the link that lets a reviewer
(or us) confirm a paper number is real, traceable, and not backed by a mock /
simulated / planned artifact.

Trace statuses: trace_complete, missing_artifact, hash_mismatch,
ineligible_evidence, unknown.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from certvic.io import ensure_parent, read_json
from certvic.provenance.run_ledger import hash_path, load_ledger
from certvic.validation.claims import NON_EVIDENCE_STATUSES

TRACE_COMPLETE = "trace_complete"
MISSING_ARTIFACT = "missing_artifact"
HASH_MISMATCH = "hash_mismatch"
INELIGIBLE_EVIDENCE = "ineligible_evidence"
UNKNOWN = "unknown"

# Evidence is ineligible when produced by a run carrying one of these statuses.
_INELIGIBLE = {s.upper() for s in NON_EVIDENCE_STATUSES} | {"MOCK_ONLY", "UNKNOWN"}


def _index_outputs(entries) -> dict[str, list]:
    """Map output artifact path -> list of (run_id, recorded_hash, evidence_status)."""
    index: dict[str, list] = {}
    for e in entries:
        for path, h in e.output_hashes.items():
            index.setdefault(path, []).append((e.run_id, h, e.evidence_status))
    return index


def _trace_artifact(path: str, index: dict[str, list]) -> dict:
    producers = index.get(path, [])
    if not producers:
        return {"artifact": path, "status": UNKNOWN, "reason": "no run produced this artifact", "producing_runs": []}

    run_ids = [p[0] for p in producers]
    current = hash_path(path)
    if current is None:
        return {"artifact": path, "status": MISSING_ARTIFACT, "reason": "artifact not present on disk", "producing_runs": run_ids}

    # Any producer whose recorded hash matches the file on disk?
    matched = [p for p in producers if p[1] == current]
    if not matched:
        return {"artifact": path, "status": HASH_MISMATCH, "reason": "on-disk hash matches no recorded output hash", "producing_runs": run_ids}

    # If every matched producer is non-evidence, the artifact cannot back a claim.
    if all(str(p[2]).upper() in _INELIGIBLE for p in matched):
        return {
            "artifact": path,
            "status": INELIGIBLE_EVIDENCE,
            "reason": f"produced only by non-evidence run(s): {sorted({p[2] for p in matched})}",
            "producing_runs": [p[0] for p in matched],
        }

    return {"artifact": path, "status": TRACE_COMPLETE, "reason": "matched an evidence-eligible producing run", "producing_runs": [p[0] for p in matched]}


# Worst-first precedence: a claim is only as good as its weakest artifact.
_PRECEDENCE = [UNKNOWN, MISSING_ARTIFACT, HASH_MISMATCH, INELIGIBLE_EVIDENCE, TRACE_COMPLETE]


def trace_claims(claim_ledger_path: str | Path, run_ledger_path: str | Path) -> dict:
    entries = load_ledger(run_ledger_path)
    index = _index_outputs(entries)

    raw = read_json(claim_ledger_path)
    claims = raw if isinstance(raw, list) else raw.get("claims", [])

    traced: list[dict] = []
    for claim in claims:
        evidence_files = claim.get("evidence_files", []) or []
        artifact_traces = [_trace_artifact(str(f), index) for f in evidence_files]
        if not artifact_traces:
            claim_status = UNKNOWN
        else:
            claim_status = min((t["status"] for t in artifact_traces), key=_PRECEDENCE.index)
        certified = str(claim.get("certification_status", "")).lower() == "certified"
        traced.append({
            "claim_id": claim.get("claim_id", "<unknown>"),
            "certification_status": claim.get("certification_status", "not_certified"),
            "status": claim_status,
            "traceable": claim_status == TRACE_COMPLETE,
            # A certified claim that is not fully traceable is a hard integrity failure.
            "integrity_violation": certified and claim_status != TRACE_COMPLETE,
            "artifacts": artifact_traces,
        })

    violations = [t for t in traced if t["integrity_violation"]]
    return {
        "trace": "certvic_claim_trace",
        "claim_ledger": str(claim_ledger_path),
        "run_ledger": str(run_ledger_path),
        "n_claims": len(traced),
        "n_traceable": sum(1 for t in traced if t["traceable"]),
        "n_integrity_violations": len(violations),
        "ok": not violations,
        "claims": traced,
        "evidence_claims_made": False,
        "paid_services_used": any(e.paid_services_used for e in entries),
    }


def render_report(result: dict) -> str:
    status = "OK" if result["ok"] else "INTEGRITY VIOLATION"
    lines = [
        "# Claim Provenance Trace Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Claim ledger: `{result['claim_ledger']}`",
        f"Run ledger: `{result['run_ledger']}`",
        f"Status: **{status}** ({result['n_traceable']}/{result['n_claims']} claims fully traceable)",
        "",
        "A certified claim that is not `trace_complete` is an integrity violation: it",
        "must be downgraded until its evidence artifacts trace to an evidence-eligible run.",
        "",
        "| Claim | Certification | Trace status | Traceable |",
        "| --- | --- | --- | --- |",
    ]
    for t in result["claims"]:
        flag = "yes" if t["traceable"] else ("**VIOLATION**" if t["integrity_violation"] else "no")
        lines.append(f"| `{t['claim_id']}` | {t['certification_status']} | {t['status']} | {flag} |")
    lines.append("")
    for t in result["claims"]:
        if t["artifacts"]:
            lines.append(f"### `{t['claim_id']}`")
            lines.append("")
            for a in t["artifacts"]:
                lines.append(f"- `{a['artifact']}` -> {a['status']} ({a['reason']})")
            lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC claim->run provenance tracer")
    parser.add_argument("--claim-ledger", default="data/results/claim_ledger.json")
    parser.add_argument("--run-ledger", default="data/provenance/run_ledger.jsonl")
    parser.add_argument("--out", default="data/provenance/claim_trace_report.md")
    args = parser.parse_args(argv)
    result = trace_claims(args.claim_ledger, args.run_ledger)
    ensure_parent(args.out)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    import json

    print(json.dumps({
        "ok": result["ok"],
        "n_claims": result["n_claims"],
        "n_traceable": result["n_traceable"],
        "n_integrity_violations": result["n_integrity_violations"],
        "report": args.out,
    }, sort_keys=True))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
