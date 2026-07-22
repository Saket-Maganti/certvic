"""Build and operate the unified, deterministic CertVIC ``kagglefiles`` pack."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from certvic.cvpr.kaggle_bundle import verify_bundle
from certvic.cvpr.notebook_builder import (
    NOTEBOOKS,
    build_suite,
    content_early_code_bootstrap_source,
    expected_return_zip,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACK_ROOT = ROOT / "kagglefiles"
ACTIVE_PROFILE = "kaggle_cp312_2026_07"
LEGACY_PROFILES = ["kaggle_cp310_legacy"]
ALLOWED_READINESS = {
    "READY_NOW",
    "WAITING_FOR_PRIOR_RETURN",
    "WAITING_FOR_EXTERNAL_BYTES",
    "WAITING_FOR_HUMAN_REVIEW",
    "CONDITIONAL_NOT_AUTHORIZED",
}
PROVIDERS = {
    "qwen2_5_vl_7b": {
        "short": "qwen",
        "repository": "Qwen/Qwen2.5-VL-7B-Instruct",
        "commit": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
        "output": "qwen2_5_vl_7b_snapshot.zip",
        "input_stage": "02_QWEN_SNAPSHOT",
    },
    "internvl_8b": {
        "short": "internvl",
        "repository": "OpenGVLab/InternVL2-8B",
        "commit": "6fb9ad6924f69424e57fab2ab061d707688f0296",
        "output": "internvl2_8b_snapshot.zip",
        "input_stage": "03_INTERNVL_SNAPSHOT",
    },
    "llava_onevision_7b": {
        "short": "llava",
        "repository": "llava-hf/llava-onevision-qwen2-7b-ov-hf",
        "commit": "0d50680527681998e456c7b78950205bedd8a068",
        "output": "llava_onevision_7b_snapshot.zip",
        "input_stage": "04_LLAVA_SNAPSHOT",
    },
}

RUNBOOK_FOLDERS = (
    "00_PROVISIONING",
    "01_ENVIRONMENT_SMOKE",
    "02_MODEL_SNAPSHOTS",
    "03_SNAPSHOT_SMOKE",
    "04_REAL_MODEL_SMOKE",
    "05_CONFIRMATORY_GENERATION",
    "06_CONFIRMATORY_MODELS",
    "07_MAIN_CONDITIONAL",
    "08_SECOND_DOMAIN_CONDITIONAL",
)
INPUT_FOLDERS = (
    "00_COMMON",
    "01_CP312_WHEELHOUSE",
    "02_QWEN_SNAPSHOT",
    "03_INTERNVL_SNAPSHOT",
    "04_LLAVA_SNAPSHOT",
    "05_REAL_TWO_ITEM_SMOKE",
    "06_PRE_SMOKE_PERMISSIONS",
    "07_CONFIRMATORY_GENERATION",
    "08_CONFIRMATORY_QWEN",
    "09_CONFIRMATORY_INTERNVL",
    "10_CONFIRMATORY_LLAVA",
    "11_MAIN_GENERATION",
    "12_MAIN_QWEN",
    "13_MAIN_INTERNVL",
    "14_MAIN_LLAVA",
    "15_SECOND_DOMAIN_GENERATION",
    "16_SECOND_DOMAIN_QWEN",
    "17_SECOND_DOMAIN_INTERNVL",
    "18_SECOND_DOMAIN_LLAVA",
)


class KagglefilesPackError(ValueError):
    """The operator pack or an imported return violates a fail-closed contract."""


def _sha(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _write(path: Path, payload: str | bytes, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    if not path.is_file() or path.read_bytes() != data:
        path.write_bytes(data)
    if executable:
        path.chmod(0o755)


def _cell(kind: str, source: str) -> dict[str, Any]:
    cell = {
        "cell_type": kind,
        "id": hashlib.sha256(f"{kind}\0{source}".encode()).hexdigest()[:12],
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }
    if kind == "code":
        cell.update(execution_count=None, outputs=[])
    return cell


def _notebook(cells: Iterable[tuple[str, str]], *, stage: str, provider: str | None) -> bytes:
    value = {
        "cells": [_cell(kind, source) for kind, source in cells],
        "metadata": {
            "certvic": {
                "accelerator": "OFF",
                "internet": "ON",
                "paper_evidence": False,
                "provider": provider,
                "runtime_profile": ACTIVE_PROFILE,
                "stage": stage,
                "zero_edit": True,
                "content_discovery": "AUTHENTICATED_ANY_ACCOUNT_NAME_PATH_EXTENSION_NESTING",
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return _json_bytes(value)


def cp312_provisioning_notebook() -> bytes:
    """Return the zero-edit live-runtime CP312 wheelhouse provisioner."""
    probe = r'''import json, os, pathlib, platform, shutil, sys
from packaging.tags import sys_tags

probe = {
    "executable": sys.executable,
    "implementation": platform.python_implementation(),
    "python": platform.python_version(),
    "architecture": platform.machine(),
    "system": platform.system(),
    "libc": platform.libc_ver(),
    "supported_tags": [str(tag) for tag in sys_tags()],
}
print(json.dumps({"status": "IMMEDIATE_CP312_PROVISIONING_PROBE", **probe}, indent=2))
if (probe["implementation"] != "CPython" or not probe["python"].startswith("3.12.")
        or probe["architecture"].lower() != "x86_64" or probe["system"] != "Linux"):
    raise RuntimeError(
        "CERTVIC_RUNTIME_01_PYTHON_PROFILE_NOT_SUPPORTED: "
        "builder requires Kaggle CPython 3.12 Linux x86_64"
    )
if (not probe["libc"][0].lower().startswith("glibc")
        or tuple(map(int, probe["libc"][1].split("."))) < (2, 17)):
    raise RuntimeError(
        "CERTVIC_RUNTIME_01_PYTHON_PROFILE_NOT_SUPPORTED: glibc >= 2.17 required"
    )
'''
    provision = r'''from certvic.cvpr.content_discovery import discover_authenticated_input
from certvic.cvpr.notebook_bootstrap import discover_unique_file
from certvic.cvpr.wheelhouse_builder import WheelhouseBuilderError, deterministic_provision

materialized = pathlib.Path("/kaggle/working/certvic_provisioning_inputs")
code = discover_authenticated_input(
    "CODE", roots=INPUT_ROOTS, expected_identity=CODE_BUNDLE_HASH,
    materialization_root=materialized,
)
configs = discover_authenticated_input(
    "CONFIGS", roots=INPUT_ROOTS, materialization_root=materialized,
)
tools = discover_authenticated_input(
    "EXECUTION_TOOLS", roots=INPUT_ROOTS, materialization_root=materialized,
)
print({
    "authenticated_content_identities": {
        row["role"]: row["content_identity_sha256"] for row in (code, configs, tools)
    }
})
environment_lock = discover_unique_file(
    configs["materialized_root"], "kaggle_t4x2_environment.lock.json"
)
requirements_root = discover_unique_file(
    configs["materialized_root"], "kaggle_base.lock"
).parent
wheel_root = pathlib.Path("/kaggle/working/certvic_cp312_wheels")
output = pathlib.Path("/kaggle/working/certvic_offline_wheelhouse_cp312.zip")
failure_report_path = pathlib.Path(
    "/kaggle/working/certvic_cp312_wheelhouse_failure_report.json"
)

def failure_names(report):
    names = set()
    for field in ("incompatible_wheels", "missing_packages", "duplicate_conflicts"):
        for value in report.get(field, []):
            if isinstance(value, dict):
                names.add(str(value.get("package") or value.get("filename") or value))
            else:
                names.add(str(value))
    return sorted(names)

try:
    result = deterministic_provision(
        wheel_root=wheel_root,
        output=output,
        requirements_root=requirements_root,
        profile_id="kaggle_cp312_2026_07",
        environment_lock=environment_lock,
        failure_report_path=failure_report_path,
    )
except WheelhouseBuilderError as error:
    report = dict(error.report)
    if failure_report_path.is_file():
        report = json.loads(failure_report_path.read_text(encoding="utf-8"))
    print(json.dumps(report, indent=2, sort_keys=True))
    raise RuntimeError(
        f"{report.get('status', error.status)}: packages={failure_names(report)}; "
        f"failure_report={failure_report_path}"
    ) from error
if not result.get("passed", False):
    report = dict(result)
    print(json.dumps(report, indent=2, sort_keys=True))
    raise RuntimeError(
        f"{report.get('status')}: packages={failure_names(report)}; "
        f"failure_report={failure_report_path}"
    )
print(json.dumps(result, indent=2, sort_keys=True))
'''
    validate = r'''from certvic.cvpr.environment_lock import (
    prepare_offline_environment,
    select_locked_runtime,
)
from certvic.cvpr.kaggle_bundle import verify_bundle
from certvic.cvpr.notebook_bootstrap import extract_verified_bundle
from certvic.cvpr.wheelhouse_builder import (
    persist_failure_report,
    provisioning_failure_report,
)

selected_profile = select_locked_runtime(environment_lock)
try:
    if not output.is_file() or result.get("deterministic_rebuild", {}).get(
        "byte_identical"
    ) is not True:
        raise RuntimeError("passed deterministic bundle was not produced")
    verification = verify_bundle(output)
    if not verification["passed"]:
        raise RuntimeError(f"authenticated bundle verification failed: {verification['errors']}")
    validation_root = pathlib.Path("/kaggle/working/certvic_cp312_offline_validation")
    extract_verified_bundle(
        output,
        validation_root,
        expected_type="OFFLINE_LINUX_WHEELHOUSE",
    )
    manifest = json.loads(
        (validation_root / "wheelhouse_manifest.json").read_text(encoding="utf-8")
    )
    offline_validation = prepare_offline_environment(
        environment_lock,
        wheelhouse=validation_root / "wheels",
        wheelhouse_manifest=validation_root / "wheelhouse_manifest.json",
        allow_preinstalled=False,
        require_exact=True,
        require_cuda=False,
        selected_profile=selected_profile,
        venv_root=pathlib.Path(
            "/kaggle/working/certvic_runtime/kaggle_cp312_builder_validation"
        ),
    )
except Exception as error:
    report = provisioning_failure_report(
        "CERTVIC_RUNTIME_09_OFFLINE_VALIDATION_FAILED",
        selected=selected_profile,
        required_packages=result.get("resolver_result", {}).get("required_packages", {}),
        provisioning=result.get("resolver_result", {}),
        downloaded_wheels=list(locals().get("manifest", {}).get("files", {}).values()),
        remediation=(
            "Inspect the named offline install/import failure. Do not upload the bundle until "
            "a clean no-system-site-packages CPython 3.12 venv passes every import."
        ),
    )
    report["offline_validation_error"] = f"{type(error).__name__}: {error}"
    persist_failure_report(failure_report_path, report)
    output.unlink(missing_ok=True)
    print(json.dumps(report, indent=2, sort_keys=True))
    raise RuntimeError(
        f"{report['status']}: offline_validation; failure_report={failure_report_path}"
    ) from error
print({
    "resolver_result": result.get("resolver_result"),
    "supported_tags": selected_profile["observed_runtime"]["supported_tags"],
    "wheel_hashes": {
        name: row["sha256"]
        for name, row in offline_validation["wheelhouse_validation"]["files"].items()
    },
    "offline_install_import_validation": offline_validation,
})
print({
    "status": "CP312_WHEELHOUSE_BUILDER_READY",
    "runtime_profile": "kaggle_cp312_2026_07",
    "bundle_sha256": verification["sha256"],
    "size": output.stat().st_size,
    "wheel_count": result.get("wheel_count"),
    "deterministic_rebuild": result["deterministic_rebuild"],
    "offline_validation_status": offline_validation["status"],
    "network_used_for_provisioning": True,
    "paper_evidence": False,
})
print(
    "NEXT: download certvic_offline_wheelhouse_cp312.zip, import it unchanged with "
    "kagglefiles/import_kaggle_return.py, then run 00A with Accelerator OFF and Internet OFF."
)
'''
    return _notebook(
        (
            (
                "markdown",
                "# Build the CertVIC CPython 3.12 offline wheelhouse\n\n"
                "Settings: **Accelerator OFF**, **Internet ON**. Attach the refreshed "
                "authenticated CertVIC CODE, CONFIGS, and EXECUTION_TOOLS inputs. Run All "
                "without editing. A failed or partial build emits only "
                "`certvic_cp312_wheelhouse_failure_report.json`; only a fully verified run "
                "produces `certvic_offline_wheelhouse_cp312.zip`.\n",
            ),
            ("code", probe),
            ("code", content_early_code_bootstrap_source()),
            ("code", provision),
            ("code", validate),
        ),
        stage="wheelhouse_provisioning",
        provider=None,
    )


def snapshot_provisioning_notebook(provider: str) -> bytes:
    """Return a provider-bound, zero-edit, path-independent snapshot builder."""
    if provider not in PROVIDERS:
        raise KagglefilesPackError(f"unsupported snapshot provider: {provider}")
    spec = PROVIDERS[provider]
    title = provider.replace("_", " ").title()
    runtime_probe = r'''import json, platform, sys

print(json.dumps({
    "status": "IMMEDIATE_SNAPSHOT_PROVISIONING_PROBE",
    "executable": sys.executable,
    "implementation": platform.python_implementation(),
    "python": platform.python_version(),
    "architecture": platform.machine(),
    "system": platform.system(),
    "libc": platform.libc_ver(),
}, indent=2))
if platform.python_implementation() != "CPython" or not platform.python_version().startswith("3.12."):
    raise RuntimeError("CERTVIC_RUNTIME_01_PYTHON_PROFILE_NOT_SUPPORTED: CPython 3.12 required")
if platform.system() != "Linux" or platform.machine().lower() != "x86_64":
    raise RuntimeError("CERTVIC_RUNTIME_01_PYTHON_PROFILE_NOT_SUPPORTED: Linux x86_64 required")
'''
    bootstrap = runtime_probe + "\n" + content_early_code_bootstrap_source()
    build = f'''import subprocess
from pathlib import Path

PROVIDER = {provider!r}
MODEL_REPOSITORY = {spec["repository"]!r}
MODEL_COMMIT = {spec["commit"]!r}
PROCESSOR_COMMIT = MODEL_COMMIT
CANONICAL_OUTPUT = {spec["output"]!r}

subprocess.run([
    sys.executable, "-m", "pip", "install", "--quiet", "huggingface_hub==0.26.2"
], check=True)
from huggingface_hub import snapshot_download
from certvic.cvpr.kaggle_bundle import verify_bundle
from certvic.cvpr.snapshot_bundle_builder import build_snapshot_bundle

snapshot_root = Path("/kaggle/working/model_snapshot") / PROVIDER
snapshot_download(
    repo_id=MODEL_REPOSITORY,
    revision=MODEL_COMMIT,
    local_dir=snapshot_root,
)
symlinks = [str(path) for path in snapshot_root.rglob("*") if path.is_symlink()]
if symlinks:
    raise RuntimeError(f"downloaded snapshot contains symlinks: {{symlinks[:5]}}")
output = Path("/kaggle/working") / CANONICAL_OUTPUT
rebuild = output.with_name(output.stem + ".deterministic_rebuild.zip")
first = build_snapshot_bundle(
    PROVIDER,
    snapshot_root,
    model_commit=MODEL_COMMIT,
    processor_commit=PROCESSOR_COMMIT,
    output=output,
)
second = build_snapshot_bundle(
    PROVIDER,
    snapshot_root,
    model_commit=MODEL_COMMIT,
    processor_commit=PROCESSOR_COMMIT,
    output=rebuild,
)
if output.read_bytes() != rebuild.read_bytes():
    raise RuntimeError("snapshot deterministic rebuild is not byte-identical")
rebuild.unlink()
verification = verify_bundle(output)
if not verification["passed"]:
    raise RuntimeError(f"snapshot bundle verification failed: {{verification['errors']}}")
print(json.dumps({{
    "status": "IMMUTABLE_SNAPSHOT_BUILT_DETERMINISTIC",
    "provider": PROVIDER,
    "model_repository": MODEL_REPOSITORY,
    "model_commit": MODEL_COMMIT,
    "processor_commit": PROCESSOR_COMMIT,
    "canonical_output": str(output),
    "size": output.stat().st_size,
    "sha256": first["sha256"],
    "deterministic_rebuild": True,
    "paper_evidence": False,
}}, indent=2, sort_keys=True))
print("NEXT: download " + CANONICAL_OUTPUT + ", then run the matching provider-specific 00B notebook with Accelerator OFF and Internet OFF.")
'''
    return _notebook(
        (
            (
                "markdown",
                f"# Build the immutable {title} snapshot\n\n"
                "Settings: **Accelerator OFF**, **Internet ON**. Attach the authenticated "
                "CertVIC CODE bundle under any account, title, filename, extension, mount, or "
                f"nesting. Run All without editing. Canonical output: `{spec['output']}`.\n",
            ),
            ("code", bootstrap),
            ("code", build),
        ),
        stage="snapshot_provisioning",
        provider=provider,
    )


def _runbook_specs() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "name": "00_build_certvic_cp312_wheelhouse.ipynb",
            "folder": "00_PROVISIONING",
            "stage": "BUILD_CP312_WHEELHOUSE",
            "provider": None,
            "study": "all",
            "input_folder": "01_CP312_WHEELHOUSE",
            "required_roles": "CODE;CONFIGS;EXECUTION_TOOLS",
            "readiness": "READY_NOW",
            "accelerator": "OFF",
            "internet": "ON",
            "runtime": "PLANNING_ESTIMATE: 45-120 min typical; up to 3 h",
            "output": "certvic_offline_wheelhouse_cp312.zip",
            "destination": "kagglefiles/inputs/01_CP312_WHEELHOUSE/certvic_offline_wheelhouse_cp312.zip",
            "parallel": "SNAPSHOT_PROVISIONING",
            "blocking": "",
            "source": "certvic/cvpr/kagglefiles_pack.py#cp312_provisioning_notebook",
        },
    ]
    for order, (provider, spec) in enumerate(PROVIDERS.items(), start=1):
        rows.append({
            "name": f"{order:02d}_build_{provider}_snapshot.ipynb",
            "folder": "00_PROVISIONING",
            "stage": "BUILD_MODEL_SNAPSHOT",
            "provider": provider,
            "study": "all",
            "input_folder": spec["input_stage"],
            "required_roles": "CODE",
            "readiness": "READY_NOW",
            "accelerator": "OFF",
            "internet": "ON",
            "runtime": "PLANNING_ESTIMATE: 2-6 h/provider",
            "output": spec["output"],
            "destination": f"kagglefiles/inputs/{spec['input_stage']}/{spec['output']}",
            "parallel": "SNAPSHOT_PROVISIONING",
            "blocking": "",
            "source": "certvic/cvpr/kagglefiles_pack.py#snapshot_provisioning_notebook",
        })
    folder_map = {
        "00A_": "01_ENVIRONMENT_SMOKE",
        "00B_": "03_SNAPSHOT_SMOKE",
        "00C2_": "04_REAL_MODEL_SMOKE",
        "01_": "05_CONFIRMATORY_GENERATION",
        "02_": "06_CONFIRMATORY_MODELS",
        "03_": "06_CONFIRMATORY_MODELS",
        "04_": "06_CONFIRMATORY_MODELS",
        "10_": "07_MAIN_CONDITIONAL",
        "11_": "07_MAIN_CONDITIONAL",
        "12_": "07_MAIN_CONDITIONAL",
        "13_": "07_MAIN_CONDITIONAL",
        "20_": "08_SECOND_DOMAIN_CONDITIONAL",
        "21_": "08_SECOND_DOMAIN_CONDITIONAL",
        "22_": "08_SECOND_DOMAIN_CONDITIONAL",
        "23_": "08_SECOND_DOMAIN_CONDITIONAL",
    }
    input_map = {
        "00A_": "01_CP312_WHEELHOUSE",
        "00B_qwen": "02_QWEN_SNAPSHOT",
        "00B_internvl": "03_INTERNVL_SNAPSHOT",
        "00B_llava": "04_LLAVA_SNAPSHOT",
        "00C2_": "06_PRE_SMOKE_PERMISSIONS",
        "01_": "07_CONFIRMATORY_GENERATION",
        "02_": "08_CONFIRMATORY_QWEN",
        "03_": "09_CONFIRMATORY_INTERNVL",
        "04_": "10_CONFIRMATORY_LLAVA",
        "10_": "11_MAIN_GENERATION",
        "11_": "12_MAIN_QWEN",
        "12_": "13_MAIN_INTERNVL",
        "13_": "14_MAIN_LLAVA",
        "20_": "15_SECOND_DOMAIN_GENERATION",
        "21_": "16_SECOND_DOMAIN_QWEN",
        "22_": "17_SECOND_DOMAIN_INTERNVL",
        "23_": "18_SECOND_DOMAIN_LLAVA",
    }
    runtime_map = {
        "00A": "PLANNING_ESTIMATE: 15-35 min",
        "00B": "PLANNING_ESTIMATE: 15-30 min/provider",
        "00C2": "PLANNING_ESTIMATE: 15-45 min/provider",
        "01": "PLANNING_ESTIMATE: 2-8 h",
        "02": "PLANNING_ESTIMATE: 2-5 h",
        "03": "PLANNING_ESTIMATE: 3-7 h",
        "04": "PLANNING_ESTIMATE: 2-5 h",
        "10": "PLANNING_ESTIMATE: 4-10 h; 8-18 h reserve",
        "11": "PLANNING_ESTIMATE: 5-10 h",
        "12": "PLANNING_ESTIMATE: 8-16 h",
        "13": "PLANNING_ESTIMATE: 5-10 h",
        "20": "PLANNING_ESTIMATE: 2-5 h",
        "21": "PLANNING_ESTIMATE: 1-2 h",
        "22": "PLANNING_ESTIMATE: 1.5-3 h",
        "23": "PLANNING_ESTIMATE: 1-2 h",
    }
    for name, (stage, provider) in NOTEBOOKS.items():
        if name.startswith("00C1_"):
            continue
        prefix = name.split("_", 1)[0]
        folder = next(value for key, value in folder_map.items() if name.startswith(key))
        input_folder = next(
            value for key, value in input_map.items() if name.startswith(key)
        )
        if name.startswith("00A_"):
            readiness, accelerator, internet = "WAITING_FOR_EXTERNAL_BYTES", "OFF", "OFF"
            roles = "CODE;CONFIGS;EXECUTION_TOOLS;CP312_WHEELHOUSE"
            blocking = "Validated CP312 wheelhouse not present"
            parallel = ""
        elif name.startswith("00B_"):
            readiness, accelerator, internet = "WAITING_FOR_PRIOR_RETURN", "OFF", "OFF"
            roles = "CODE;CONFIGS;EXECUTION_TOOLS;CP312_WHEELHOUSE;MODEL_SNAPSHOT"
            blocking = "Matching immutable snapshot and 00A return required"
            parallel = "SNAPSHOT_SMOKE"
        elif name.startswith("00C2_"):
            readiness, accelerator, internet = "WAITING_FOR_EXTERNAL_BYTES", "T4x2", "OFF"
            roles = (
                "CODE;CONFIGS;EXECUTION_TOOLS;CP312_WHEELHOUSE;MODEL_SNAPSHOT;"
                "REAL_TWO_ITEM_SMOKE;PRE_SMOKE_PROVIDER_PERMISSION"
            )
            blocking = "Real smoke bytes, 00A/00B returns, and provider permission required"
            parallel = "REAL_MODEL_SMOKE"
        elif name.startswith("01_"):
            readiness, accelerator, internet = "WAITING_FOR_EXTERNAL_BYTES", "T4x2", "OFF"
            roles = "COMMON;CP312_WHEELHOUSE;CONFIRMATORY_GENERATION_INPUT"
            blocking = "Licensed source bytes and prior smoke gate required"
            parallel = ""
        elif name.startswith(("02_", "03_", "04_")):
            readiness, accelerator, internet = "WAITING_FOR_HUMAN_REVIEW", "T4x2", "OFF"
            roles = "COMMON;CP312_WHEELHOUSE;MODEL_SNAPSHOT;CONFIRMATORY_PROVIDER_INPUT;PERMISSION"
            blocking = "Genuine review, task freeze, detectability, and permission gates pending"
            parallel = "CONFIRMATORY_PROVIDERS"
        elif name.startswith(("10_", "11_", "12_", "13_")):
            readiness, accelerator, internet = "CONDITIONAL_NOT_AUTHORIZED", "T4x2", "OFF"
            roles = "COMMON;CP312_WHEELHOUSE;MAIN_GO;MAIN_INPUT"
            blocking = "Main execution_allowed=false until genuine confirmatory GO"
            parallel = "MAIN_PROVIDERS" if not name.startswith("10_") else ""
        else:
            readiness, accelerator, internet = "CONDITIONAL_NOT_AUTHORIZED", "T4x2", "OFF"
            roles = "COMMON;CP312_WHEELHOUSE;SECOND_DOMAIN_AUTHORIZATION;SECOND_DOMAIN_INPUT"
            blocking = "Second-domain execution_allowed=false until separate authorization"
            parallel = "SECOND_DOMAIN_PROVIDERS" if not name.startswith("20_") else ""
        rows.append({
            "name": name,
            "folder": folder,
            "stage": stage.upper(),
            "provider": provider,
            "study": (
                "specificity_confirmatory_cvpr"
                if name.startswith(("01_", "02_", "03_", "04_"))
                else "main_study_cvpr"
                if name.startswith(("10_", "11_", "12_", "13_"))
                else "second_domain_cvpr"
                if name.startswith(("20_", "21_", "22_", "23_"))
                else "all"
            ),
            "input_folder": input_folder,
            "required_roles": roles,
            "readiness": readiness,
            "accelerator": accelerator,
            "internet": internet,
            "runtime": runtime_map[prefix],
            "output": expected_return_zip(name, stage, provider),
            "destination": (
                f"data/runtime/{expected_return_zip(name, stage, provider)}"
                if name.startswith(("00A_", "00B_", "00C2_"))
                else f"local_inputs/provider_returns/{'specificity_confirmatory_cvpr' if name.startswith(('01_', '02_', '03_', '04_')) else 'main_study_cvpr' if name.startswith(('10_', '11_', '12_', '13_')) else 'second_domain_cvpr'}/{expected_return_zip(name, stage, provider)}"
            ),
            "parallel": parallel,
            "blocking": blocking,
            "source": f"notebooks/kaggle/cvpr/{name}",
        })
    return rows


INPUT_SPECS: dict[str, dict[str, Any]] = {
    "00_COMMON": {
        "filenames": [
            "certvic_code_bundle.zip",
            "certvic_configs_bundle.zip",
            "certvic_execution_tools_bundle.zip",
        ],
        "role": "REPOSITORY_COMMON",
        "readiness": "READY_NOW",
        "prerequisite": "Current repository checkout",
        "builder": "python3 -m certvic.cvpr.build_all_kaggle_inputs --local-only",
        "why": "Repository-derived deterministic bytes are locally available.",
    },
    "01_CP312_WHEELHOUSE": {
        "filenames": ["certvic_offline_wheelhouse_cp312.zip"],
        "role": "CP312_WHEELHOUSE",
        "readiness": "WAITING_FOR_EXTERNAL_BYTES",
        "prerequisite": "BUILD_CP312_WHEELHOUSE",
        "builder": "Run runbooks/00_PROVISIONING/00_build_certvic_cp312_wheelhouse.ipynb",
        "why": "The active CPython 3.12 Linux wheel bytes must be provisioned on Kaggle with Internet ON.",
        "expected_size": "approximately 3-18 GB; record actual bytes",
    },
    "02_QWEN_SNAPSHOT": {
        "filenames": ["qwen2_5_vl_7b_snapshot.zip"],
        "role": "QWEN_MODEL_SNAPSHOT",
        "readiness": "WAITING_FOR_EXTERNAL_BYTES",
        "prerequisite": "BUILD_MODEL_SNAPSHOT qwen2_5_vl_7b",
        "builder": "Run runbooks/00_PROVISIONING/01_build_qwen2_5_vl_7b_snapshot.ipynb",
        "why": "Immutable model bytes are external.",
        "expected_size": "15-18 GB",
    },
    "03_INTERNVL_SNAPSHOT": {
        "filenames": ["internvl2_8b_snapshot.zip"],
        "role": "INTERNVL_MODEL_SNAPSHOT",
        "readiness": "WAITING_FOR_EXTERNAL_BYTES",
        "prerequisite": "BUILD_MODEL_SNAPSHOT internvl_8b",
        "builder": "Run runbooks/00_PROVISIONING/02_build_internvl_8b_snapshot.ipynb",
        "why": "Immutable model bytes are external.",
        "expected_size": "16-20 GB",
    },
    "04_LLAVA_SNAPSHOT": {
        "filenames": ["llava_onevision_7b_snapshot.zip"],
        "role": "LLAVA_MODEL_SNAPSHOT",
        "readiness": "WAITING_FOR_EXTERNAL_BYTES",
        "prerequisite": "BUILD_MODEL_SNAPSHOT llava_onevision_7b",
        "builder": "Run runbooks/00_PROVISIONING/03_build_llava_onevision_7b_snapshot.ipynb",
        "why": "Immutable model bytes are external.",
        "expected_size": "15-18 GB",
    },
    "05_REAL_TWO_ITEM_SMOKE": {
        "filenames": ["certvic_real_two_item_smoke_bundle.zip"],
        "role": "REAL_TWO_ITEM_SMOKE",
        "readiness": "WAITING_FOR_EXTERNAL_BYTES",
        "prerequisite": "Licensed two-item task manifest and images",
        "builder": "python3 -m certvic.cvpr.smoke_input_builder --task-manifest local_inputs/smoke/real_smoke_tasks.jsonl --output kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip",
        "why": "The two real licensed examples are not repository bytes.",
        "expected_size": "1-50 MB",
    },
    "06_PRE_SMOKE_PERMISSIONS": {
        "filenames": ["certvic_pre_smoke_permissions.zip"],
        "role": "PRE_SMOKE_PERMISSIONS",
        "readiness": "WAITING_FOR_PRIOR_RETURN",
        "prerequisite": "Verified 00A, all three 00B returns, and real smoke bundle",
        "builder": "python3 -m certvic.cvpr.pre_smoke_packager --config local_inputs/pre_smoke_inputs.json",
        "why": "Permissions are derived from genuine upstream identities and cannot be precomputed.",
        "expected_size": "under 1 MB",
    },
    "07_CONFIRMATORY_GENERATION": {
        "filenames": ["certvic_confirmatory_generation_input.zip"],
        "role": "CONFIRMATORY_GENERATION_INPUT",
        "readiness": "WAITING_FOR_EXTERNAL_BYTES",
        "prerequisite": "Real smoke gate and licensed zero-overlap source universe",
        "builder": "python3 -m certvic.cvpr.confirmatory_input_builder --config local_inputs/confirmatory_generation_inputs.json",
        "why": "Licensed source and insertion bytes are external.",
        "expected_size": "1-20 GB",
    },
    "08_CONFIRMATORY_QWEN": {
        "filenames": ["certvic_confirmatory_qwen_input.zip"],
        "role": "CONFIRMATORY_QWEN_INPUT",
        "readiness": "WAITING_FOR_HUMAN_REVIEW",
    },
    "09_CONFIRMATORY_INTERNVL": {
        "filenames": ["certvic_confirmatory_internvl_input.zip"],
        "role": "CONFIRMATORY_INTERNVL_INPUT",
        "readiness": "WAITING_FOR_HUMAN_REVIEW",
    },
    "10_CONFIRMATORY_LLAVA": {
        "filenames": ["certvic_confirmatory_llava_input.zip"],
        "role": "CONFIRMATORY_LLAVA_INPUT",
        "readiness": "WAITING_FOR_HUMAN_REVIEW",
    },
    "11_MAIN_GENERATION": {
        "filenames": ["certvic_main_generation_input.zip"],
        "role": "MAIN_GENERATION_INPUT",
        "readiness": "CONDITIONAL_NOT_AUTHORIZED",
    },
    "12_MAIN_QWEN": {
        "filenames": ["certvic_main_qwen_input.zip"],
        "role": "MAIN_QWEN_INPUT",
        "readiness": "CONDITIONAL_NOT_AUTHORIZED",
    },
    "13_MAIN_INTERNVL": {
        "filenames": ["certvic_main_internvl_input.zip"],
        "role": "MAIN_INTERNVL_INPUT",
        "readiness": "CONDITIONAL_NOT_AUTHORIZED",
    },
    "14_MAIN_LLAVA": {
        "filenames": ["certvic_main_llava_input.zip"],
        "role": "MAIN_LLAVA_INPUT",
        "readiness": "CONDITIONAL_NOT_AUTHORIZED",
    },
    "15_SECOND_DOMAIN_GENERATION": {
        "filenames": ["certvic_coco_generation_input.zip"],
        "role": "SECOND_DOMAIN_GENERATION_INPUT",
        "readiness": "CONDITIONAL_NOT_AUTHORIZED",
    },
    "16_SECOND_DOMAIN_QWEN": {
        "filenames": ["certvic_coco_qwen_input.zip"],
        "role": "SECOND_DOMAIN_QWEN_INPUT",
        "readiness": "CONDITIONAL_NOT_AUTHORIZED",
    },
    "17_SECOND_DOMAIN_INTERNVL": {
        "filenames": ["certvic_coco_internvl_input.zip"],
        "role": "SECOND_DOMAIN_INTERNVL_INPUT",
        "readiness": "CONDITIONAL_NOT_AUTHORIZED",
    },
    "18_SECOND_DOMAIN_LLAVA": {
        "filenames": ["certvic_coco_llava_input.zip"],
        "role": "SECOND_DOMAIN_LLAVA_INPUT",
        "readiness": "CONDITIONAL_NOT_AUTHORIZED",
    },
}

for _stage in (
    "08_CONFIRMATORY_QWEN", "09_CONFIRMATORY_INTERNVL", "10_CONFIRMATORY_LLAVA"
):
    INPUT_SPECS[_stage].update({
        "prerequisite": "Genuine human review, exact selection, detectability, task freeze, and provider permission",
        "builder": f"python3 -m certvic.cvpr.scientific_input_builder --study confirmatory --provider {INPUT_SPECS[_stage]['role'].split('_')[1].lower()} --config local_inputs/{_stage.lower()}.json --run-tag specificity_confirmatory_v1",
        "why": "Prospective human and authorization gates are incomplete.",
        "expected_size": "1 MB-25 GB",
    })
for _stage in ("11_MAIN_GENERATION", "12_MAIN_QWEN", "13_MAIN_INTERNVL", "14_MAIN_LLAVA"):
    INPUT_SPECS[_stage].update({
        "prerequisite": "Genuine confirmatory GO decision",
        "builder": "python3 -m certvic.cvpr.build_all_kaggle_inputs --with-external-roots local_inputs/main_external_roots.yaml",
        "why": "Main execution_allowed=false until confirmatory gates pass.",
        "expected_size": "1 MB-60 GB depending on role",
    })
for _stage in (
    "15_SECOND_DOMAIN_GENERATION", "16_SECOND_DOMAIN_QWEN",
    "17_SECOND_DOMAIN_INTERNVL", "18_SECOND_DOMAIN_LLAVA",
):
    INPUT_SPECS[_stage].update({
        "prerequisite": "Separate second-domain feasibility and execution authorization",
        "builder": "python3 -m certvic.cvpr.build_all_kaggle_inputs --with-external-roots local_inputs/second_domain_external_roots.yaml",
        "why": "Second-domain execution_allowed=false until separately authorized.",
        "expected_size": "1 MB-60 GB depending on role",
    })


def _root_helper_sources() -> dict[str, tuple[str, bool]]:
    refresh = '''#!/usr/bin/env python3
"""Refresh the unified CertVIC Kaggle operator pack without fabricating inputs."""
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from certvic.cvpr.kagglefiles_pack import refresh_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(refresh_main())
'''
    importer = '''#!/usr/bin/env python3
"""Authenticate and import one unchanged Kaggle return into CertVIC."""
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from certvic.cvpr.kagglefiles_pack import import_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(import_main())
'''
    resume = '''#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR/.."
python3 scripts/run_all_cpu_workflows.py --resume
python3 -m certvic.cvpr.doctor --json
python3 -m certvic.cvpr.next_action
python3 -m certvic.cvpr.run_graph status
'''
    return {
        "refresh_kagglefiles.py": (refresh, True),
        "import_kaggle_return.py": (importer, True),
        "run_local_resume.sh": (resume, True),
    }


def _validate_external_bundle(path: Path, stage: str) -> dict[str, Any]:
    try:
        result = verify_bundle(path)
    except Exception as error:
        raise KagglefilesPackError(f"{stage}: unverified external ZIP {path}: {error}") from error
    if not result.get("passed"):
        raise KagglefilesPackError(f"{stage}: unverified external ZIP {path}: {result['errors']}")
    manifest = result["bundle_manifest"]
    if stage == "01_CP312_WHEELHOUSE" and manifest.get("runtime_profile_id") != ACTIVE_PROFILE:
        raise KagglefilesPackError("CP312 input folder contains a non-CP312 wheelhouse")
    expected_provider = {
        "02_QWEN_SNAPSHOT": "qwen2_5_vl_7b",
        "03_INTERNVL_SNAPSHOT": "internvl_8b",
        "04_LLAVA_SNAPSHOT": "llava_onevision_7b",
    }.get(stage)
    if expected_provider and manifest.get("provider") != expected_provider:
        raise KagglefilesPackError(f"{stage}: snapshot provider mismatch")
    return result


def _link_or_copy(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() or destination.is_symlink():
        destination.unlink()
    try:
        os.link(source, destination)
        method = "HARDLINK"
    except OSError:
        shutil.copyfile(source, destination)
        method = "COPY"
    if _sha(source) != _sha(destination):
        raise KagglefilesPackError(f"materialized bytes differ: {destination}")
    return method


def _write_input_stage(
    pack_root: Path,
    stage: str,
    spec: Mapping[str, Any],
    source_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    root = pack_root / "inputs" / stage
    root.mkdir(parents=True, exist_ok=True)
    expected = list(spec["filenames"])
    unexpected = sorted(
        path.name for path in root.glob("*.zip") if path.name not in expected
    )
    if unexpected:
        raise KagglefilesPackError(f"{stage}: unexpected external ZIPs: {unexpected}")
    present: list[dict[str, Any]] = []
    for filename in expected:
        path = root / filename
        if not path.is_file():
            continue
        result = _validate_external_bundle(path, stage)
        present.append({
            "filename": filename,
            "size": path.stat().st_size,
            "sha256": result["sha256"],
            "verified": True,
        })
        source_map[path.relative_to(pack_root).as_posix()] = {
            "source_path": "GENUINE_EXTERNAL_INPUT_PRESERVED",
            "materialization_method": "PRESERVED_AUTHENTICATED_EXTERNAL",
        }
    ready = len(present) == len(expected)
    readiness = str(spec["readiness"])
    if ready and readiness not in {"CONDITIONAL_NOT_AUTHORIZED", "WAITING_FOR_HUMAN_REVIEW"}:
        readiness = "READY_NOW"
    status = {
        "schema": "certvic.kagglefiles.input_status.v1",
        "stage": stage,
        "role": spec["role"],
        "expected_filenames": expected,
        "required_files_present": ready,
        "present_files": present,
        "readiness": readiness,
        "missing_role": None if ready else spec["role"],
        "why_missing": None if ready else spec.get("why"),
        "prerequisite_stage": spec.get("prerequisite"),
        "exact_builder": spec.get("builder"),
        "expected_size": spec.get("expected_size", "record actual deterministic bytes"),
        "where_completed_file_belongs": f"kagglefiles/inputs/{stage}/",
        "evidence_boundary": (
            "paper_evidence=false; do not fabricate model/data/permission/review/output bytes"
        ),
        "paper_evidence": False,
    }
    status_path = root / "STATUS.json"
    _write(status_path, _json_bytes(status))
    source_map[status_path.relative_to(pack_root).as_posix()] = {
        "source_path": "certvic/cvpr/kagglefiles_pack.py#INPUT_SPECS",
        "materialization_method": "GENERATED",
    }
    attach_lines = [
        f"# Upload files for {stage}",
        "",
        f"Readiness: `{readiness}`.",
        "",
        "Always attach `inputs/00_COMMON/` to execution notebooks. Attach only authenticated ZIPs; Kaggle dataset titles, owners, filenames, extensions, mounts, and nesting may vary because runbooks discover by content.",
        "",
        "Expected files:",
        "",
        *[f"- `{name}` ({'present and verified' if (root / name).is_file() else 'not present'})" for name in expected],
        "",
        f"Builder or provisioning action: `{spec.get('builder', 'See STATUS.json')}`.",
        "",
        "Keep `paper_evidence=false`. Never substitute a similarly named or unauthenticated archive.",
    ]
    upload_path = root / "UPLOAD_THESE_FILES.md"
    _write(upload_path, "\n".join(attach_lines) + "\n")
    source_map[upload_path.relative_to(pack_root).as_posix()] = {
        "source_path": "certvic/cvpr/kagglefiles_pack.py#_write_input_stage",
        "materialization_method": "GENERATED",
    }
    not_ready = root / "NOT_READY.md"
    if ready:
        if not_ready.is_file():
            not_ready.unlink()
    else:
        body = f"""# NOT READY: {spec['role']}

