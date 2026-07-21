"""Small helpers for comparing diagnostic prompt manifests."""

from __future__ import annotations

from collections import Counter

from certvic.io import read_jsonl


def summarize_prompt_manifest(path: str) -> dict:
    rows = read_jsonl(path)
    labels = Counter(str(row.get("diagnostic_prompt_label")) for row in rows)
    roles = Counter(str(row.get("analysis_role")) for row in rows)
    return {
        "path": path,
        "n_rows": len(rows),
        "prompt_labels": dict(sorted(labels.items())),
        "analysis_roles": dict(sorted(roles.items())),
        "primary_claim_default_rows": sum(1 for row in rows if bool(row.get("primary_claim_default"))),
    }
