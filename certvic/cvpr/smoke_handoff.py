"""One-command reconciliation of returned 00A/00B/00C2 smoke artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from certvic.cvpr.environment_lock import environment_lock_hash
from certvic.cvpr.smoke_artifacts import environment_names, smoke_name, snapshot_names
from certvic.cvpr.smoke_gate import evaluate
from certvic.cvpr.contracts import load_yaml


class SmokeHandoffError(ValueError):
    """Canonical smoke inputs cannot be discovered or reconciled without editing."""


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _discover(root: Path, providers: list[str]) -> dict[str, Path]:
    names = [*environment_names()]
    for provider in providers:
        names.extend(snapshot_names(provider))
        names.append(smoke_name(provider))
    discovered: dict[str, Path] = {}
    for name in names:
        matches = list(root.rglob(name))
        if len(matches) != 1:
            raise SmokeHandoffError(
                f"canonical artifact discovery requires exactly one {name}; found {len(matches)}"
            )
        discovered[name] = matches[0]
    return discovered


def _stage_flat(discovered: dict[str, Path], root: Path) -> None:
    """The gate consumes names directly; reject ambiguous nesting without renaming user files."""
    for name, path in discovered.items():
        if path.parent.resolve() != root.resolve():
            raise SmokeHandoffError(
                f"canonical returned artifacts must share one directory; {name} is under {path.parent}"
            )


def run_handoff(
    artifacts_dir: str | Path,
    *,
    smoke_contract: str | Path,
    model_registry: str | Path,
    environment_lock: str | Path,
    out_dir: str | Path,
) -> dict[str, Any]:
    root = Path(artifacts_dir)
    if not root.is_dir():
        raise SmokeHandoffError("returned artifact directory does not exist")
    registry = load_yaml(model_registry)
    providers = list(map(str, registry.get("primary_models", [])))
    if len(providers) != 3 or len(set(providers)) != 3:
        raise SmokeHandoffError("model registry must declare exactly three unique primary providers")
    discovered = _discover(root, providers)
    _stage_flat(discovered, root)
    contract = json.loads(Path(smoke_contract).read_text(encoding="utf-8"))
    expected_environment = contract.get(
        "environment_manifest_hash", contract.get("environment_hash")
    )
    observed_environment = environment_lock_hash(environment_lock)
    if expected_environment != observed_environment:
        raise SmokeHandoffError("trusted smoke contract and current environment lock differ")
    result = evaluate(root, providers, contract=contract)
    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "REAL_MODEL_SMOKE_GATE.json"
    csv_path = destination / "REAL_MODEL_SMOKE_GATE.csv"
    report_path = destination / "SMOKE_HANDOFF_REPORT.md"
    _write_json(json_path, result)
    fields = [
        "model",
        "status",
        "reason",
        "runtime_class",
        "synthetic_fixture",
        "model_id",
        "model_revision",
        "snapshot_hash",
        "snapshot_root_hash",
        "environment_hash",
        "code_hash",
        "processor_model_contract",
        "parser_version",
        "prompt_hash",
        "task_bundle_hash",
        "smoke_fixture_hash",
        "peak_vram_gib",
        "smoke_zip_sha256",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["models"])
    passed = result["status"] == "REAL_MODEL_SMOKE_PASSED"
    next_command = (
        "python3 -m certvic.cvpr.reconcile_provider_permissions issue-matrix "
        "--study <STUDY> --task-bundle-manifest <TASK_BUNDLE_MANIFEST> "
        "--bundle-root <TASK_BUNDLE_ROOT> --final-task-manifest <FINAL_TASKS.jsonl> "
        "--final-review <FINAL_REVIEW.json> --detectability-gate <DETECTABILITY_GATE.json> "
        "--environment-lock <ENVIRONMENT_LOCK.json> --model-registry <MODEL_REGISTRY.yaml> "
        "--providers qwen2_5_vl_7b internvl_8b llava_onevision_7b "
        "--code-bundle <CODE_BUNDLE.zip> "
        "--out <STUDY_ROOT>/matrix_authorization.json"
        if passed
        else None
    )
    rows = "\n".join(
        f"| {row['model']} | {row['status']} | {row['reason']} |" for row in result["models"]
    )
    next_section = (
        f"```bash\n{next_command}\n```"
        if next_command
        else "Authorization remains blocked until all three canonical real-model smoke rows pass."
    )
    report = f"""# CertVIC real-model smoke handoff

Status: `{result['status']}`. Paper evidence: `false`.

| Provider | Status | Reason |
| --- | --- | --- |
{rows}

Artifact contract: `certvic.cvpr.smoke_artifact.v1`.
Trusted contract SHA-256: `{hashlib.sha256(Path(smoke_contract).read_bytes()).hexdigest()}`.
Environment lock identity: `{observed_environment}`.

## Next command

{next_section}
"""
    report_path.write_text(report, encoding="utf-8")
    return {
        **result,
        "outputs": [str(json_path), str(csv_path), str(report_path)],
        "next_authorization_command": next_command,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile canonical CertVIC smoke returns")
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--smoke-contract", required=True)
    parser.add_argument("--model-registry", required=True)
    parser.add_argument("--environment-lock", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    try:
        result = run_handoff(
            args.artifacts_dir,
            smoke_contract=args.smoke_contract,
            model_registry=args.model_registry,
            environment_lock=args.environment_lock,
            out_dir=args.out_dir,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "SMOKE_HANDOFF_BLOCKED", "reason": str(exc)}))
        return 2
    print(
        json.dumps(
            {
                "status": result["status"],
                "outputs": result["outputs"],
                "next_authorization_command": result["next_authorization_command"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "REAL_MODEL_SMOKE_PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
