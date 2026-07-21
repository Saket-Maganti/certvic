"""Result-artifact manifest builder (V3 prompt 12).

Scans a report directory for generated result artifacts (tables/figures/data),
hashes each, and records its evidence status and provider type so the paper
injector and number guard can refuse anything mock / simulated / unhashed. The
emitted manifest is compatible with ``certvic.validation.paper_numbers_guard``.

No inference, no downloads, no evidence claims.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from certvic.hashing import sha256_file
from certvic.io import ensure_parent, read_json
from certvic.validation.paper_numbers_guard import _eligible_entry

ARTIFACT_EXTENSIONS = {".tex": "table", ".csv": "data", ".png": "figure", ".pdf": "figure", ".json": "data"}


def _report_evidence(report_dir: Path, claim_ledger_path: str | None) -> tuple[str, str]:
    """Conservatively derive (evidence_status, provider_type) for the report.

    Defaults to non-evidence (UNKNOWN/unknown) unless a report summary or claim
    ledger positively establishes a real, open-local, certified run.
    """
    evidence_status = "UNKNOWN"
    provider_type = "unknown"
    for summary in sorted(report_dir.glob("*summary*.json")) + sorted(report_dir.glob("*.json")):
        data = read_json(summary) if summary.exists() else None
        if isinstance(data, dict):
            es = str(data.get("evidence_status", "")).upper()
            pt = str(data.get("provider_type", "")).lower()
            if es:
                evidence_status = es
            if pt:
                provider_type = pt
            if es or pt:
                break
    # The claim ledger can only *downgrade* to safe defaults; it never fabricates.
    if claim_ledger_path and Path(claim_ledger_path).exists():
        raw = read_json(claim_ledger_path)
        claims = raw if isinstance(raw, list) else raw.get("claims", [])
        certified = any(str(c.get("certification_status", "")).lower() == "certified" and c.get("safe") for c in claims)
        if not certified and evidence_status not in {"REAL_EVIDENCE", "EVIDENCE_ELIGIBLE", "REAL_PILOT", "REAL_MAIN"}:
            evidence_status = "UNKNOWN"
    return evidence_status, provider_type


def build_result_manifest(report_dir: str, claim_ledger_path: str | None, out_path: str) -> dict:
    rdir = Path(report_dir)
    evidence_status, provider_type = _report_evidence(rdir, claim_ledger_path)

    entries: list[dict] = []
    if rdir.exists():
        for f in sorted(rdir.rglob("*")):
            if f.is_file() and f.suffix.lower() in ARTIFACT_EXTENSIONS and not f.name.endswith("result_manifest.json"):
                entry = {
                    "artifact": str(f),
                    "basename": f.name,
                    "kind": ARTIFACT_EXTENSIONS[f.suffix.lower()],
                    "sha256": sha256_file(f),
                    "evidence_status": evidence_status,
                    "provider_type": provider_type,
                }
                entry["eligible"] = _eligible_entry(entry)
                entries.append(entry)

    n_eligible = sum(1 for e in entries if e["eligible"])
    manifest = {
        "manifest": "certvic_result_manifest",
        "generated": date.today().isoformat(),
        "report_dir": str(rdir),
        "claim_ledger": claim_ledger_path,
        "report_evidence_status": evidence_status,
        "report_provider_type": provider_type,
        "n_entries": len(entries),
        "n_eligible": n_eligible,
        "all_eligible": bool(entries) and n_eligible == len(entries),
        "any_eligible": n_eligible > 0,
        "entries": entries,
        "evidence_claims_made": False,
        "downloads_attempted": False,
    }
    ensure_parent(out_path)
    Path(out_path).write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC paper result-artifact manifest builder")
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--claim-ledger")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    manifest = build_result_manifest(args.report_dir, args.claim_ledger, args.out)
    print(json.dumps({
        "n_entries": manifest["n_entries"],
        "n_eligible": manifest["n_eligible"],
        "any_eligible": manifest["any_eligible"],
        "report_evidence_status": manifest["report_evidence_status"],
        "out": args.out,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
