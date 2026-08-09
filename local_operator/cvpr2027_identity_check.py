"""Measure C11 final authenticated identities and compare them with the captured baseline."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from certvic.cvpr.content_discovery import authenticate_content_path  # noqa: E402
from local_operator.cvpr2027_common import (  # noqa: E402
    REPORT_ROOT,
    REPO,
    sha256_file,
    write_json,
)


ROLE_MAP = {"CODE": "CODE", "CONFIGS": "CONFIGS", "TOOLS": "EXECUTION_TOOLS"}


def _current_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def measure(baseline: dict[str, Any]) -> dict[str, Any]:
    common = {}
    for name, row in baseline["common_bundles"].items():
        path = REPO / row["path"]
        common[name] = {
            "path": row["path"],
            "content_identity_sha256": authenticate_content_path(path, ROLE_MAP[name]),
            "archive_sha256": sha256_file(path),
        }
    runtime = {}
    for name, row in baseline["runtime_returns"].items():
        runtime[name] = {
            "archive_path": row["archive_path"],
            "archive_sha256": sha256_file(REPO / row["archive_path"]),
            "member_path": row["member_path"],
            "member_sha256": sha256_file(REPO / row["member_path"]),
        }
    wheel = baseline["wheelhouse"]
    wheel_path = REPO / wheel["path"]
    return {
        "schema": "certvic.cvpr2027.c11.identity_snapshot.v1",
        "snapshot": "FINAL_AFTER_C11_EDITS",
        "git_head": _current_commit(),
        "common_bundles": common,
        "runtime_returns": runtime,
        "wheelhouse": {
            "path": wheel["path"],
            "content_identity_sha256": authenticate_content_path(
                wheel_path, "OFFLINE_LINUX_WHEELHOUSE"
            ),
            "archive_sha256": sha256_file(wheel_path),
        },
        "paper_evidence": False,
    }


def compare(baseline: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    comparisons = []
    for family in ["common_bundles", "runtime_returns"]:
        for name, before in baseline[family].items():
            after = final[family][name]
            for key in sorted(set(before) & set(after)):
                if key.endswith("sha256"):
                    comparisons.append({
                        "artifact": f"{family}.{name}.{key}",
                        "before": before[key], "after": after[key],
                        "preserved": before[key] == after[key],
                    })
    for key in ["content_identity_sha256", "archive_sha256"]:
        comparisons.append({
            "artifact": f"wheelhouse.{key}",
            "before": baseline["wheelhouse"][key],
            "after": final["wheelhouse"][key],
            "preserved": baseline["wheelhouse"][key] == final["wheelhouse"][key],
        })
    changed = [row for row in comparisons if not row["preserved"]]
    common_changed = any(row["artifact"].startswith("common_bundles") for row in changed)
    runtime_changed = any(row["artifact"].startswith("runtime_returns") for row in changed)
    wheel_changed = any(row["artifact"].startswith("wheelhouse") for row in changed)
    return {
        "schema": "certvic.cvpr2027.c11.identity_diff.v1",
        "status": "ALL_AUTHENTICATED_IDENTITIES_PRESERVED" if not changed else "IDENTITY_CHANGE_DETECTED",
        "comparisons": comparisons,
        "changed": changed,
        "common_identities_preserved": not common_changed and not wheel_changed,
        "runtime_returns_preserved": not runtime_changed,
        "00A_00B_rerun_required": common_changed or runtime_changed or wheel_changed,
        "stale_external_runs": [] if not changed else ["Re-evaluate exact dependencies from changed rows"],
        "paper_evidence": False,
    }


def run(output_root: Path = REPORT_ROOT) -> dict[str, Any]:
    baseline = json.loads((output_root / "C11_IDENTITY_BASELINE.json").read_text(encoding="utf-8"))
    final = measure(baseline)
    diff = compare(baseline, final)
    write_json(output_root / "C11_IDENTITY_FINAL.json", final)
    write_json(output_root / "C11_IDENTITY_DIFF.json", diff)
    return diff


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "ALL_AUTHENTICATED_IDENTITIES_PRESERVED" else 2)
