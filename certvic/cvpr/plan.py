"""Dry-run dependency planner for frozen CVPR studies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from certvic.cvpr.contracts import load_yaml, unresolved_freeze_fields
from certvic.cvpr.execution_gate import ExecutionAuthorizationError, verify_permission


def build_plan(study: str, *, project_root: str | Path = ".") -> dict[str, Any]:
    root = Path(project_root)
    config_path = root / "configs/studies" / f"{study}.yaml"
    if not config_path.is_file():
        raise ValueError(f"unknown study: {study}")
    config = load_yaml(config_path)
    execution = config.get("execution", {})
    task_path = root / str(execution.get("task_manifest", ""))
    smoke_gate = root / "reports/cvpr_final_integration/REAL_MODEL_SMOKE_GATE.csv"
    blockers: list[str] = []
    if not task_path.is_file():
        blockers.append(f"missing frozen task manifest: {task_path.relative_to(root)}")
    permission_path = root / str(execution.get("permission_artifact", ""))
    if not permission_path.is_file():
        blockers.append("signed execution permission is absent")
    else:
        try:
            verify_permission(permission_path, study=study)
        except ExecutionAuthorizationError as exc:
            blockers.append(f"signed execution permission invalid: {exc}")
    unresolved = unresolved_freeze_fields(config)
    if unresolved:
        blockers.append("unresolved frozen inputs: " + ",".join(unresolved[:20]))
    if not smoke_gate.is_file():
        blockers.append("real model smoke gate has not been returned and validated")
    review = execution.get("human_review_outputs", {})
    for name, value in sorted(review.items()):
        path = root / str(value)
        if not path.is_file():
            blockers.append(f"missing human-review artifact {name}: {value}")
    if not blockers:
        allowed = "RUN_FROZEN_STUDY_NOTEBOOKS"
    elif any("smoke" in blocker for blocker in blockers):
        allowed = "PROVISION_WHEELHOUSE_AND_SNAPSHOTS_THEN_RUN_00A_00B_00C2"
    elif any("task manifest" in blocker for blocker in blockers):
        allowed = "BUILD_AND_REVIEW_FROZEN_TASK_MANIFEST"
    else:
        allowed = "RESOLVE_FIRST_LISTED_BLOCKER_WITHOUT_CHANGING_FROZEN_OUTCOME_RULES"
    return {
        "schema": "certvic.cvpr.dry_run_plan.v1",
        "study": study,
        "status": "READY_TO_EXECUTE" if not blockers else "BLOCKED_PRECONDITIONS",
        "dependencies": [
            "verified source bytes and license rows",
            "exact offline environment or verified wheelhouse",
            "unified model/processor snapshots",
            "PASS real-model smoke for all required providers",
            "QA-enriched and independently reviewed frozen tasks",
            "hash-locked run contract and code bundle",
        ],
        "blockers": blockers,
        "expected_inputs": {
            "study_config": str(config_path.relative_to(root)),
            "task_manifest": str(task_path.relative_to(root)) if task_path != root else "UNRESOLVED",
            "smoke_gate": str(smoke_gate.relative_to(root)),
            "environment_lock": execution.get("environment_lock"),
            "execution_permission": execution.get("permission_artifact"),
        },
        "expected_outputs": [
            "immutable provider return ZIPs", "atomic canonical model matrix",
            "human-aware analysis", "evidence and gate ledger updates", "signed Main permission",
        ],
        "allowed_next_action": allowed,
        "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print a no-execution CertVIC study dependency plan")
    parser.add_argument("--study", required=True)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args(argv)
    result = build_plan(args.study, project_root=args.project_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
