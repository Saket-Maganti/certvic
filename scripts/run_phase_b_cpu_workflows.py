#!/usr/bin/env python3
"""Execute the complete CPU-only Phase B validation matrix; never launch a real GPU run."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _sanitize_output(value: str) -> str:
    """Keep generated validation logs free of workstation-private absolute paths."""
    sanitized = value.replace(str(ROOT), ".").replace(str(Path.home()), "<HOME>")
    return re.sub(r"/(?:Users|home|root|mnt|media)/[^\s\"']+", "<PRIVATE_PATH>", sanitized)


def _run(command: list[str], *, cwd: Path, timeout: int = 1800) -> dict[str, Any]:
    started = time.monotonic()
    environment = {
        **os.environ,
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "DIFFUSERS_OFFLINE": "1",
        "PIP_NO_INDEX": "1",
        "CUDA_VISIBLE_DEVICES": "",
    }
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=environment,
    )
    return {
        "command": [_sanitize_output(value) for value in command],
        "exit_code": completed.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "stdout_tail": _sanitize_output(completed.stdout[-8000:]),
        "stderr_tail": _sanitize_output(completed.stderr[-8000:]),
    }


def execute(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    # Clear any stale failed-run log before pytest invokes the repository privacy guard.
    (out / "validation_results.json").write_text(json.dumps({
        "schema": "certvic.kaggle.phase_b_cpu_validation.v1",
        "status": "RUNNING",
        "paper_evidence": False,
        "real_gpu_runs_launched": False,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    python = sys.executable
    commands = [
        [python, "-m", "pytest", "-q"],
        [python, "-m", "ruff", "check", "--no-cache", "certvic", "scripts", "tests"],
        [python, "-m", "compileall", "-q", "certvic", "scripts", "tests"],
        [python, "-m", "certvic.cvpr.notebook_validation", "--out", str(out / "notebook_static_validation.json")],
        [python, "-m", "certvic.cvpr.notebook_runner", "--kaggle-runbook-suite", "--out-dir", str(out / "notebook_proof"), "--timeout", "180"],
        [python, "-m", "certvic.cvpr.build_all_kaggle_inputs", "--local-only"],
        [python, "-m", "certvic.cvpr.build_all_kaggle_inputs", "--status"],
        [python, "-m", "certvic.cvpr.doctor", "--json", "--out", str(out / "doctor.json")],
        [python, "-m", "certvic.cvpr.next_action"],
        [python, "-m", "certvic.cvpr.run_graph", "status"],
        [python, str(ROOT / "scripts/refresh_kaggle_release_lineage.py"), "--include-release"],
        [python, str(ROOT / "scripts/run_all_cpu_workflows.py"), "--internal", "register_bundles"],
        [python, "-m", "certvic.cvpr.artifact_registry", "verify"],
        [python, "-m", "certvic.cvpr.kaggle_claim_guard", "--out", str(out / "claim_guard.json")],
        [python, "-m", "certvic.security.release_privacy_audit", "--root", ".", "--release-dir", "kaggle_uploads/00_code", "--out", str(out / "privacy_audit.md"), "--json-out", str(out / "privacy_audit.json")],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
        [python, str(ROOT / "scripts/build_maximum_ceiling_release.py"), "--deterministic-rebuild", "--clean-extraction"],
    ]
    results = []
    for command in commands:
        cwd = ROOT / "paper_cvpr" if command[0] == "pdflatex" else ROOT
        result = _run(command, cwd=cwd)
        results.append(result)
        if result["exit_code"] != 0:
            break
    report = {
        "schema": "certvic.kaggle.phase_b_cpu_validation.v1",
        "status": "PASS" if len(results) == len(commands) and all(row["exit_code"] == 0 for row in results) else "FAIL",
        "commands_planned": len(commands),
        "commands_executed": len(results),
        "results": results,
        "real_gpu_runs_launched": False,
        "synthetic_fixture": True,
        "paper_evidence": False,
    }
    (out / "validation_results.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = execute(args.out)
    print(json.dumps({
        "status": result["status"],
        "commands_executed": result["commands_executed"],
        "commands_planned": result["commands_planned"],
        "validation_results": str(Path(args.out) / "validation_results.json"),
    }, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
