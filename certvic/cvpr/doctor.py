"""One-command, fail-closed diagnosis of the CertVIC execution state."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any

from certvic.cvpr.ceiling_common import atomic_json, repository_root, sha256_file, utc_now
from certvic.cvpr.contracts import load_yaml, unresolved_freeze_fields


STATES = (
    "READY_FOR_00A",
    "READY_FOR_00B",
    "READY_FOR_00C2",
    "READY_FOR_CONFIRMATORY_BUILD",
    "READY_FOR_HUMAN_REVIEW",
    "READY_FOR_AUTHORIZATION",
    "READY_FOR_MODEL_RUNS",
    "READY_FOR_IMPORT",
    "READY_FOR_ANALYSIS",
    "BLOCKED",
)

CRITICAL_IMPORTS = (
    "certvic.cvpr.smoke_gate",
    "certvic.cvpr.smoke_artifacts",
    "certvic.cvpr.package_run",
    "certvic.cvpr.execution_gate",
    "certvic.cvpr.reconcile_provider_permissions",
    "certvic.cvpr.notebook_builder",
    "certvic.cvpr.content_discovery",
    "certvic.cvpr.notebook_00c2_proof",
    "certvic.cvpr.task_bundle",
    "certvic.cvpr.import_transaction",
    "certvic.cvpr.after_runs",
)

REQUIRED_LOCAL = (
    "pyproject.toml",
    "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md",
    "certvic",
    "tests",
    "configs",
    "notebooks/kaggle/cvpr",
    "scripts",
    "configs/studies/specificity_confirmatory_cvpr.yaml",
    "configs/models/certvic_cvpr_model_registry.yaml",
    "configs/runtime/kaggle_t4x2_environment.lock.json",
)


def _blocker(
    code: str,
    artifact: str,
    command: str,
    remediation: str,
    *,
    scope: str,
) -> dict[str, str]:
    return {
        "error_code": code,
        "missing_artifact": artifact,
        "next_command": command,
        "remediation": remediation,
        "scope": scope,
    }


def _json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _notebook_check(root: Path) -> dict[str, Any]:
    from certvic.cvpr.notebook_builder import NOTEBOOKS

    folder = root / "notebooks/kaggle/cvpr"
    notebooks = sorted(folder.glob("*.ipynb"))
    invalid: list[str] = []
    output_cells = 0
    for notebook in notebooks:
        try:
            payload = json.loads(notebook.read_text(encoding="utf-8"))
            cells = payload.get("cells", [])
            if not isinstance(cells, list):
                raise ValueError("cells is not a list")
            for cell in cells:
                if cell.get("cell_type") == "code" and (
                    cell.get("outputs") or cell.get("execution_count") is not None
                ):
                    output_cells += 1
        except (OSError, ValueError, json.JSONDecodeError):
            invalid.append(notebook.relative_to(root).as_posix())
    return {
        "count": len(notebooks),
        "expected_count": len(NOTEBOOKS),
        "invalid": invalid,
        "code_cells_with_outputs": output_cells,
        "passed": len(notebooks) == len(NOTEBOOKS) and not invalid and output_cells == 0,
    }


def _multi_account_portability_check(root: Path) -> dict[str, Any]:
    from certvic.cvpr.notebook_builder import NOTEBOOKS

    forbidden = (
        "locate_dataset(",
        "expected_filename=",
        "slug=",
        "certvic/certvic-",
        "/kaggle/input/certvic-",
    )
    violations: dict[str, list[str]] = {}
    for name in NOTEBOOKS:
        path = root / "notebooks/kaggle/cvpr" / name
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            text = "\n".join(
                "".join(cell.get("source", [])) for cell in payload.get("cells", [])
            )
        except (OSError, json.JSONDecodeError):
            violations[name] = ["unreadable_notebook"]
            continue
        found = [marker for marker in forbidden if marker in text]
        if "discover_authenticated_input(" not in text:
            found.append("content_discovery_missing")
        metadata = payload.get("metadata", {}).get("certvic", {})
        if any(metadata.get(field) is not False for field in (
            "owner_binding", "filename_binding", "mount_binding"
        )):
            found.append("portable_metadata_invalid")
        if found:
            violations[name] = found
    return {
        "passed": not violations,
        "owner_slug_binding": False,
        "filename_binding": False,
        "mount_binding": False,
        "content_authentication_required": True,
        "active_runbooks_checked": len(NOTEBOOKS),
        "violations": violations,
    }


def diagnose(root: str | Path | None = None, *, study: str = "specificity_confirmatory_cvpr") -> dict[str, Any]:
    base = repository_root(root)
    blockers: list[dict[str, str]] = []
    local_checks: dict[str, Any] = {}
    missing_local = [entry for entry in REQUIRED_LOCAL if not (base / entry).exists()]
    local_checks["required_tree"] = {"passed": not missing_local, "missing": missing_local}
    for entry in missing_local:
        blockers.append(_blocker(
            "DOCTOR_LOCAL_ARTIFACT_MISSING",
            entry,
            "python3 -m certvic.cvpr.doctor --json",
            "Restore the missing canonical file from the verified full-project archive.",
            scope="local",
        ))

    import_errors: dict[str, str] = {}
    for module in CRITICAL_IMPORTS:
        try:
            importlib.import_module(module)
        except Exception as error:  # pragma: no cover - defensive environment boundary
            import_errors[module] = f"{type(error).__name__}: {error}"
    local_checks["critical_imports"] = {"passed": not import_errors, "errors": import_errors}
    for module in import_errors:
        blockers.append(_blocker(
            "DOCTOR_CRITICAL_IMPORT_FAILED",
            module,
            f"python3 -c 'import {module}'",
            "Repair the import before any external execution.",
            scope="local",
        ))

    notebook = _notebook_check(base)
    local_checks["notebooks"] = notebook
    if not notebook["passed"]:
        blockers.append(_blocker(
            "DOCTOR_NOTEBOOK_SUITE_INVALID",
            "notebooks/kaggle/cvpr",
            "python3 -m certvic.cvpr.notebook_validation --root notebooks/kaggle/cvpr",
            f"Regenerate the {notebook['expected_count']}-notebook suite and clear every stored output.",
            scope="local",
        ))

    portability = _multi_account_portability_check(base)
    local_checks["multi_account_portability"] = portability
    if not portability["passed"]:
        blockers.append(_blocker(
            "DOCTOR_MULTI_ACCOUNT_PORTABILITY_INVALID",
            "notebooks/kaggle/cvpr",
            "python3 -m certvic.cvpr.notebook_validation --root notebooks/kaggle/cvpr",
            "Remove exact owner, slug, filename, and mount binding from every active runbook.",
            scope="local",
        ))

    # The active checkout is authoritative.  An obsolete distribution archive is
    # not an execution dependency and must never block a repaired live tree.
    local_checks["active_checkout_authority"] = {
        "passed": True,
        "status": "LIVE_CHECKOUT_AUTHORITATIVE",
        "obsolete_replacement_archive_required": False,
    }

    try:
        from certvic.cvpr.protocol_authority import validate_authority

        authority = validate_authority(base)
    except (OSError, ValueError) as error:
        authority = {"passed": False, "errors": [str(error)]}
    local_checks["protocol_authority"] = authority
    if not authority.get("passed"):
        blockers.append(_blocker(
            "DOCTOR_PROTOCOL_AUTHORITY_INVALID",
            "configs/studies/certvic_confirmatory_authority.json",
            "python3 -c 'from certvic.cvpr.protocol_authority import require_authority; require_authority()'",
            "Repair the sole prospective protocol authority and its locked hashes.",
            scope="local",
        ))

    study_path = base / f"configs/studies/{study}.yaml"
    study_config: dict[str, Any] = {}
    if study_path.is_file():
        try:
            study_config = load_yaml(study_path)
        except (OSError, ValueError) as error:
            blockers.append(_blocker(
                "DOCTOR_STUDY_CONFIG_INVALID",
                study_path.relative_to(base).as_posix(),
                f"python3 -m certvic.cvpr.doctor --study {study}",
                str(error),
                scope="local",
            ))
    elif study not in {"main_study_cvpr", "second_domain_cvpr"}:
        blockers.append(_blocker(
            "DOCTOR_STUDY_CONFIG_MISSING",
            study_path.relative_to(base).as_posix(),
            f"python3 -m certvic.cvpr.doctor --study {study}",
            "Restore the canonical study configuration.",
            scope="local",
        ))

    unresolved = unresolved_freeze_fields(study_config) if study_config else []
    local_checks["study"] = {
        "path": study_path.relative_to(base).as_posix(),
        "unresolved_freeze_fields": unresolved,
        "paper_evidence": study_config.get("paper_evidence"),
        "execution_allowed": study_config.get("execution_allowed"),
    }
    if study_config.get("paper_evidence") is not False:
        blockers.append(_blocker(
            "DOCTOR_EVIDENCE_BOUNDARY_INVALID",
            local_checks["study"]["path"],
            "python3 -m certvic.cvpr.doctor --json",
            "Pre-run study configs must keep paper_evidence=false.",
            scope="local",
        ))
    if study_config.get("execution_allowed") is not False:
        blockers.append(_blocker(
            "DOCTOR_STATIC_EXECUTION_FLAG_INVALID",
            local_checks["study"]["path"],
            "python3 -m certvic.cvpr.doctor --json",
            "Authority must come from expiring hash-bound permissions, not the static config.",
            scope="local",
        ))
    if unresolved:
        blockers.append(_blocker(
            "DOCTOR_EXTERNAL_FREEZE_INPUTS_REQUIRED",
            "|".join(unresolved),
            "run 00A and 00B after provisioning immutable snapshots",
            "Fill only from verified external bytes before issuing any permission.",
            scope="external",
        ))

    execution = study_config.get("execution", {}) if isinstance(study_config, dict) else {}
    paths = {
        "environment": base / "data/runtime/00A_environment.json",
        "smoke_gate": base / str(execution.get(
            "smoke_gate", "reports/cvpr_final_integration/REAL_MODEL_SMOKE_GATE.json"
        )),
        "task_bundle": base / str(execution.get(
            "task_bundle_manifest", f"data/studies/{study}/task_bundle/task_bundle_manifest.json"
        )),
        "review": base / str(execution.get("human_review_outputs", {}).get(
            "final_inclusion_manifest", f"data/studies/{study}/review/final_inclusion.json"
        )),
        "permission": base / str(execution.get(
            "permission_artifact", f"data/studies/{study}/execution_permission.json"
        )),
        "import": base / f"data/studies/{study}/canonical_import/study_import_audit.json",
        "analysis": base / f"data/studies/{study}/analysis/decision_trace.json",
    }
    providers = list(execution.get("expected_providers", (
        "qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"
    )))
    snapshots = [base / f"data/runtime/00B_{provider}_snapshot.json" for provider in providers]
    smoke_returns = [base / f"data/runtime/00C2_{provider}_real_model_smoke.zip" for provider in providers]
    provider_returns = [base / f"local_inputs/provider_returns/{study}/{provider}.zip" for provider in providers]

    local_blockers = [row for row in blockers if row["scope"] == "local"]
    if local_blockers:
        state = "BLOCKED"
    elif not paths["environment"].is_file():
        state = "READY_FOR_00A"
    elif not all(path.is_file() for path in snapshots):
        state = "READY_FOR_00B"
    elif not all(path.is_file() for path in smoke_returns) or not paths["smoke_gate"].is_file():
        state = "READY_FOR_00C2"
    elif not paths["task_bundle"].is_file():
        state = "READY_FOR_CONFIRMATORY_BUILD"
    elif not paths["review"].is_file():
        state = "READY_FOR_HUMAN_REVIEW"
    elif not paths["permission"].is_file():
        state = "READY_FOR_AUTHORIZATION"
    elif not any(path.is_file() for path in provider_returns):
        state = "READY_FOR_MODEL_RUNS"
    elif not all(path.is_file() for path in provider_returns) or not paths["import"].is_file():
        state = "READY_FOR_IMPORT"
    elif not paths["analysis"].is_file():
        state = "READY_FOR_ANALYSIS"
    else:
        state = "READY_FOR_ANALYSIS"

    inventory = {
        name: {
            "path": path.relative_to(base).as_posix(),
            "exists": path.is_file(),
            "sha256": sha256_file(path) if path.is_file() else None,
        }
        for name, path in paths.items()
    }
    return {
        "schema": "certvic.cvpr.doctor.v1",
        "generated_at_utc": utc_now(),
        "repository": ".",
        "study": study,
        "state": state,
        "local_ready": not local_blockers,
        "paper_evidence": False,
        "multi_account_portability": portability,
        "checks": local_checks,
        "inventory": inventory,
        "blockers": blockers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose the CertVIC pre-run state")
    parser.add_argument("--root")
    parser.add_argument("--study", default="specificity_confirmatory_cvpr")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    result = diagnose(args.root, study=args.study)
    if args.out:
        destination = Path(args.out)
        if not destination.is_absolute():
            destination = repository_root(args.root) / destination
        atomic_json(destination, result)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"CertVIC doctor: {result['state']}")
        print(f"Study: {result['study']}; local_ready={str(result['local_ready']).lower()}")
        for row in result["blockers"]:
            print(
                f"[{row['scope']}] {row['error_code']}: {row['missing_artifact']}\n"
                f"  next: {row['next_command']}\n  remediation: {row['remediation']}"
            )
    return 0 if result["local_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
