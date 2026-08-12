"""Reproduce deterministic C12 readiness artifacts from a clean committed worktree."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from local_operator.cvpr2027_common import canonical_json_bytes, write_json  # noqa: E402


DEFAULT_OUTPUT = REPOSITORY_ROOT / "reports/cvpr2027_c12"
COMPARE_FILES = (
    "design/C12_CONFIRMATORY_POWER_DECISION.json",
    "design/allocation_power_grid.csv",
    "design/allocation_pareto_frontier.csv",
    "design/MATCHING_DETECTABILITY_READINESS.json",
    "design/selection_balance_before.csv",
    "design/selection_balance_after.csv",
    "design/matching_trace.json",
    "gpu/00C2_READINESS.json",
    "gpu/PRIMARY_RUNBOOK_READINESS.json",
    "gpu/SECONDARY_RUNBOOK_READINESS.json",
    "gpu/OPTIONAL_MODEL_EXPANSION_READINESS.json",
    "analysis/ANALYSIS_GOLDEN_FIXTURES.json",
    "analysis/PRIMARY_ANALYSIS_READINESS.json",
    "evidence/CLAIM_REGISTRY_V2.json",
    "evidence/SCIENTIFIC_RED_TEAM_V2.json",
    "human/HUMAN_REVIEW_READINESS.json",
    "main/MAIN500_READINESS.json",
    "second_domain/SECOND_DOMAIN_READINESS.json",
)


def _semantic_value(path: Path) -> Any:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    return path.read_bytes()


def _semantic_hash(path: Path) -> str:
    value = _semantic_value(path)
    payload = value if isinstance(value, bytes) else canonical_json_bytes(value)
    return hashlib.sha256(payload).hexdigest()


def _run(command: list[str], *, cwd: Path, timeout: int = 3600) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def run(output_root: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    started = time.perf_counter()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    output_root.mkdir(parents=True, exist_ok=True)
    clean_root: Path | None = None
    command_results: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    cleanup_error = ""
    with tempfile.TemporaryDirectory(prefix="certvic-c12-clean-") as temporary:
        clean_root = Path(temporary) / "checkout"
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(clean_root), commit],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        try:
            commands = [
                [sys.executable, "local_operator/cvpr2027_c12_design.py"],
                [sys.executable, "local_operator/cvpr2027_c12_matching.py"],
                [sys.executable, "local_operator/cvpr2027_c12_readiness.py"],
            ]
            for command in commands:
                result = _run(command, cwd=clean_root)
                command_results.append(result)
                if result["returncode"] != 0:
                    break
            clean_output = clean_root / "reports/cvpr2027_c12"
            for relative in COMPARE_FILES:
                reference = output_root / relative
                reproduced = clean_output / relative
                if not reference.is_file() or not reproduced.is_file():
                    comparisons.append({
                        "path": relative,
                        "status": "MISSING",
                        "reference_present": reference.is_file(),
                        "reproduced_present": reproduced.is_file(),
                    })
                    continue
                reference_hash = _semantic_hash(reference)
                reproduced_hash = _semantic_hash(reproduced)
                comparisons.append({
                    "path": relative,
                    "status": "MATCH" if reference_hash == reproduced_hash else "MISMATCH",
                    "reference_semantic_sha256": reference_hash,
                    "reproduced_semantic_sha256": reproduced_hash,
                })
        finally:
            cleanup = subprocess.run(
                ["git", "worktree", "remove", "--force", str(clean_root)],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if cleanup.returncode:
                cleanup_error = cleanup.stderr[-2000:]
    mismatches = [row for row in comparisons if row["status"] != "MATCH"]
    commands_passed = len(command_results) == 3 and all(
        row["returncode"] == 0 for row in command_results
    )
    result = {
        "schema": "certvic.cvpr2027.c12.clean_reproduction.v1",
        "status": (
            "CLEAN_REPRODUCTION_COMPLETE"
            if commands_passed and not mismatches and not cleanup_error
            else "CLEAN_REPRODUCTION_FAILED"
        ),
        "committed_head": commit,
        "method": "detached_git_worktree",
        "commands": command_results,
        "comparisons": comparisons,
        "mismatch_count": len(mismatches),
        "cleanup_error": cleanup_error,
        "runtime_seconds": time.perf_counter() - started,
        "paper_evidence": False,
    }
    write_json(output_root / "reproducibility/C12_CLEAN_REPRODUCTION.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = run(args.output_root)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "CLEAN_REPRODUCTION_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
