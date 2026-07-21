"""Static local run dashboard builder (V3 prompt 11).

Aggregates local run artifacts into a static HTML dashboard + JSON. Defensive by
design: every collector tolerates missing inputs (most artifacts do not exist
until real runs). No external services, no JS framework, no pixel copying.
"""

from __future__ import annotations

import argparse
import html
import json
from datetime import date
from pathlib import Path

from certvic.io import read_jsonl
from certvic.validation.claims import NON_EVIDENCE_STATUSES

PAGES = ["index", "runs", "quality", "review", "metrics", "claims", "artifacts"]
_NON_EVIDENCE = {s.upper() for s in NON_EVIDENCE_STATUSES} | {"MOCK_ONLY", "SIMULATED_ONLY"}


def _safe_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _find(root: Path, pattern: str) -> list[Path]:
    return sorted(root.rglob(pattern)) if root.exists() else []


# --- collectors ------------------------------------------------------------

def collect_runs(predictions_root: Path) -> dict:
    items = []
    for mf in _find(predictions_root, "*.run_manifest.json"):
        data = _safe_json(mf) or {}
        items.append({
            "run_id": data.get("run_id", mf.stem),
            "provider": data.get("provider"),
            "paid_services_used": data.get("paid_services_used", False),
            "zero_cost_ack": data.get("zero_cost_policy_ack"),
            "timestamp": data.get("timestamp_utc"),
        })
    return {"name": "runs", "status": "ok" if items else "missing", "items": items,
            "notes": [] if items else ["No prediction runs found yet."]}


def collect_metrics(results_root: Path) -> dict:
    items = []
    for sf in _find(results_root, "*summary*.json"):
        data = _safe_json(sf)
        if not isinstance(data, dict):
            continue
        overall = data.get("overall") or data
        if not isinstance(overall, dict):
            continue
        gap = overall.get("intervention_consistency_gap") or overall.get("gap") or overall.get("delta")
        if gap is None and "by_required_change" not in data:
            continue
        items.append({
            "file": str(sf.name),
            "gap": gap,
            "original_accuracy": overall.get("original_accuracy"),
            "consistency_rate": overall.get("consistency_rate"),
            "certified": data.get("certified") or (data.get("certification") or {}).get("certified"),
        })
    return {"name": "metrics", "status": "ok" if items else "missing", "items": items,
            "notes": [] if items else ["No metric summaries found yet."]}


def collect_quality(results_root: Path) -> dict:
    items = []
    for df in _find(results_root, "detectability_summary.json"):
        d = _safe_json(df) or {}
        cls = d.get("classifier", {})
        items.append({"file": df.name, "kind": "edit_detectability", "auc": cls.get("auc"), "artifact_risk": d.get("artifact_risk")})
    for qf in _find(results_root, "*edit_generation_summary*.json"):
        d = _safe_json(qf) or {}
        items.append({"file": qf.name, "kind": "edit_generation", "quality_passed": d.get("quality_passed"), "quality_failed": d.get("quality_failed")})
    return {"name": "quality", "status": "ok" if items else "missing", "items": items,
            "notes": [] if items else ["No edit-quality / detectability artifacts found yet."]}


def collect_review(annotations_dir: Path, results_root: Path) -> dict:
    items = []
    for rp in _find(annotations_dir, "review_progress.json") + _find(results_root, "review_progress.json"):
        d = _safe_json(rp) or {}
        items.append({"file": rp.name, "completion_fraction": d.get("completion_fraction"),
                      "n_disagreements": d.get("n_disagreements"), "all_complete": d.get("all_complete")})
    return {"name": "review", "status": "ok" if items else "missing", "items": items,
            "notes": [] if items else ["No human-review progress found yet."]}


