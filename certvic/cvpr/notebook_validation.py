"""Closure-specific static validation for the canonical CVPR notebooks."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

from certvic.cvpr.notebook_builder import NOTEBOOKS, expected_return_zip


def validate_suite(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    expected = set(NOTEBOOKS)
    observed = {path.name for path in root.glob("*.ipynb")}
    suite_errors: list[str] = []
    if observed != expected:
        suite_errors.append(f"notebook set mismatch: missing={sorted(expected-observed)} extra={sorted(observed-expected)}")
    manifest_path = root / "notebook_manifest.json"
    if not manifest_path.is_file():
        suite_errors.append("notebook manifest is missing")
        manifest = {"notebooks": {}}
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results = []
    for name in sorted(expected & observed):
        path = root / name
        payload = json.loads(path.read_text(encoding="utf-8"))
        text = "\n".join("".join(cell.get("source", [])) for cell in payload.get("cells", []))
        errors: list[str] = []
        ids = [cell.get("id") for cell in payload.get("cells", [])]
        if not ids or None in ids or len(ids) != len(set(ids)):
            errors.append("cell IDs are missing or duplicated")
        if any(cell.get("execution_count") is not None or cell.get("outputs")
               for cell in payload.get("cells", []) if cell.get("cell_type") == "code"):
            errors.append("notebook contains execution state")
        stage, provider = NOTEBOOKS[name]
        zero_edit = stage in {"code_smoke", "snapshot_smoke", "real_model_smoke"}
        required_tokens = (
            "HF_HUB_OFFLINE", "ENVIRONMENT_LOCK_HASH", "ATTACHED_INPUT_HASHES",
            "hardware_report", "ALLOW_SINGLE_GPU_FALLBACK",
        )
        if not zero_edit:
            required_tokens += (
                "--resume", "runtime_manifest.json", "hash_manifest.json",
                "local_import_command",
            )
        for token in required_tokens:
            if token not in text:
                errors.append(f"missing contract token: {token}")
        if zero_edit:
            if "REQUIRED_USER_FILL" in text:
                errors.append("zero-edit notebook contains an unresolved runtime placeholder")
            for index, cell in enumerate(payload.get("cells", [])):
                if cell.get("cell_type") != "code":
                    continue
                try:
                    ast.parse("".join(cell.get("source", [])), filename=f"{name}:cell-{index}")
                except SyntaxError as error:
                    errors.append(f"code cell is not Ruff-compatible Python: {error}")
            for token in (
                "materialize_dataset", "certvic/certvic-code", "certvic/certvic-configs",
                "certvic/certvic-execution-tools", "certvic/certvic-offline-wheelhouse",
                "certvic_offline_wheelhouse.zip", "wheelhouse_manifest.json",
                "KAGGLE_BOOTSTRAP_09_UNSAFE_EXTRACTION", "LOCAL_DESTINATION=",
                "python3 scripts/run_all_cpu_workflows.py --resume",
            ):
                if token not in text:
                    errors.append(f"zero-edit discovery contract missing: {token}")
            expected_gpus = 0 if stage in {"code_smoke", "snapshot_smoke"} else 2
            if f"EXPECTED_GPUS = {expected_gpus}" not in text:
                errors.append("zero-edit notebook has the wrong accelerator contract")
            if f"CANONICAL_RETURN_ZIP = {expected_return_zip(name, stage, provider)!r}" not in text:
                errors.append("zero-edit notebook has the wrong canonical return filename")
        if stage in {"generation", "evaluation"} and "subprocess.Popen" not in text:
            errors.append("GPU stage does not use concurrent process launch")
        if stage == "generation":
            if "bounded_rows = rows if MAX_ITEMS is None else rows[:MAX_ITEMS]" not in text:
                errors.append("generation has no study-global item bound")
            if text.index("bounded_rows =") > text.index("for shard, gpu in enumerate(GPU_IDS)"):
                errors.append("global bound is applied after sharding")
        if stage in {"evaluation", "snapshot_smoke", "real_model_smoke"}:
            if "verify_manifest" not in text or "SNAPSHOT_MANIFEST_HASH" not in text:
                errors.append("model stage does not verify snapshot bytes")
        if stage == "snapshot_smoke":
            slug = {
                "qwen2_5_vl_7b": "certvic/qwen2-5-vl-7b-snapshot",
                "internvl_8b": "certvic/internvl2-8b-snapshot",
                "llava_onevision_7b": "certvic/llava-onevision-7b-snapshot",
            }[provider]
            if slug not in text or "EXPECTED_GPUS = 0" not in text:
                errors.append("00B is not provider-specific CPU-only discovery")
        if stage == "mock_smoke":
            if "SYNTHETIC_SMOKE" not in text or 'command.append("--mock-runtime")' not in text:
                errors.append("00C1 is not unambiguously mock-only")
        if stage == "real_model_smoke":
            if (
                "REAL_MODEL_SMOKE" not in text
                or "USE_REAL_MODEL = True" not in text
                or expected_return_zip(name, stage, provider) not in text
            ):
                errors.append("00C2 is not fail-closed real-model smoke")
            for token in (
                "certvic/certvic-real-two-item-smoke",
                "certvic/certvic-pre-smoke-permissions",
                "KAGGLE_ZERO_EDIT_00C2_PERMISSION",
                "verify_matrix_authorization", "verify_provider_permission",
            ):
                if token not in text:
                    errors.append(f"00C2 permission discovery missing: {token}")
            permission_position = text.find("verify_provider_permission(")
            hardware_position = text.find("hardware = hardware_report()")
            worker_position = text.find('"-m", "certvic.cvpr.worker"')
            if min(permission_position, hardware_position, worker_position) < 0 or not (
                permission_position < hardware_position < worker_position
            ):
                errors.append("00C2 does not fail closed before hardware/model execution")
        expected_hash = manifest.get("notebooks", {}).get(name)
        if expected_hash != hashlib.sha256(path.read_bytes()).hexdigest():
            errors.append("notebook hash differs from suite manifest")
        results.append({"notebook": name, "stage": stage, "passed": not errors, "errors": errors})
    return {
        "schema": "certvic.cvpr.notebook_static_validation.v1",
        "passed": not suite_errors and all(row["passed"] for row in results),
        "suite_errors": suite_errors, "notebooks": results,
        "counts": {"expected": len(expected), "observed": len(observed),
                   "passed": sum(row["passed"] for row in results)},
        "execution_scope": "STATIC_ONLY_NOT_EXECUTED_ON_KAGGLE",
        "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the exact CVPR closure notebook suite")
    parser.add_argument("--root", default="notebooks/kaggle/cvpr")
    parser.add_argument("--out", default="reports/cvpr_execution_closure/notebook_static_validation.json")
    args = parser.parse_args(argv)
    result = validate_suite(args.root)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], **result["counts"]}, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
