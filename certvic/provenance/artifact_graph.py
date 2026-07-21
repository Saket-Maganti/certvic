"""Artifact dependency graph from the run ledger (V3 prompt 01).

Reads the run ledger and builds a bipartite graph of runs and artifacts:
``input -> run -> output``. It re-hashes artifacts on disk to detect drift and
reports per-artifact status (present / missing / hash_mismatch) and per-run
status. Output is a JSON graph plus a human-readable markdown summary and a
Graphviz DOT file. No heavy imports, no downloads.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from certvic.io import ensure_parent
from certvic.provenance.run_ledger import hash_path, load_ledger

# Artifact-level statuses.
PRESENT = "present"
MISSING = "missing_artifact"
HASH_MISMATCH = "hash_mismatch"
UNHASHABLE = "unhashable_pointer"  # remote/planned pointer recorded as null hash


def _artifact_status(path: str, recorded_hash: str | None) -> str:
    current = hash_path(path)
    if recorded_hash is None:
        # Pointer that was never hashable (remote/planned/simulated) -- only
        # "missing" if it now resolves to nothing and isn't a remote pointer.
        return UNHASHABLE if current is None else PRESENT
    if current is None:
        return MISSING
    return PRESENT if current == recorded_hash else HASH_MISMATCH


def build_artifact_graph(ledger_path: str | Path) -> dict:
    entries = load_ledger(ledger_path)

    artifacts: dict[str, dict] = {}
    runs: list[dict] = []

    def touch(path: str, recorded_hash: str | None, role: str, run_id: str) -> None:
        node = artifacts.setdefault(
            path,
            {"path": path, "recorded_hash": recorded_hash, "produced_by": [], "consumed_by": []},
        )
        # Prefer a concrete recorded hash if any entry supplied one.
        if node["recorded_hash"] is None and recorded_hash is not None:
            node["recorded_hash"] = recorded_hash
        if role == "output" and run_id not in node["produced_by"]:
            node["produced_by"].append(run_id)
        if role == "input" and run_id not in node["consumed_by"]:
            node["consumed_by"].append(run_id)

    for e in entries:
        for path, h in e.input_hashes.items():
            touch(path, h, "input", e.run_id)
        for path, h in e.output_hashes.items():
            touch(path, h, "output", e.run_id)
        runs.append({
            "run_id": e.run_id,
            "stage": e.stage,
            "evidence_status": e.evidence_status,
            "paid_services_used": e.paid_services_used,
            "inputs": sorted(e.input_hashes),
            "outputs": sorted(e.output_hashes),
        })

    for node in artifacts.values():
        node["status"] = _artifact_status(node["path"], node["recorded_hash"])
        # An artifact consumed but never produced by any recorded run is dangling
        # provenance: we cannot trace where it came from.
        node["orphan_input"] = bool(node["consumed_by"]) and not node["produced_by"]

    missing = sorted(p for p, n in artifacts.items() if n["status"] == MISSING)
    mismatched = sorted(p for p, n in artifacts.items() if n["status"] == HASH_MISMATCH)
    orphans = sorted(p for p, n in artifacts.items() if n["orphan_input"])

    return {
        "graph": "certvic_artifact_graph",
        "ledger": str(ledger_path),
        "n_runs": len(runs),
        "n_artifacts": len(artifacts),
        "runs": runs,
        "artifacts": [artifacts[p] for p in sorted(artifacts)],
        "missing_artifacts": missing,
        "hash_mismatches": mismatched,
        "orphan_inputs": orphans,
        "healthy": not missing and not mismatched,
        "paid_services_used": any(r["paid_services_used"] for r in runs),
        "evidence_claims_made": False,
    }


def render_dot(graph: dict) -> str:
    lines = ["digraph certvic_provenance {", "  rankdir=LR;", '  node [fontname="Helvetica"];']
    for run in graph["runs"]:
        lines.append(f'  "run:{run["run_id"]}" [shape=box,style=filled,fillcolor=lightblue,label="{run["run_id"]}\\n({run["stage"]})"];')
    for node in graph["artifacts"]:
        color = {"present": "palegreen", "missing_artifact": "salmon", "hash_mismatch": "orange", "unhashable_pointer": "lightgrey"}.get(node["status"], "white")
        safe = node["path"].replace('"', "'")
        lines.append(f'  "art:{safe}" [shape=ellipse,style=filled,fillcolor={color},label="{safe}"];')
    for run in graph["runs"]:
        for inp in run["inputs"]:
            lines.append(f'  "art:{inp}" -> "run:{run["run_id"]}";')
        for out in run["outputs"]:
            lines.append(f'  "run:{run["run_id"]}" -> "art:{out}";')
    lines.append("}")
    return "\n".join(lines)


def render_report(graph: dict) -> str:
    status = "HEALTHY" if graph["healthy"] else "ISSUES FOUND"
    lines = [
        "# Artifact Provenance Graph",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Ledger: `{graph['ledger']}`",
        f"Status: **{status}** ({graph['n_runs']} runs, {graph['n_artifacts']} artifacts)",
        "",
        "This graph is descriptive provenance only. It makes no evidence claim.",
        "",
        "## Issues",
        "",
        f"- Missing artifacts: {len(graph['missing_artifacts'])}",
        f"- Hash mismatches: {len(graph['hash_mismatches'])}",
        f"- Orphan inputs (consumed but never produced by a recorded run): {len(graph['orphan_inputs'])}",
        "",
    ]
    for label, key in (("Missing artifacts", "missing_artifacts"), ("Hash mismatches", "hash_mismatches"), ("Orphan inputs", "orphan_inputs")):
        if graph[key]:
            lines.append(f"### {label}")
            lines.append("")
            lines += [f"- `{p}`" for p in graph[key]]
            lines.append("")
    lines += [
        "## Runs",
        "",
        "| Run | Stage | Evidence status | Inputs | Outputs |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in graph["runs"]:
        lines.append(f"| `{r['run_id']}` | {r['stage']} | {r['evidence_status']} | {len(r['inputs'])} | {len(r['outputs'])} |")
    lines.append("")
    return "\n".join(lines)


def write_graph(graph: dict, out_dir: str | Path) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "graph_json": str(out / "artifact_graph.json"),
        "report_md": str(out / "artifact_graph_report.md"),
        "dot": str(out / "artifact_graph.dot"),
    }
    Path(paths["graph_json"]).write_text(json.dumps(graph, indent=2, sort_keys=True), encoding="utf-8")
    Path(paths["report_md"]).write_text(render_report(graph), encoding="utf-8")
    Path(paths["dot"]).write_text(render_dot(graph), encoding="utf-8")
    return paths


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC artifact provenance graph")
    parser.add_argument("--ledger", default="data/provenance/run_ledger.jsonl")
    parser.add_argument("--out-dir", default="data/provenance/artifact_graph")
    args = parser.parse_args(argv)
    graph = build_artifact_graph(args.ledger)
    ensure_parent(Path(args.out_dir) / "x")
    paths = write_graph(graph, args.out_dir)
    print(json.dumps({
        "healthy": graph["healthy"],
        "n_runs": graph["n_runs"],
        "n_artifacts": graph["n_artifacts"],
        "missing_artifacts": len(graph["missing_artifacts"]),
        "hash_mismatches": len(graph["hash_mismatches"]),
        **paths,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