- Missing role: `{spec['role']}`
- Why missing: {spec.get('why')}
- Prerequisite stage: `{spec.get('prerequisite')}`
- Exact builder/notebook/command: `{spec.get('builder')}`
- Expected filename: `{'; '.join(expected)}`
- Expected size: {spec.get('expected_size', 'record actual deterministic bytes')}
- Completed-file destination: `kagglefiles/inputs/{stage}/`
- Evidence boundary: `paper_evidence=false`; do not fabricate the missing bytes.
"""
        _write(not_ready, body)
        source_map[not_ready.relative_to(pack_root).as_posix()] = {
            "source_path": "certvic/cvpr/kagglefiles_pack.py#_write_input_stage",
            "materialization_method": "GENERATED",
        }
    return status


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "order", "stage", "runbook", "runbook_path", "matching_input_folder",
        "required_roles", "required_files_present", "readiness", "accelerator",
        "internet", "estimated_runtime", "expected_output", "local_destination",
        "next_local_command", "can_run_in_parallel_with", "blocking_reason",
        "paper_evidence",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _start_here(
    commit: str,
    origin: str,
    doctor_state: str,
    rows: list[dict[str, Any]],
) -> str:
    lines = [
        "OPEN ONLY THIS FOLDER FOR KAGGLE EXECUTION.",
        "DO NOT NAVIGATE THE REST OF THE REPOSITORY.",
        "",
        "# CertVIC Kaggle operator pack",
        "",
        f"- Repository source commit: `{commit}`",
        f"- Origin/main at generation: `{origin}`",
        f"- Doctor state: `{doctor_state}`",
        f"- Active runtime profile: `{ACTIVE_PROFILE}`",
        "- Evidence boundary: `paper_evidence=false`; genuine `human_reviewed=true` count is 0.",
        "- Main: `execution_allowed=false`.",
        "- Second domain: `execution_allowed=false`.",
        "",
        "## C4 live-provisioning retry",
        "",
        "Delete the four failed Kaggle draft sessions. Pull the latest `main`, then use only "
        "the four refreshed notebooks in `runbooks/00_PROVISIONING/` with the refreshed "
        "files from `inputs/00_COMMON/`. Use **Accelerator OFF**, **Internet ON**, and click "
        "**Run All**. Do not reuse a failed session's working directory.",
        "",
        "## Exact first executable action",
        "",
        "`BUILD_CP312_WHEELHOUSE`",
        "",
        "Open `runbooks/00_PROVISIONING/00_build_certvic_cp312_wheelhouse.ipynb`, attach the three ZIPs from `inputs/00_COMMON/`, set **Accelerator OFF** and **Internet ON**, then click **Run All**. Download `certvic_offline_wheelhouse_cp312.zip` and import it unchanged with:",
        "",
        "```bash",
        "python3 kagglefiles/import_kaggle_return.py /path/to/downloaded_return.zip",
        "```",
        "",
        "The locally present CPython 3.10 wheelhouse is legacy and is not an active input.",
        "",
        "## Chronological run table",
        "",
        "| Order | Stage | Runbook | Matching input | Attach | Accelerator | Internet | Estimate | Expected output | Local destination | Resume | Readiness |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['order']} | `{row['stage']}` | `{row['runbook']}` | "
            f"`{row['matching_input_folder']}` | `{row['required_roles']}` | "
            f"{row['accelerator']} | {row['internet']} | {row['estimated_runtime']} | "
            f"`{row['expected_output']}` | `{row['local_destination']}` | "
            f"`{row['next_local_command']}` | `{row['readiness']}` |"
        )
    lines += [
        "",
        "## Parallel execution",
        "",
        "Only rows sharing the same nonempty `can_run_in_parallel_with` value in `RUN_ORDER.csv` are explicit parallel groups. Provider permissions remain distinct and single-use.",
        "",
        "## After every download",
        "",
        "```bash",
        "python3 kagglefiles/import_kaggle_return.py /path/to/downloaded_return.zip",
        "bash kagglefiles/run_local_resume.sh",
        "```",
        "",
        "Never rename archive contents, edit a runbook configuration cell, bypass a permission gate, or treat a planning estimate as an observed runtime.",
    ]
    return "\n".join(lines) + "\n"


def _manifest_record(
    path: Path,
    pack_root: Path,
    source_map: Mapping[str, Mapping[str, Any]],
    runbooks: Mapping[str, Mapping[str, Any]],
    statuses: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    relative = path.relative_to(pack_root).as_posix()
    source = source_map.get(relative, {})
    runbook = runbooks.get(relative, {})
    stage = str(runbook.get("stage") or relative.split("/", 2)[1] if "/" in relative else "pack")
    status = statuses.get(stage, {})
    suffix_schema = {
        ".ipynb": "nbformat.v4",
        ".json": "json",
        ".csv": "csv",
        ".md": "markdown",
        ".py": "python3",
        ".sh": "posix-shell",
        ".zip": "certvic.kaggle.bundle.v1",
        ".sha256": "sha256sum",
    }
    return {
        "relative_path": relative,
        "role": runbook.get("stage") or status.get("role") or "OPERATOR_PACK_FILE",
        "stage": stage,
        "source_path": source.get("source_path", "certvic/cvpr/kagglefiles_pack.py"),
        "materialization_method": source.get("materialization_method", "GENERATED"),
        "size": path.stat().st_size,
        "sha256": _sha(path),
        "schema": suffix_schema.get(path.suffix.lower(), "opaque-file"),
        "runtime_profile": ACTIVE_PROFILE if path.suffix in {".ipynb", ".zip"} else "NOT_APPLICABLE",
        "provider": runbook.get("provider"),
        "study": runbook.get("study", "all"),
        "readiness": runbook.get("readiness") or status.get("readiness") or "READY_NOW",
        "canonical_output": runbook.get("output"),
        "paper_evidence": False,
    }


def build_operator_pack(
    pack_root: str | Path = DEFAULT_PACK_ROOT,
    *,
    rebuild_common: bool = True,
    pytest_summary: str | None = None,
    notebook_summary: str | None = None,
) -> dict[str, Any]:
    """Refresh the complete pack while preserving only verified external inputs."""
    pack_root = Path(pack_root)
    pack_root.mkdir(parents=True, exist_ok=True)
    # Validation tools such as compileall may leave caches inside the generated pack.
    # They are never operator inputs and must not alter its required two-directory shape.
    for cache_dir in sorted(pack_root.rglob("__pycache__"), reverse=True):
        shutil.rmtree(cache_dir)
    for bytecode in pack_root.rglob("*.py[co]"):
        bytecode.unlink()
    for finder_metadata in pack_root.rglob(".DS_Store"):
        finder_metadata.unlink()
    extra_dirs = sorted(
        path.name for path in pack_root.iterdir()
        if path.is_dir() and path.name not in {"runbooks", "inputs"}
    )
    if extra_dirs:
        raise KagglefilesPackError(f"unexpected root-level directories: {extra_dirs}")
    (pack_root / "runbooks").mkdir(exist_ok=True)
    (pack_root / "inputs").mkdir(exist_ok=True)
    for folder in RUNBOOK_FOLDERS:
        (pack_root / "runbooks" / folder).mkdir(parents=True, exist_ok=True)
    for folder in INPUT_FOLDERS:
        (pack_root / "inputs" / folder).mkdir(parents=True, exist_ok=True)

    if rebuild_common:
        from certvic.cvpr.build_all_kaggle_inputs import build_local_bundles

        local = build_local_bundles()
    else:
        local = []
        for filename in (
            "certvic_code_bundle.zip", "certvic_configs_bundle.zip",
            "certvic_execution_tools_bundle.zip",
        ):
            source = ROOT / "kaggle_uploads/00_code" / filename
            verification = verify_bundle(source)
            local.append({
                "name": filename, "path": str(source), "size": source.stat().st_size,
                "sha256": verification["sha256"], "status": "CREATED_AND_VALIDATED",
            })
    local_by_name = {row["name"]: row for row in local}
    build_suite(ROOT / "notebooks/kaggle/cvpr")
    source_map: dict[str, dict[str, Any]] = {}

    for name, (payload, executable) in _root_helper_sources().items():
        destination = pack_root / name
        _write(destination, payload, executable=executable)
        source_map[name] = {
            "source_path": "certvic/cvpr/kagglefiles_pack.py#_root_helper_sources",
            "materialization_method": "GENERATED",
        }

    runbook_specs = _runbook_specs()
    required_paths: set[str] = set()
    runbook_map: dict[str, dict[str, Any]] = {}
    for spec in runbook_specs:
        relative = f"runbooks/{spec['folder']}/{spec['name']}"
        destination = pack_root / relative
        if spec["name"] == "00_build_certvic_cp312_wheelhouse.ipynb":
            payload = cp312_provisioning_notebook()
            method = "GENERATED_LIVE_RUNTIME_PROVISIONER"
        elif spec["stage"] == "BUILD_MODEL_SNAPSHOT":
            payload = snapshot_provisioning_notebook(str(spec["provider"]))
            method = "GENERATED_PROVIDER_BOUND_RUNBOOK"
        else:
            source = ROOT / str(spec["source"])
            payload = source.read_bytes()
            method = "COPIED_GOVERNED_RUNBOOK"
        _write(destination, payload)
        required_paths.add(relative)
        source_map[relative] = {
            "source_path": spec["source"],
            "materialization_method": method,
        }
        runbook_map[relative] = spec
    for path in (pack_root / "runbooks").rglob("*.ipynb"):
        relative = path.relative_to(pack_root).as_posix()
        if relative not in required_paths:
            raise KagglefilesPackError(f"obsolete or duplicate runbook in pack: {relative}")
    pointer = pack_root / "runbooks/02_MODEL_SNAPSHOTS/USE_00_PROVISIONING.md"
    _write(
        pointer,
        "# Model snapshot provisioning\n\nThe three provider-bound source-of-truth builders are in `../00_PROVISIONING/`. They are intentionally not duplicated here.\n",
    )
    source_map[pointer.relative_to(pack_root).as_posix()] = {
        "source_path": "certvic/cvpr/kagglefiles_pack.py#_runbook_specs",
        "materialization_method": "GENERATED_POINTER_NO_DUPLICATION",
    }

    common_root = pack_root / "inputs/00_COMMON"
    for filename in INPUT_SPECS["00_COMMON"]["filenames"]:
        source = Path(str(local_by_name[filename]["path"]))
        destination = common_root / filename
        method = _link_or_copy(source, destination)
        verification = verify_bundle(destination)
        if not verification["passed"]:
            raise KagglefilesPackError(f"common bundle failed after placement: {filename}")
        source_map[destination.relative_to(pack_root).as_posix()] = {
            "source_path": source.relative_to(ROOT).as_posix(),
            "materialization_method": method,
        }

    statuses: dict[str, dict[str, Any]] = {}
    for stage, spec in INPUT_SPECS.items():
        statuses[stage] = _write_input_stage(pack_root, stage, spec, source_map)

    run_rows: list[dict[str, Any]] = []
    for order, spec in enumerate(runbook_specs, start=1):
        input_status = statuses[str(spec["input_folder"])]
        readiness = str(spec["readiness"])
        if spec["stage"] in {"BUILD_CP312_WHEELHOUSE", "BUILD_MODEL_SNAPSHOT"}:
            present = True
        else:
            present = bool(input_status["required_files_present"])
            if present and readiness in {"WAITING_FOR_EXTERNAL_BYTES", "WAITING_FOR_PRIOR_RETURN"}:
                readiness = "READY_NOW"
        if readiness not in ALLOWED_READINESS:
            raise KagglefilesPackError(f"invalid readiness: {readiness}")
        row = {
            "order": order,
            "stage": spec["stage"],
            "runbook": spec["name"],
            "runbook_path": f"runbooks/{spec['folder']}/{spec['name']}",
            "matching_input_folder": f"inputs/{spec['input_folder']}",
            "required_roles": spec["required_roles"],
            "required_files_present": str(present).lower(),
            "readiness": readiness,
            "accelerator": spec["accelerator"],
            "internet": spec["internet"],
            "estimated_runtime": spec["runtime"],
            "expected_output": spec["output"],
            "local_destination": spec["destination"],
            "next_local_command": "bash kagglefiles/run_local_resume.sh",
            "can_run_in_parallel_with": spec["parallel"],
            "blocking_reason": spec["blocking"],
            "paper_evidence": "false",
        }
        run_rows.append(row)
        runbook_map[row["runbook_path"]] = {**spec, "readiness": readiness}
    run_order = pack_root / "RUN_ORDER.csv"
    _write_csv(run_order, run_rows)
    source_map["RUN_ORDER.csv"] = {
        "source_path": "certvic/cvpr/kagglefiles_pack.py#_runbook_specs",
        "materialization_method": "GENERATED",
    }

    commit = _git("rev-parse", "HEAD")
    origin = _git("rev-parse", "origin/main")
    generated = _git("show", "-s", "--format=%cI", commit)
    doctor = subprocess.run(
        [sys.executable, "-m", "certvic.cvpr.doctor", "--json"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    doctor_state = json.loads(doctor.stdout)["state"]
    start = pack_root / "START_HERE.md"
    _write(start, _start_here(commit, origin, doctor_state, run_rows))
    source_map["START_HERE.md"] = {
        "source_path": "certvic/cvpr/kagglefiles_pack.py#_start_here",
        "materialization_method": "GENERATED",
    }
    status = pack_root / "KAGGLEFILES_PACK_STATUS.md"
    _write(status, f"""# CertVIC unified Kagglefiles pack status

