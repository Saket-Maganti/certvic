"""Render edit-sweep reports."""

from __future__ import annotations

from certvic.io import read_jsonl


def render_sweep_report(sweep_plan: str) -> str:
    rows = read_jsonl(sweep_plan)
    lines = [
        "# Edit Sweep Report",
        "",
        "Planned parameter sweep only. No diffusion or simple edit generation has run.",
        "",
        "| Sweep | Engine | Edit | Runtime estimate |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['sweep_id']}` | {row['engine']} | `{row.get('edit_id')}` | "
            f"{row['estimated_runtime_seconds']}s |"
        )
    lines.append("")
    return "\n".join(lines)

