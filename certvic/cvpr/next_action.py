"""Read-only next-action guidance with a deliberately narrow local-safe executor."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from certvic.cvpr.ceiling_common import repository_root
from certvic.cvpr.doctor import diagnose


ACTIONS: dict[str, dict[str, Any]] = {
    "BLOCKED": {
        "kind": "local_safe",
        "command": [sys.executable, "-m", "compileall", "-q", "certvic", "scripts", "tests"],
        "description": "Repair the first local doctor blocker, then re-run the doctor.",
    },
    "READY_FOR_00A": {
        "kind": "external",
        "command": ["Kaggle", "00A_certvic_code_and_environment_smoke.ipynb"],
        "description": (
            "Publish the verified offline wheelhouse and run 00A in a fresh Kaggle CPU session "
            "with accelerator and Internet off."
        ),
    },
    "READY_FOR_00B": {
        "kind": "external",
        "command": ["Kaggle", "00B_certvic_model_snapshot_smoke.ipynb", "per provider"],
        "description": "Verify each immutable model/processor snapshot with 00B.",
    },
    "READY_FOR_00C2": {
        "kind": "external",
        "command": ["Kaggle", "00C2_certvic_real_model_two_item_smoke.ipynb", "three sessions"],
        "description": "Run each provider's authorized two-item real-model smoke separately.",
    },
    "READY_FOR_CONFIRMATORY_BUILD": {
        "kind": "external",
        "command": ["Kaggle", "01_specificity_confirmatory_generation_T4x2.ipynb"],
        "description": "Build outcome-unseen confirmatory candidates from licensed source assets.",
    },
    "READY_FOR_HUMAN_REVIEW": {
        "kind": "external",
        "command": [sys.executable, "-m", "certvic.cvpr.human_review", "--help"],
        "description": "Complete genuine two-rater blinded review and adjudication.",
    },
    "READY_FOR_AUTHORIZATION": {
        "kind": "local_safe",
        "command": [sys.executable, "-m", "certvic.cvpr.execution_gate", "--help"],
        "description": "Validate the exact frozen bytes and issue expiring scientific permissions.",
    },
    "READY_FOR_MODEL_RUNS": {
        "kind": "external",
        "command": ["Kaggle", "02/03/04 confirmatory provider notebooks"],
        "description": "Run three independent provider sessions without changing frozen inputs.",
    },
    "READY_FOR_IMPORT": {
        "kind": "local_safe",
        "command": [sys.executable, "-m", "certvic.cvpr.import_transaction", "--help"],
        "description": "Reconcile all provider proofs and perform the transactional import.",
    },
    "READY_FOR_ANALYSIS": {
        "kind": "local_safe",
        "command": [sys.executable, "-m", "certvic.cvpr.after_runs", "--help"],
        "description": "Run the preregistered analysis and guarded paper/release workflow.",
    },
}


def next_action(root: str | Path | None = None, *, study: str = "specificity_confirmatory_cvpr") -> dict[str, Any]:
    report = diagnose(root, study=study)
    action = ACTIONS[report["state"]]
    return {
        "schema": "certvic.cvpr.next_action.v1",
        "study": study,
        "state": report["state"],
        "description": action["description"],
        "kind": action["kind"],
        "command": action["command"],
        "blockers": report["blockers"],
        "executed": False,
    }


def execute_local_safe(result: dict[str, Any], root: str | Path | None = None) -> dict[str, Any]:
    if result["kind"] != "local_safe":
        return {
            **result,
            "execution_refused": True,
            "reason": "next action requires external compute or genuine human action",
        }
    base = repository_root(root)
    completed = subprocess.run(
        result["command"], cwd=base, check=False, capture_output=True, text=True, timeout=300
    )
    return {
        **result,
        "executed": True,
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show the exact next CertVIC action")
    parser.add_argument("--root")
    parser.add_argument("--study", default="specificity_confirmatory_cvpr")
    parser.add_argument("--execute-local-safe", action="store_true")
    args = parser.parse_args(argv)
    result = next_action(args.root, study=args.study)
    if args.execute_local_safe:
        result = execute_local_safe(result, args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("execution_refused"):
        return 3
    return int(result.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
