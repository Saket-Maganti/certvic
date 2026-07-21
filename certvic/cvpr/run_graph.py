"""Machine-readable execution DAG status, explanation, and DOT export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from certvic.cvpr.ceiling_common import repository_root
from certvic.cvpr.contracts import load_yaml


REQUIRED_NODE_FIELDS = {
    "id",
    "study",
    "prerequisites",
    "inputs",
    "outputs",
    "command",
    "hardware",
    "permission_class",
    "retry_recovery",
    "evidence_class",
    "downstream",
}


class RunGraphError(ValueError):
    """The execution graph is malformed or references an unknown node."""


def load_graph(path: str | Path) -> dict[str, Any]:
    value = load_yaml(path)
    nodes = value.get("nodes")
    if value.get("schema") != "certvic.cvpr.run_graph.v1" or not isinstance(nodes, list):
        raise RunGraphError("execution graph schema/nodes mismatch")
    ids: list[str] = []
    for node in nodes:
        if not isinstance(node, dict) or REQUIRED_NODE_FIELDS - set(node):
            missing = sorted(REQUIRED_NODE_FIELDS - set(node if isinstance(node, dict) else {}))
            raise RunGraphError(f"execution graph node is malformed; missing={missing}")
        ids.append(str(node["id"]))
    if len(ids) != len(set(ids)):
        raise RunGraphError("execution graph has duplicate node IDs")
    known = set(ids)
    for node in nodes:
        for field in ("prerequisites", "downstream"):
            unknown = set(map(str, node[field])) - known
            if unknown:
                raise RunGraphError(f"{node['id']}: unknown {field}: {sorted(unknown)}")
    return value


def graph_status(graph: dict[str, Any], root: str | Path) -> dict[str, Any]:
    base = Path(root).resolve()
    statuses: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    for node in graph["nodes"]:
        outputs = [base / str(path) for path in node["outputs"]]
        inputs = [base / str(path) for path in node["inputs"]]
        missing_inputs = [path.relative_to(base).as_posix() for path in inputs if not path.exists()]
        missing_outputs = [path.relative_to(base).as_posix() for path in outputs if not path.exists()]
        prerequisites_complete = all(
            statuses.get(str(prerequisite)) == "COMPLETE" for prerequisite in node["prerequisites"]
        )
        if outputs and not missing_outputs:
            status = "COMPLETE"
        elif prerequisites_complete and not missing_inputs:
            status = "READY"
        else:
            status = "BLOCKED"
        statuses[str(node["id"])] = status
        rows.append({
            "id": node["id"],
            "study": node["study"],
            "status": status,
            "permission_class": node["permission_class"],
            "missing_inputs": missing_inputs,
            "missing_outputs": missing_outputs,
            "prerequisites_complete": prerequisites_complete,
        })
    return {
        "schema": "certvic.cvpr.run_graph_status.v1",
        "paper_evidence": False,
        "nodes": rows,
        "next": next((row["id"] for row in rows if row["status"] == "READY"), None),
    }


def explain(graph: dict[str, Any], node_id: str, root: str | Path) -> dict[str, Any]:
    node = next((item for item in graph["nodes"] if item["id"] == node_id), None)
    if node is None:
        raise RunGraphError(f"unknown execution graph node: {node_id}")
    status = next(row for row in graph_status(graph, root)["nodes"] if row["id"] == node_id)
    return {**node, "observed": status}


def export_dot(graph: dict[str, Any]) -> str:
    lines = ["digraph certvic {", "  rankdir=LR;"]
    for node in graph["nodes"]:
        label = f"{node['id']}\\n{node['study']}"
        lines.append(f'  "{node["id"]}" [label="{label}"];')
    for node in graph["nodes"]:
        for target in node["downstream"]:
            lines.append(f'  "{node["id"]}" -> "{target}";')
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect the CertVIC execution DAG")
    parser.add_argument("--root")
    parser.add_argument("--graph", default="configs/execution/certvic_run_graph.yaml")
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("status")
    explanation = subparsers.add_parser("explain")
    explanation.add_argument("node")
    subparsers.add_parser("next")
    dot = subparsers.add_parser("export-dot")
    dot.add_argument("--out")
    args = parser.parse_args(argv)
    base = repository_root(args.root)
    graph_path = Path(args.graph)
    if not graph_path.is_absolute():
        graph_path = base / graph_path
    graph = load_graph(graph_path)
    if args.action == "status":
        payload: Any = graph_status(graph, base)
    elif args.action == "explain":
        payload = explain(graph, args.node, base)
    elif args.action == "next":
        payload = {"next": graph_status(graph, base)["next"], "paper_evidence": False}
    else:
        rendered = export_dot(graph)
        if args.out:
            destination = Path(args.out)
            if not destination.is_absolute():
                destination = base / destination
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(rendered, encoding="utf-8")
            payload = {"written": destination.relative_to(base).as_posix()}
        else:
            print(rendered, end="")
            return 0
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