def collect_claims(results_root: Path) -> dict:
    items = []
    notes = []
    cl = results_root / "claim_ledger.json"
    data = _safe_json(cl)
    claims = data if isinstance(data, list) else (data or {}).get("claims", []) if data else []
    for c in claims or []:
        items.append({"claim_id": c.get("claim_id"), "certification_status": c.get("certification_status"), "safe": c.get("safe")})
    if not items:
        notes.append("No claim ledger found; no certified claims (expected before real evidence).")
    return {"name": "claims", "status": "ok" if items else "missing", "items": items, "notes": notes}


def collect_artifacts(provenance_dir: Path) -> dict:
    items = []
    notes = []
    graph = _safe_json(provenance_dir / "artifact_graph" / "artifact_graph.json")
    if graph:
        items.append({"kind": "artifact_graph", "n_runs": graph.get("n_runs"), "n_artifacts": graph.get("n_artifacts"),
                      "missing": len(graph.get("missing_artifacts", [])), "mismatches": len(graph.get("hash_mismatches", []))})
    ledger = provenance_dir / "run_ledger.jsonl"
    if ledger.exists():
        try:
            items.append({"kind": "run_ledger", "n_entries": len(read_jsonl(str(ledger)))})
        except Exception:
            pass
    if not items:
        notes.append("No provenance artifacts found yet (run certvic.provenance.run_ledger).")
    return {"name": "artifacts", "status": "ok" if items else "missing", "items": items, "notes": notes}


def _scan_non_evidence(sections: dict) -> list[str]:
    flags = []
    for run in sections["runs"]["items"]:
        if run.get("paid_services_used"):
            flags.append(f"run {run.get('run_id')}: paid_services_used=true")
    blob = json.dumps(sections).upper()
    for status in sorted(_NON_EVIDENCE):
        if status in blob:
            flags.append(f"non-evidence status present: {status}")
    return flags


def _missing_gates(sections: dict) -> list[str]:
    gates = []
    if sections["runs"]["status"] == "missing":
        gates.append("no real prediction runs recorded")
    if sections["metrics"]["status"] == "missing":
        gates.append("no metric summaries")
    if not any(c.get("certification_status") == "certified" for c in sections["claims"]["items"]):
        gates.append("no certified claim (expected until real evidence exists)")
    if sections["review"]["status"] == "missing":
        gates.append("no human-review progress")
    if sections["artifacts"]["status"] == "missing":
        gates.append("no provenance ledger / artifact graph")
    return gates


def build_dashboard(
    results_root: str,
    out_dir: str,
    *,
    predictions_root: str | None = None,
    provenance_dir: str | None = None,
    annotations_dir: str | None = None,
) -> dict:
    results = Path(results_root)
    predictions = Path(predictions_root) if predictions_root else results.parent / "predictions"
    provenance = Path(provenance_dir) if provenance_dir else results.parent / "provenance"
    annotations = Path(annotations_dir) if annotations_dir else results.parent / "annotations"

    sections = {
        "runs": collect_runs(predictions),
        "metrics": collect_metrics(results),
        "quality": collect_quality(results),
        "review": collect_review(annotations, results),
        "claims": collect_claims(results),
        "artifacts": collect_artifacts(provenance),
    }
    non_evidence_flags = _scan_non_evidence(sections)
    missing_gates = _missing_gates(sections)

    data = {
        "dashboard": "certvic_local_run_dashboard",
        "generated": date.today().isoformat(),
        "results_root": str(results),
        "sections": sections,
        "non_evidence_flags": non_evidence_flags,
        "missing_gates": missing_gates,
        "any_certified_claim": any(c.get("certification_status") == "certified" for c in sections["claims"]["items"]),
        "evidence_claims_made": False,
        "external_services_used": False,
        "pixels_copied": False,
    }

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dashboard_data.json").write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    _write_pages(data, out)
    data["out_dir"] = str(out)
    return data


# --- rendering -------------------------------------------------------------

_CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;color:#1b1f24;background:#f6f8fa}
header{background:#24292f;color:#fff;padding:14px 20px}
nav a{color:#fff;margin-right:14px;text-decoration:none;font-size:14px}
nav a:hover{text-decoration:underline}
main{padding:20px;max-width:1000px;margin:0 auto}
.card{background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:16px;margin-bottom:16px}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;margin-right:6px}
.ok{background:#dafbe1;color:#0a6b29}.missing{background:#fff1e5;color:#9a4a00}.warn{background:#ffebe9;color:#a40e26}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #d0d7de;padding:6px 8px;text-align:left}
th{background:#f6f8fa}.note{color:#57606a;font-size:13px}
"""


def _nav() -> str:
    return "<nav>" + " ".join(f'<a href="{p}.html">{p}</a>' for p in PAGES) + "</nav>"


def _page(title: str, body: str) -> str:
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>"
        f"<style>{_CSS}</style></head><body>"
        f"<header><strong>CertVIC local run dashboard</strong> — {html.escape(title)}{_nav()}</header>"
        f"<main>{body}<p class='note'>Static local dashboard. No external services. Not evidence by itself.</p></main>"
        "</body></html>"
    )


def _table(items: list[dict]) -> str:
    if not items:
        return "<p class='note'>No data.</p>"
    cols = list(items[0].keys())
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    rows = ""
    for it in items:
        rows += "<tr>" + "".join(f"<td>{html.escape(str(it.get(c, '')))}</td>" for c in cols) + "</tr>"
    return f"<table><tr>{head}</tr>{rows}</table>"


def _section_card(section: dict) -> str:
    badge = {"ok": "ok", "missing": "missing", "warning": "warn"}.get(section["status"], "missing")
    notes = "".join(f"<p class='note'>{html.escape(n)}</p>" for n in section.get("notes", []))
    return (
        f"<div class='card'><h2>{html.escape(section['name'])} "
        f"<span class='badge {badge}'>{section['status']}</span></h2>"
        f"{_table(section['items'])}{notes}</div>"
    )


def _write_pages(data: dict, out: Path) -> None:
    # Index / overview.
    ne = data["non_evidence_flags"]
    mg = data["missing_gates"]
    overview = "<div class='card'><h2>Overview</h2>"
    overview += f"<p>Generated {html.escape(data['generated'])} from <code>{html.escape(data['results_root'])}</code>.</p>"
    overview += f"<p><span class='badge {'warn' if not data['any_certified_claim'] else 'ok'}'>certified claim: {data['any_certified_claim']}</span></p>"
    overview += "<h3>Missing gates</h3>" + ("<ul>" + "".join(f"<li>{html.escape(g)}</li>" for g in mg) + "</ul>" if mg else "<p class='note'>None flagged.</p>")
    overview += "<h3>Non-evidence flags</h3>" + ("<ul>" + "".join(f"<li class='note'>{html.escape(f)}</li>" for f in ne) + "</ul>" if ne else "<p class='note'>None.</p>")
    overview += "</div>"
    overview += "".join(_section_card(data["sections"][s]) for s in ["runs", "metrics", "quality", "review", "claims", "artifacts"])
    (out / "index.html").write_text(_page("Overview", overview), encoding="utf-8")

    for name in ["runs", "quality", "review", "metrics", "claims", "artifacts"]:
        (out / f"{name}.html").write_text(_page(name.title(), _section_card(data["sections"][name])), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC static local run dashboard")
    parser.add_argument("--results-root", default="data/results")
    parser.add_argument("--out-dir", default="data/dashboard")
    parser.add_argument("--predictions-root")
    parser.add_argument("--provenance-dir")
    parser.add_argument("--annotations-dir")
    args = parser.parse_args(argv)
    data = build_dashboard(
        args.results_root,
        args.out_dir,
        predictions_root=args.predictions_root,
        provenance_dir=args.provenance_dir,
        annotations_dir=args.annotations_dir,
    )
    print(json.dumps({
        "out_dir": data["out_dir"],
        "missing_gates": data["missing_gates"],
        "non_evidence_flags": data["non_evidence_flags"],
        "any_certified_claim": data["any_certified_claim"],
        "pages": [f"{p}.html" for p in PAGES],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