- Source commit: `{commit}`
- Active runtime profile: `{ACTIVE_PROFILE}`
- Doctor state: `{doctor_state}`
- Required operator runbooks: {len(run_rows)}
- Repository-derived common ZIPs: 3/3 verified
- External/gated input stages: {len(INPUT_FOLDERS) - 1}, truthfully represented by `STATUS.json` and `NOT_READY.md` when absent
- Genuine `human_reviewed=true` count: 0
- Main `execution_allowed`: false
- Second-domain `execution_allowed`: false
- Obsolete notebooks in pack: 0
- Scientific GPU runs launched by refresh: 0

First action: `BUILD_CP312_WHEELHOUSE`.

CERTVIC_UNIFIED_KAGGLEFILES_OPERATOR_PACK_COMPLETE
KAGGLEFILES_RUNBOOKS_ORDERED_AND_VALIDATED
KAGGLEFILES_INPUTS_BUILT_OR_TRUTHFULLY_MARKED
CP312_RUNTIME_PROFILE_ACTIVE
NO_OBSOLETE_RUNBOOKS_INCLUDED
NO_MANUAL_REPOSITORY_NAVIGATION_REQUIRED
FIRST_ACTION_EXPLICIT

CERTVIC_LIVE_KAGGLE_PROVISIONING_PATCH_COMPLETE
SNAPSHOT_PROVISIONERS_SUPPORT_EXTRACTED_DATASETS
CP312_RESOLVER_USES_LIVE_RUNTIME_TAGS
CP312_FAILURE_REPORTING_ACTIONABLE
UNIFIED_KAGGLEFILES_PACK_REFRESHED
READY_TO_RETRY_PROVISIONING
""")
    source_map["KAGGLEFILES_PACK_STATUS.md"] = {
        "source_path": "certvic/cvpr/kagglefiles_pack.py#build_operator_pack",
        "materialization_method": "GENERATED",
    }

    prior_manifest: dict[str, Any] = {}
    manifest_path = pack_root / "PACK_MANIFEST.json"
    if manifest_path.is_file():
        try:
            prior_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prior_manifest = {}
    test_totals = pytest_summary or prior_manifest.get("test_totals") or "PENDING_FINAL_VALIDATION"
    notebook_totals = (
        notebook_summary
        or prior_manifest.get("notebook_validation_totals")
        or "PENDING_FINAL_VALIDATION"
    )
    materialized_paths = sorted(
        path for path in pack_root.rglob("*")
        if path.is_file() and path.name not in {"PACK_MANIFEST.json", "CHECKSUMS.sha256"}
        and path.name != ".IMPORTED_RETURNS.json"
    )
    records = [
        _manifest_record(path, pack_root, source_map, runbook_map, statuses)
        for path in materialized_paths
    ]
    deterministic_fingerprint = hashlib.sha256(_json_bytes(records)).hexdigest()
    missing = [
        filename
        for stage, spec in INPUT_SPECS.items()
        if stage != "00_COMMON"
        for filename in spec["filenames"]
        if not (pack_root / "inputs" / stage / filename).is_file()
    ]
    manifest = {
        "schema": "certvic.kagglefiles.pack_manifest.v1",
        "status": "CERTVIC_UNIFIED_KAGGLEFILES_OPERATOR_PACK_COMPLETE",
        "final_status": [
            "CERTVIC_UNIFIED_KAGGLEFILES_OPERATOR_PACK_COMPLETE",
            "KAGGLEFILES_RUNBOOKS_ORDERED_AND_VALIDATED",
            "KAGGLEFILES_INPUTS_BUILT_OR_TRUTHFULLY_MARKED",
            "CP312_RUNTIME_PROFILE_ACTIVE",
            "NO_OBSOLETE_RUNBOOKS_INCLUDED",
            "NO_MANUAL_REPOSITORY_NAVIGATION_REQUIRED",
            "FIRST_ACTION_EXPLICIT",
        ],
        "provisioning_patch_status": [
            "CERTVIC_LIVE_KAGGLE_PROVISIONING_PATCH_COMPLETE",
            "SNAPSHOT_PROVISIONERS_SUPPORT_EXTRACTED_DATASETS",
            "CP312_RESOLVER_USES_LIVE_RUNTIME_TAGS",
            "CP312_FAILURE_REPORTING_ACTIONABLE",
            "UNIFIED_KAGGLEFILES_PACK_REFRESHED",
            "READY_TO_RETRY_PROVISIONING",
        ],
        "repository": "Saket-Maganti/certvic",
        "repository_commit": commit,
        "origin_main_commit": origin,
        "generated_at_utc": generated,
        "doctor_state": doctor_state,
        "active_runtime_profile": ACTIVE_PROFILE,
        "legacy_runtime_profiles": LEGACY_PROFILES,
        "test_totals": test_totals,
        "notebook_validation_totals": notebook_totals,
        "missing_external_artifacts": missing,
        "human_gate_status": {
            "genuine_human_reviewed_true_count": 0,
            "status": "WAITING_FOR_HUMAN_REVIEW",
        },
        "Main_authorization": {"execution_allowed": False, "status": "CONDITIONAL_NOT_AUTHORIZED"},
        "second_domain_authorization": {
            "execution_allowed": False,
            "status": "CONDITIONAL_NOT_AUTHORIZED",
        },
        "deterministic_portion_sha256": deterministic_fingerprint,
        "primary_subfolders": ["runbooks", "inputs"],
        "files": [
            *records,
            {
                "relative_path": "PACK_MANIFEST.json", "role": "SELF_MANIFEST",
                "stage": "pack", "source_path": "certvic/cvpr/kagglefiles_pack.py",
                "materialization_method": "GENERATED_SELF_REFERENTIAL",
                "size": None, "sha256": None, "schema": "certvic.kagglefiles.pack_manifest.v1",
                "runtime_profile": "NOT_APPLICABLE", "provider": None, "study": "all",
                "readiness": "READY_NOW", "canonical_output": None, "paper_evidence": False,
            },
            {
                "relative_path": "CHECKSUMS.sha256", "role": "CHECKSUM_INDEX",
                "stage": "pack", "source_path": "certvic/cvpr/kagglefiles_pack.py",
                "materialization_method": "GENERATED_SELF_REFERENTIAL",
                "size": None, "sha256": None, "schema": "sha256sum",
                "runtime_profile": "NOT_APPLICABLE", "provider": None, "study": "all",
                "readiness": "READY_NOW", "canonical_output": None, "paper_evidence": False,
            },
        ],
        "paper_evidence": False,
    }
    _write(manifest_path, _json_bytes(manifest))
    checksummed = sorted(
        path for path in pack_root.rglob("*")
        if path.is_file() and path.name not in {"CHECKSUMS.sha256", ".IMPORTED_RETURNS.json"}
    )
    checksums = "".join(
        f"{_sha(path)}  {path.relative_to(pack_root).as_posix()}\n" for path in checksummed
    )
    _write(pack_root / "CHECKSUMS.sha256", checksums)
    return {
        "schema": "certvic.kagglefiles.refresh.v1",
        "status": "CERTVIC_UNIFIED_KAGGLEFILES_OPERATOR_PACK_COMPLETE",
        "pack_root": str(pack_root),
        "repository_commit": commit,
        "origin_main_commit": origin,
        "doctor_state": doctor_state,
        "runbooks": len(run_rows),
        "common_bundles": 3,
        "missing_external_artifacts": missing,
        "deterministic_portion_sha256": deterministic_fingerprint,
        "paper_evidence": False,
    }


def verify_pack(pack_root: str | Path = DEFAULT_PACK_ROOT) -> dict[str, Any]:
    root = Path(pack_root)
    errors: list[str] = []
    dirs = sorted(path.name for path in root.iterdir() if path.is_dir()) if root.is_dir() else []
    if dirs != ["inputs", "runbooks"]:
        errors.append(f"root subfolders differ: {dirs}")
    manifest_path = root / "PACK_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    checksums_path = root / "CHECKSUMS.sha256"
    if not checksums_path.is_file():
        errors.append("CHECKSUMS.sha256 missing")
    else:
        for line in checksums_path.read_text().splitlines():
            expected, relative = line.split("  ", 1)
            path = root / relative
            if not path.is_file() or _sha(path) != expected:
                errors.append(f"checksum mismatch: {relative}")
    run_rows = list(csv.DictReader((root / "RUN_ORDER.csv").open()))
    if len(run_rows) != 23 or len({row["runbook"] for row in run_rows}) != 23:
        errors.append("required runbook cardinality/uniqueness failed")
    for row in run_rows:
        path = root / row["runbook_path"]
        if not path.is_file():
            errors.append(f"runbook missing: {row['runbook_path']}")
        if row["readiness"] not in ALLOWED_READINESS:
            errors.append(f"invalid readiness: {row['readiness']}")
    for stage in INPUT_FOLDERS:
        folder = root / "inputs" / stage
        for filename in ("STATUS.json", "UPLOAD_THESE_FILES.md"):
            if not (folder / filename).is_file():
                errors.append(f"{stage}/{filename} missing")
        status = json.loads((folder / "STATUS.json").read_text())
        if not status["required_files_present"] and not (folder / "NOT_READY.md").is_file():
            errors.append(f"{stage}: missing input has no NOT_READY.md")
        for path in folder.glob("*.zip"):
            try:
                _validate_external_bundle(path, stage)
            except KagglefilesPackError as error:
                errors.append(str(error))
    if manifest.get("paper_evidence") is not False:
        errors.append("pack manifest paper_evidence boundary failed")
    return {
        "schema": "certvic.kagglefiles.pack_verification.v1",
        "passed": not errors,
        "errors": errors,
        "root_subfolders": dirs,
        "runbooks": len(run_rows),
        "manifest_files": len(manifest.get("files", [])),
        "paper_evidence": False,
    }


def _safe_zip_payloads(path: Path) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names: list[str] = []
            total = 0
            for info in infos:
                name = info.filename
                pure = PurePosixPath(name)
                mode = (info.external_attr >> 16) & 0xFFFF
                if (
                    not name or name.endswith("/") or pure.is_absolute() or ".." in pure.parts
                    or info.is_dir() or stat.S_ISLNK(mode)
                ):
                    raise KagglefilesPackError(f"unsafe return member: {name!r}")
                names.append(name)
                total += info.file_size
                if total > 80_000_000_000:
                    raise KagglefilesPackError("return extracted-size limit exceeded")
            if len(names) != len(set(names)) or archive.testzip() is not None:
                raise KagglefilesPackError("return is corrupt or contains duplicate members")
            return {name: archive.read(name) for name in names}
    except zipfile.BadZipFile as error:
        raise KagglefilesPackError("downloaded return is not a valid ZIP") from error


def _verify_return_hashes(payloads: Mapping[str, bytes]) -> None:
    if "hash_manifest.json" not in payloads:
        raise KagglefilesPackError("return has no authenticated hash_manifest.json")
    manifest = json.loads(payloads["hash_manifest.json"])
    declared = manifest.get("files", manifest)
    if not isinstance(declared, dict) or not declared:
        raise KagglefilesPackError("return hash manifest is empty")
    observed = {
        name: hashlib.sha256(payload).hexdigest()
        for name, payload in payloads.items() if name != "hash_manifest.json"
    }
    normalized = {
        name: value.get("sha256") if isinstance(value, dict) else value
        for name, value in declared.items()
    }
    if normalized != observed:
        raise KagglefilesPackError("return bytes differ from hash_manifest.json")


def _require_active_profile(value: Mapping[str, Any], *, role: str) -> None:
    profile = value.get("runtime_profile_id")
    if profile != ACTIVE_PROFILE:
        raise KagglefilesPackError(
            f"{role}: wrong or missing runtime profile {profile!r}; required {ACTIVE_PROFILE}"
        )


def identify_kaggle_return(path: str | Path, *, pack_root: str | Path = DEFAULT_PACK_ROOT) -> dict[str, Any]:
    """Authenticate a return by contents and resolve its canonical destination."""
    source = Path(path).resolve()
    if not source.is_file() or source.stat().st_size == 0:
        raise KagglefilesPackError("return does not exist or is zero-byte")
    pack = Path(pack_root)
    payloads = _safe_zip_payloads(source)
    digest = _sha(source)
    if "bundle_manifest.json" in payloads:
        result = verify_bundle(source)
        if not result["passed"]:
            raise KagglefilesPackError(f"bundle return failed verification: {result['errors']}")
        manifest = result["bundle_manifest"]
        bundle_type = manifest.get("bundle_type")
        if bundle_type == "OFFLINE_LINUX_WHEELHOUSE":
            _require_active_profile(manifest, role="wheelhouse")
            canonical = "certvic_offline_wheelhouse_cp312.zip"
            destination = pack / "inputs/01_CP312_WHEELHOUSE" / canonical
            return_type = "CP312_WHEELHOUSE"
        elif bundle_type == "MODEL_SNAPSHOT":
            provider = str(manifest.get("provider"))
            if provider not in PROVIDERS:
                raise KagglefilesPackError(f"unknown snapshot provider: {provider}")
            canonical = str(PROVIDERS[provider]["output"])
            destination = pack / "inputs" / str(PROVIDERS[provider]["input_stage"]) / canonical
            return_type = f"MODEL_SNAPSHOT:{provider}"
        else:
            raise KagglefilesPackError(f"bundle type is not an importable Kaggle return: {bundle_type}")
        return {
            "return_type": return_type, "canonical_filename": canonical,
            "destination": str(destination), "sha256": digest, "size": source.stat().st_size,
            "runtime_profile_id": manifest.get("runtime_profile_id"), "paper_evidence": False,
        }
    _verify_return_hashes(payloads)
    json_payloads = {
        name: json.loads(payload)
        for name, payload in payloads.items()
        if name.endswith(".json") and name != "hash_manifest.json"
    }
    if "00A_environment.json" in payloads:
        primary = json.loads(payloads["00A_environment.json"])
        if primary.get("passed") is not True:
            raise KagglefilesPackError("00A return is not successful")
        _require_active_profile(primary, role="00A")
        canonical = "00A_environment_bundle.zip"
        destination = ROOT / "data/runtime" / canonical
        return_type = "00A_ENVIRONMENT"
    else:
        snapshot_primary = [
            name for name in payloads
            if re.fullmatch(r"00B_[a-z0-9_]+_snapshot\.json", name)
        ]
        if len(snapshot_primary) == 1:
            primary = json.loads(payloads[snapshot_primary[0]])
            provider = str(primary.get("provider"))
            if provider not in PROVIDERS or primary.get("passed") is not True:
                raise KagglefilesPackError("00B provider or validation status is invalid")
            _require_active_profile(primary, role="00B")
            canonical = f"00B_{provider}_snapshot_bundle.zip"
            destination = ROOT / "data/runtime" / canonical
            return_type = f"00B_SNAPSHOT_SMOKE:{provider}"
        elif "authorization_proof.json" in payloads and "predictions.jsonl" in payloads:
            from certvic.cvpr.smoke_artifacts import read_smoke_archive

            result = read_smoke_archive(source)
            runtime = result["runtime"]
            if runtime.get("runtime_class") not in {"REAL_MODEL_SMOKE", "NON_EVIDENCE_REAL_MODEL_SMOKE"}:
                raise KagglefilesPackError("synthetic or non-real smoke return cannot be imported")
            _require_active_profile(runtime, role="00C2")
            provider = str(runtime.get("provider"))
            if provider not in PROVIDERS:
                raise KagglefilesPackError("00C2 provider is unknown")
            canonical = f"00C2_{provider}_real_model_smoke.zip"
            destination = ROOT / "data/runtime" / canonical
            return_type = f"00C2_REAL_MODEL_SMOKE:{provider}"
        else:
            runtime = json_payloads.get("runtime_manifest.json")
            validation = (
                json_payloads.get("validation_report.json")
                or json_payloads.get("global_validation_report.json")
            )
            if not isinstance(runtime, dict) or not isinstance(validation, dict):
                raise KagglefilesPackError("return type is ambiguous or lacks runtime validation")
            if validation.get("passed") is not True:
                raise KagglefilesPackError("return validation report did not pass")
            _require_active_profile(runtime, role="scientific/generation return")
            identity = " ".join(
                str(runtime.get(key, "")) for key in ("study", "run_tag", "provider")
            ).lower()
            if "confirm" in identity:
                lane, local_lane = "confirmatory", "specificity_confirmatory_cvpr"
            elif "main" in identity:
                lane, local_lane = "main", "main_study_cvpr"
            elif "second" in identity or "coco" in identity:
                lane, local_lane = "coco", "second_domain_cvpr"
            else:
                raise KagglefilesPackError("return study identity is ambiguous")
            provider = str(runtime.get("provider", ""))
            generation_aliases = {"controls", "main_study", "coco_object_presence"}
            if provider in generation_aliases or "global_validation_report.json" in payloads:
                canonical = f"{lane}_generation_return.zip"
                return_type = f"GENERATION:{lane}"
            else:
                if provider not in PROVIDERS:
                    raise KagglefilesPackError("scientific provider identity is unknown")
                canonical = f"{lane}_{PROVIDERS[provider]['short']}_return.zip"
                return_type = f"SCIENTIFIC:{lane}:{provider}"
            destination = ROOT / "local_inputs/provider_returns" / local_lane / canonical
    return {
        "return_type": return_type,
        "canonical_filename": canonical,
        "destination": str(destination),
        "sha256": digest,
        "size": source.stat().st_size,
        "runtime_profile_id": ACTIVE_PROFILE,
        "paper_evidence": False,
    }


def import_kaggle_return(
    path: str | Path,
    *,
    pack_root: str | Path = DEFAULT_PACK_ROOT,
    dry_run: bool = False,
) -> dict[str, Any]:
    source = Path(path).resolve()
    identity = identify_kaggle_return(source, pack_root=pack_root)
    destination = Path(str(identity["destination"]))
    ledger_path = Path(pack_root) / ".IMPORTED_RETURNS.json"
    ledger = (
        json.loads(ledger_path.read_text())
        if ledger_path.is_file()
        else {"schema": "certvic.kagglefiles.imported_returns.v1", "returns": {}}
    )
    if identity["sha256"] in ledger.get("returns", {}):
        raise KagglefilesPackError("replayed return hash was already imported")
    if destination.is_file():
        if _sha(destination) == identity["sha256"]:
            raise KagglefilesPackError("replayed return already exists at the canonical destination")
        raise KagglefilesPackError("canonical destination already contains different bytes")
    if dry_run:
        return {**identity, "status": "DRY_RUN_AUTHENTICATED_NOT_IMPORTED", "next_command": "bash kagglefiles/run_local_resume.sh"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        if _sha(temporary) != identity["sha256"]:
            raise KagglefilesPackError("copy changed return bytes")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    ledger.setdefault("returns", {})[str(identity["sha256"])] = {
        "return_type": identity["return_type"],
        "canonical_destination": str(destination),
        "size": identity["size"],
        "paper_evidence": False,
    }
    _write(ledger_path, _json_bytes(ledger))
    return {
        **identity,
        "status": "AUTHENTICATED_RETURN_IMPORTED_UNCHANGED",
        "next_command": "bash kagglefiles/run_local_resume.sh",
    }


def refresh_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh the unified CertVIC Kaggle operator pack")
    parser.add_argument("--pack-root", default=str(DEFAULT_PACK_ROOT))
    parser.add_argument("--no-rebuild-common", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--determinism-check", action="store_true")
    parser.add_argument("--pytest-summary")
    parser.add_argument("--notebook-summary")
    args = parser.parse_args(argv)
    if args.check:
        result = verify_pack(args.pack_root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 2
    first = build_operator_pack(
        args.pack_root,
        rebuild_common=not args.no_rebuild_common,
        pytest_summary=args.pytest_summary,
        notebook_summary=args.notebook_summary,
    )
    if args.determinism_check:
        before = {
            path.relative_to(args.pack_root).as_posix(): _sha(path)
            for path in Path(args.pack_root).rglob("*") if path.is_file()
            and path.name != ".IMPORTED_RETURNS.json"
        }
        second = build_operator_pack(
            args.pack_root,
            rebuild_common=not args.no_rebuild_common,
            pytest_summary=args.pytest_summary,
            notebook_summary=args.notebook_summary,
        )
        after = {
            path.relative_to(args.pack_root).as_posix(): _sha(path)
            for path in Path(args.pack_root).rglob("*") if path.is_file()
            and path.name != ".IMPORTED_RETURNS.json"
        }
        first["deterministic_rebuild"] = {
            "byte_identical": before == after,
            "first_fingerprint": first["deterministic_portion_sha256"],
            "second_fingerprint": second["deterministic_portion_sha256"],
        }
        if before != after:
            print(json.dumps(first, indent=2, sort_keys=True))
            return 2
    print(json.dumps(first, indent=2, sort_keys=True))
    return 0


def import_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Authenticate and import one Kaggle return")
    parser.add_argument("return_zip")
    parser.add_argument("--pack-root", default=str(DEFAULT_PACK_ROOT))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = import_kaggle_return(
            args.return_zip, pack_root=args.pack_root, dry_run=args.dry_run
        )
    except (KagglefilesPackError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({
            "status": "RETURN_IMPORT_REJECTED",
            "error": str(error),
            "paper_evidence": False,
        }, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"NEXT: {result['next_command']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("refresh")
    subparsers.add_parser("verify")
    subparsers.add_parser("import-return")
    args, remaining = parser.parse_known_args(argv)
    if args.command == "refresh":
        return refresh_main(remaining)
    if args.command == "verify":
        result = verify_pack()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 2
    return import_main(remaining)


if __name__ == "__main__":
    raise SystemExit(main())
