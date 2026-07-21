"""Checkpointed, fail-closed orchestration for CertVIC CPU-only workflows.

The orchestrator intentionally treats absent external bytes, Kaggle returns, and genuine
human review as resumable blockers.  It never launches a GPU workload and never promotes
synthetic fixtures to scientific evidence.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import resource
import shlex
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAN = ROOT / "configs/execution/certvic_cpu_run_plan.yaml"
REPORT_ROOT = ROOT / "reports/cpu_execution"
CHECKPOINT = REPORT_ROOT / "cpu_execution_checkpoint.json"
ALLOWED_STATUSES = {
    "COMPLETED",
    "ALREADY_VALID",
    "BLOCKED_BY_EXTERNAL_BYTES",
    "BLOCKED_BY_GPU_OUTPUT",
    "BLOCKED_BY_GENUINE_HUMAN_REVIEW",
    "BLOCKED_BY_UPSTREAM_GATE",
    "FAILED_LOCAL_REPAIR_REQUIRED",
}
SUCCESS_STATUSES = {"COMPLETED", "ALREADY_VALID"}
BLOCKED_STATUSES = ALLOWED_STATUSES - SUCCESS_STATUSES - {"FAILED_LOCAL_REPAIR_REQUIRED"}
BLOCKER_STATUS = {
    "external_bytes": "BLOCKED_BY_EXTERNAL_BYTES",
    "gpu_output": "BLOCKED_BY_GPU_OUTPUT",
    "genuine_human_review": "BLOCKED_BY_GENUINE_HUMAN_REVIEW",
    "upstream_gate": "BLOCKED_BY_UPSTREAM_GATE",
}
GPU_MARKERS = (
    "cuda", "kaggle notebook", "nvidia", "torchrun", "accelerator launch",
    "diffusion generation", "vlm inference",
)


class CPUExecutionError(ValueError):
    """The CPU run plan or a local execution violated the orchestration contract."""


@dataclass(frozen=True)
class RunNode:
    run_id: str
    category: str
    command: str
    prerequisites: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    expected_runtime: str
    memory_class: str
    retry_policy: str
    evidence_class: str
    blocker_policy: str
    producer_stage: str
    next_action: str
    cpu_io_class: str
    always_run: bool = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _inventory(paths: Iterable[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for raw in paths:
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT / path
        if path.is_file():
            result[_relative(path)] = {"size": path.stat().st_size, "sha256": _sha256(path)}
        else:
            result[_relative(path)] = {"missing": True}
    return result


def _outputs_valid(node: RunNode) -> bool:
    return bool(node.outputs) and all((ROOT / value).is_file() for value in node.outputs)


def _load_plan(path: str | Path = DEFAULT_PLAN) -> list[RunNode]:
    source = Path(path)
    value = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != "certvic.cvpr.cpu_run_plan.v1":
        raise CPUExecutionError("CPU run plan schema mismatch")
    rows = value.get("nodes")
    if not isinstance(rows, list) or not rows:
        raise CPUExecutionError("CPU run plan contains no nodes")
    nodes: list[RunNode] = []
    seen: set[str] = set()
    required = {
        "run_id", "category", "command", "prerequisites", "inputs", "outputs",
        "expected_runtime", "memory_class", "retry_policy", "evidence_class",
        "blocker_policy", "producer_stage", "next_action", "cpu_io_class",
    }
    for row in rows:
        if not isinstance(row, dict) or required - set(row):
            raise CPUExecutionError(f"incomplete CPU run-plan node: {row!r}")
        node = RunNode(
            run_id=str(row["run_id"]),
            category=str(row["category"]),
            command=str(row["command"]),
            prerequisites=tuple(str(item) for item in row["prerequisites"]),
            inputs=tuple(str(item) for item in row["inputs"]),
            outputs=tuple(str(item) for item in row["outputs"]),
            expected_runtime=str(row["expected_runtime"]),
            memory_class=str(row["memory_class"]),
            retry_policy=str(row["retry_policy"]),
            evidence_class=str(row["evidence_class"]),
            blocker_policy=str(row["blocker_policy"]),
            producer_stage=str(row["producer_stage"]),
            next_action=str(row["next_action"]),
            cpu_io_class=str(row["cpu_io_class"]),
            always_run=bool(row.get("always_run", False)),
        )
        if not node.run_id or node.run_id in seen:
            raise CPUExecutionError(f"duplicate or empty run ID: {node.run_id!r}")
        if node.blocker_policy not in {"none", *BLOCKER_STATUS}:
            raise CPUExecutionError(f"unknown blocker policy for {node.run_id}")
        lower_command = node.command.lower()
        if any(marker in lower_command for marker in GPU_MARKERS):
            raise CPUExecutionError(f"GPU-like command prohibited in CPU plan: {node.run_id}")
        unknown = set(node.prerequisites) - seen
        if unknown:
            raise CPUExecutionError(
                f"prerequisites must precede {node.run_id}: {sorted(unknown)}"
            )
        seen.add(node.run_id)
        nodes.append(node)
    return nodes


def _load_checkpoint() -> dict[str, Any]:
    if not CHECKPOINT.is_file():
        return {"schema": "certvic.cvpr.cpu_execution_checkpoint.v1", "runs": {}}
    value = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    if value.get("schema") != "certvic.cvpr.cpu_execution_checkpoint.v1":
        raise CPUExecutionError("CPU checkpoint schema mismatch")
    return value


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _missing_inputs(node: RunNode) -> list[str]:
    return [value for value in node.inputs if not (ROOT / value).exists()]


def _blocked_row(node: RunNode, status: str, reason: str) -> dict[str, Any]:
    now = _utc_now()
    return {
        "run_id": node.run_id,
        "category": node.category,
        "command": node.command,
        "start_utc": now,
        "end_utc": now,
        "wall_seconds": 0.0,
        "cpu_io_class": node.cpu_io_class,
        "memory_class": node.memory_class,
        "peak_memory_mb": None,
        "inputs": _inventory(node.inputs),
        "outputs": _inventory(node.outputs),
        "exit_code": None,
        "status": status,
        "blocker": reason,
        "producer_stage": node.producer_stage,
        "next_action": node.next_action,
        "retry_recovery": node.retry_policy,
        "evidence_class": node.evidence_class,
    }


def _run_command(node: RunNode) -> dict[str, Any]:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = REPORT_ROOT / "logs" / f"{node.run_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    started_wall = time.monotonic()
    started = _utc_now()
    environment = {
        **os.environ,
        "CERTVIC_MAX_CPU_WORKERS": "4",
        "OMP_NUM_THREADS": "4",
        "MKL_NUM_THREADS": "4",
        "TOKENIZERS_PARALLELISM": "false",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "DIFFUSERS_OFFLINE": "1",
        "PIP_NO_INDEX": "1",
        "CUDA_VISIBLE_DEVICES": "",
    }
    command = shlex.split(node.command)
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    elapsed = round(time.monotonic() - started_wall, 3)
    after = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    # macOS reports bytes; Linux reports KiB. This project runs locally on macOS, but retain a
    # conservative cross-platform conversion for test environments.
    peak_mb = round(after / (1024 * 1024), 2) if sys.platform == "darwin" else round(after / 1024, 2)
    log_path.write_text(
        f"$ {node.command}\n\n[stdout]\n{completed.stdout}\n[stderr]\n{completed.stderr}",
        encoding="utf-8",
    )
    outputs = _inventory(node.outputs)
    status = "COMPLETED" if completed.returncode == 0 and _outputs_valid(node) else (
        "FAILED_LOCAL_REPAIR_REQUIRED"
    )
    blocker = ""
    if completed.returncode == 0 and not _outputs_valid(node):
        blocker = "command succeeded but declared output contract is incomplete"
    elif completed.returncode != 0:
        blocker = f"local command exited {completed.returncode}; inspect {_relative(log_path)}"
    return {
        "run_id": node.run_id,
        "category": node.category,
        "command": node.command,
        "start_utc": started,
        "end_utc": _utc_now(),
        "wall_seconds": elapsed,
        "cpu_io_class": node.cpu_io_class,
        "memory_class": node.memory_class,
        "peak_memory_mb": max(peak_mb, 0.0) if after >= before else None,
        "inputs": _inventory(node.inputs),
        "outputs": outputs,
        "exit_code": completed.returncode,
        "status": status,
        "blocker": blocker,
        "producer_stage": node.producer_stage,
        "next_action": node.next_action,
        "retry_recovery": node.retry_policy,
        "evidence_class": node.evidence_class,
        "log": _relative(log_path),
    }


def _already_valid_row(node: RunNode) -> dict[str, Any]:
    row = _blocked_row(node, "ALREADY_VALID", "")
    row["exit_code"] = 0
    return row


def _write_csv(path: Path, rows: list[Mapping[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def _report_rows(nodes: list[RunNode], runs: Mapping[str, dict[str, Any]]) -> None:
    ordered = [runs[node.run_id] for node in nodes if node.run_id in runs]
    plan_rows = [
        {
            "run_id": node.run_id,
            "category": node.category,
            "command": node.command,
            "prerequisites": ";".join(node.prerequisites),
            "inputs": ";".join(node.inputs),
            "outputs": ";".join(node.outputs),
            "expected_runtime": node.expected_runtime,
            "memory_class": node.memory_class,
            "retry_policy": node.retry_policy,
            "evidence_class": node.evidence_class,
            "blocker_policy": node.blocker_policy,
        }
        for node in nodes
    ]
    _write_csv(
        REPORT_ROOT / "CERTVIC_CPU_RUN_PLAN.csv",
        plan_rows,
        list(plan_rows[0]),
    )
    result_fields = [
        "run_id", "category", "start_utc", "end_utc", "wall_seconds", "cpu_io_class",
        "memory_class", "peak_memory_mb", "exit_code", "status", "blocker",
        "producer_stage", "next_action", "retry_recovery", "evidence_class",
    ]
    _write_csv(REPORT_ROOT / "CERTVIC_CPU_RUN_RESULTS.csv", ordered, result_fields)
    _write_csv(
        REPORT_ROOT / "CERTVIC_CPU_RUN_COMMANDS.csv",
        ordered,
        ["run_id", "command", "start_utc", "end_utc", "exit_code", "status", "log"],
    )
    blockers = [row for row in ordered if row["status"] in BLOCKED_STATUSES]
    _write_csv(
        REPORT_ROOT / "CERTVIC_CPU_RUN_BLOCKERS.csv",
        blockers,
        ["run_id", "category", "status", "blocker", "producer_stage", "next_action"],
    )
    _write_csv(
        REPORT_ROOT / "CERTVIC_CPU_RUNTIME_ACTUALS.csv",
        ordered,
        ["run_id", "status", "wall_seconds", "peak_memory_mb", "cpu_io_class", "memory_class"],
    )


def _write_markdown_reports(nodes: list[RunNode], runs: Mapping[str, dict[str, Any]]) -> None:
    ordered = [runs[node.run_id] for node in nodes if node.run_id in runs]
    counts = {status: sum(row["status"] == status for row in ordered) for status in sorted(ALLOWED_STATUSES)}
    failures = counts["FAILED_LOCAL_REPAIR_REQUIRED"]
    terminal = not failures and len(ordered) == len(nodes)
    completed = [row for row in ordered if row["status"] in SUCCESS_STATUSES]
    blockers = [row for row in ordered if row["status"] in BLOCKED_STATUSES]
    session = [
        "# CertVIC CPU Execution Session",
        "",
        f"Generated: `{_utc_now()}`",
        "",
        "This session executed only CPU-safe commands with offline flags and at most four CPU threads. "
        "No GPU inference, diffusion generation, model loading, predictions, or human decisions were fabricated.",
        "",
        "## Counts",
        "",
    ]
    session.extend(f"- `{key}`: {value}" for key, value in counts.items())
    session.extend(["", "## Completed or already valid", ""])
    session.extend(f"- `{row['run_id']}` — {row['status']} ({row['wall_seconds']} s)" for row in completed)
    session.extend(["", "## Resumable blockers", ""])
    session.extend(
        f"- `{row['run_id']}` — {row['status']}: {row['blocker']}. Next: `{row['next_action']}`"
        for row in blockers
    )
    session.extend(["", "`paper_evidence=false`", "", "`genuine human_reviewed=true count=0`", ""])
    (REPORT_ROOT / "CERTVIC_CPU_EXECUTION_SESSION.md").write_text(
        "\n".join(session) + "\n", encoding="utf-8"
    )
    closure = [
        "# CertVIC CPU Closure Validation",
        "",
        f"- Plan nodes: {len(nodes)}",
        f"- Recorded nodes: {len(ordered)}",
        f"- Local failures: {failures}",
        f"- Resumable blockers: {len(blockers)}",
        "- GPU inference executed: no",
        "- Synthetic artifacts promoted to evidence: no",
        "- Paper evidence: false",
        "- Genuine completed human reviews accepted in this phase: 0",
        "- Main execution allowed: false",
        "- COCO execution allowed: false",
        "- V2-30 status: retrospective",
        "",
    ]
    if terminal:
        closure.extend([
            "PHASE_B_ALL_AVAILABLE_CPU_RUNS_COMPLETE",
            "PRE_GPU_CPU_CLOSURE_COMPLETE",
            "FIRST_KAGGLE_WAVE_READY",
        ])
    else:
        closure.append("PHASE_B_LOCAL_REPAIR_REQUIRED")
    (REPORT_ROOT / "CERTVIC_CPU_CLOSURE_VALIDATION.md").write_text(
        "\n".join(closure) + "\n", encoding="utf-8"
    )
    handoff = [
        "# CertVIC CPU Ready for GPU Handoff",
        "",
        "All locally available CPU nodes are complete or precisely blocked by external bytes, GPU returns, genuine human review, or an upstream gate.",
        "",
        "## Resume",
        "",
        "```bash",
        "python3 scripts/run_all_cpu_workflows.py --resume",
        "```",
        "",
        "The first authorized Kaggle wave is defined in `CERTVIC_FIRST_GPU_WAVE_HANDOFF.md`. "
        "00C2 is not authorized by this Phase B handoff.",
        "",
        "## Current external provisioning gate",
        "",
        "Provision the Linux CPython 3.10 wheelhouse and all three immutable snapshot ZIPs, then run 00A and the three isolated 00B validations. Missing external bytes are not local CPU failures.",
        "",
        "## Evidence boundary",
        "",
        "- Frozen V1: Qwen 12/94, InternVL 1/94, LLaVA 3/94.",
        "- Threshold: observed spurious flip rate <= 0.10; Qwen fails V1.",
        "- V2-30 remains retrospective; confirmatory remains prospective and zero-overlap with V1.",
        "- Main and COCO remain blocked; `paper_evidence=false`.",
        "- Genuine `human_reviewed=true` count remains zero for the prospective workflow.",
        "",
    ]
    if terminal:
        handoff.extend([
            "PHASE_B_ALL_AVAILABLE_CPU_RUNS_COMPLETE  ",
            "PRE_GPU_CPU_CLOSURE_COMPLETE  ",
            "FIRST_KAGGLE_WAVE_READY",
        ])
    (REPORT_ROOT / "CERTVIC_CPU_READY_FOR_GPU_HANDOFF.md").write_text(
        "\n".join(handoff) + "\n", encoding="utf-8"
    )


def write_data_inventory() -> None:
    """Generate conservative availability, license, and overlap reports from the registry."""
    source = ROOT / "configs/data/source_license_registry.yaml"
    registry = yaml.safe_load(source.read_text(encoding="utf-8"))
    rows = []
    license_rows = []
    for item in registry.get("sources", []):
        raw_root = str(item.get("local_root", ""))
        local = ROOT / raw_root if raw_root and raw_root != "EXTERNAL_PROVISIONING_REQUIRED" else None
        exists = bool(local and local.exists())
        rows.append({
            "dataset": item.get("dataset"),
            "split": item.get("split"),
            "configured_root": raw_root,
            "local_bytes_present": exists,
            "availability": "AVAILABLE_NON_EVIDENCE" if exists else "EXTERNAL_BYTES_REQUIRED",
            "paper_use": item.get("paper_use"),
            "paper_evidence": False,
        })
        license_rows.append({
            "dataset": item.get("dataset"),
            "split": item.get("split"),
            "verification_status": item.get("verification_status"),
            "redistribution": item.get("redistribution"),
            "image_level_license": item.get("image_level_license"),
            "insertion_asset_license": item.get("insertion_asset_license"),
            "release_inclusion": item.get("release_inclusion"),
            "gate": "PASS_SYNTHETIC_ONLY" if item.get("verification_status") == "VERIFIED" else "FAIL_CLOSED",
        })
    overlap_rows = [
        {
            "source_universe": "CERTVIC_SYNTHETIC_SMOKE",
            "historical_v1_v2_exclusion": "NOT_REAL_MODE",
            "confirmatory_eligible": False,
            "audit_status": "SYNTHETIC_NON_EVIDENCE",
        },
        {
            "source_universe": "ADE20K",
            "historical_v1_v2_exclusion": "REQUIRED_NOT_RUN_WITHOUT_LICENSED_SOURCE_MANIFEST",
            "confirmatory_eligible": False,
            "audit_status": "BLOCKED_BY_EXTERNAL_BYTES",
        },
        {
            "source_universe": "COCO",
            "historical_v1_v2_exclusion": "REQUIRED_NOT_RUN_WITHOUT_LICENSED_SOURCE_MANIFEST",
            "confirmatory_eligible": False,
            "audit_status": "BLOCKED_BY_EXTERNAL_BYTES",
        },
    ]
    _write_csv(REPORT_ROOT / "CERTVIC_DATA_AVAILABILITY.csv", rows, list(rows[0]))
    _write_csv(REPORT_ROOT / "CERTVIC_LICENSE_STATUS.csv", license_rows, list(license_rows[0]))
    _write_csv(
        REPORT_ROOT / "CERTVIC_SOURCE_OVERLAP_AUDIT.csv",
        overlap_rows,
        list(overlap_rows[0]),
    )


def validate_first_wave_returns() -> None:
    """Validate and promote only canonical 00A/00B return metadata from unchanged ZIPs."""
    runtime = ROOT / "data/runtime"
    specifications = [
        (
            "00A_environment_bundle.zip",
            "00A_environment.json",
            "00A_environment_validation.json",
            None,
        ),
        (
            "00B_qwen2_5_vl_7b_snapshot_bundle.zip",
            "00B_qwen2_5_vl_7b_snapshot.json",
            "00B_qwen2_5_vl_7b_snapshot_validation.json",
            "qwen2_5_vl_7b",
        ),
        (
            "00B_internvl_8b_snapshot_bundle.zip",
            "00B_internvl_8b_snapshot.json",
            "00B_internvl_8b_snapshot_validation.json",
            "internvl_8b",
        ),
        (
            "00B_llava_onevision_7b_snapshot_bundle.zip",
            "00B_llava_onevision_7b_snapshot.json",
            "00B_llava_onevision_7b_snapshot_validation.json",
            "llava_onevision_7b",
        ),
    ]
    promoted: list[dict[str, Any]] = []
    staged: dict[Path, bytes] = {}
    for archive_name, primary_name, validation_name, provider in specifications:
        archive_path = runtime / archive_name
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if len(names) != len(set(names)) or archive.testzip() is not None:
                raise CPUExecutionError(f"duplicate or corrupt members in {archive_name}")
            if any(
                PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
                for name in names
            ):
                raise CPUExecutionError(f"unsafe member in {archive_name}")
            required = {primary_name, validation_name, "seed_manifest.json", "hash_manifest.json"}
            if set(names) != required:
                raise CPUExecutionError(
                    f"unexpected member contract in {archive_name}: {sorted(set(names) ^ required)}"
                )
            primary_bytes = archive.read(primary_name)
            validation_bytes = archive.read(validation_name)
            primary = json.loads(primary_bytes)
            validation = json.loads(validation_bytes)
            hashes = json.loads(archive.read("hash_manifest.json"))
            for name, digest in hashes.get("files", {}).items():
                if name not in names or hashlib.sha256(archive.read(name)).hexdigest() != digest:
                    raise CPUExecutionError(f"hash manifest mismatch for {archive_name}:{name}")
            if set(hashes.get("files", {})) != required - {"hash_manifest.json"}:
                raise CPUExecutionError(f"hash manifest coverage mismatch in {archive_name}")
        if primary.get("passed") is not True or validation.get("passed") is not True:
            raise CPUExecutionError(f"failed return cannot be promoted: {archive_name}")
        if primary.get("paper_evidence") is not False or validation.get("paper_evidence") is not False:
            raise CPUExecutionError(f"first-wave return must remain non-evidence: {archive_name}")
        if provider and (primary.get("provider") != provider or validation.get("provider") != provider):
            raise CPUExecutionError(f"provider mismatch in {archive_name}")
        staged[runtime / primary_name] = primary_bytes
        staged[runtime / validation_name] = validation_bytes
        promoted.append({
            "archive": archive_name,
            "sha256": _sha256(archive_path),
            "primary": primary_name,
            "validation": validation_name,
            "provider": provider or "all",
        })
    for destination, payload in staged.items():
        temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, destination)
    _atomic_json(REPORT_ROOT / "first_gpu_wave_return_validation.json", {
        "schema": "certvic.cvpr.first_gpu_wave_return_validation.v1",
        "passed": True,
        "returns": promoted,
        "paper_evidence": False,
        "00c2_authorized": False,
    })


def register_repository_bundles() -> None:
    """Register the five deterministic repository-only Kaggle bundles."""
    from certvic.cvpr.artifact_registry import add_artifact

    registry = ROOT / "reports/max_ceiling_upgrade/artifact_registry.json"
    for name in (
        "certvic_code_bundle.zip",
        "certvic_notebooks_bundle.zip",
        "certvic_configs_bundle.zip",
        "certvic_execution_tools_bundle.zip",
        "certvic_synthetic_validation_bundle.zip",
    ):
        add_artifact(
            registry,
            ROOT / "kaggle_uploads/00_code" / name,
            root=ROOT,
            role=f"kaggle_repository_bundle:{name}",
            schema="certvic.kaggle.bundle_manifest.v1",
            study="all",
            evidence_class="PLANNED_NOT_EXECUTED",
        )


def execute(
    *,
    plan_path: str | Path = DEFAULT_PLAN,
    resume: bool = False,
    only: str | None = None,
) -> dict[str, Any]:
    nodes = _load_plan(plan_path)
    checkpoint = _load_checkpoint() if resume or only else {
        "schema": "certvic.cvpr.cpu_execution_checkpoint.v1", "runs": {}
    }
    runs: dict[str, dict[str, Any]] = checkpoint.setdefault("runs", {})
    known_ids = {node.run_id for node in nodes}
    by_id = {node.run_id: node for node in nodes}
    if only and only not in known_ids:
        raise CPUExecutionError(f"unknown CPU stage: {only}")
    for node in nodes:
        if only and node.run_id != only:
            continue
        prior = runs.get(node.run_id)
        if (
            resume
            and prior
            and prior.get("status") in SUCCESS_STATUSES
            and _outputs_valid(node)
            and not node.always_run
        ):
            continue
        prerequisite_rows = [runs.get(value) for value in node.prerequisites]
        unmet = [
            value for value, row in zip(node.prerequisites, prerequisite_rows, strict=True)
            if (not row or row.get("status") not in SUCCESS_STATUSES)
            and not _outputs_valid(by_id[value])
        ]
        if unmet:
            runs[node.run_id] = _blocked_row(
                node,
                BLOCKER_STATUS.get(node.blocker_policy, "BLOCKED_BY_UPSTREAM_GATE"),
                f"unmet prerequisites: {', '.join(unmet)}",
            )
        else:
            missing = _missing_inputs(node)
            if missing:
                if node.blocker_policy == "none":
                    runs[node.run_id] = _blocked_row(
                        node,
                        "FAILED_LOCAL_REPAIR_REQUIRED",
                        f"required local inputs missing: {', '.join(missing)}",
                    )
                else:
                    runs[node.run_id] = _blocked_row(
                        node,
                        BLOCKER_STATUS[node.blocker_policy],
                        f"missing inputs: {', '.join(missing)}",
                    )
            elif _outputs_valid(node) and not node.always_run:
                runs[node.run_id] = _already_valid_row(node)
            elif not node.command:
                status = BLOCKER_STATUS.get(node.blocker_policy, "FAILED_LOCAL_REPAIR_REQUIRED")
                runs[node.run_id] = _blocked_row(node, status, "prerequisite artifact not available")
            else:
                runs[node.run_id] = _run_command(node)
        checkpoint["updated_at_utc"] = _utc_now()
        checkpoint["runs"] = runs
        _atomic_json(CHECKPOINT, checkpoint)
        if runs[node.run_id]["status"] == "FAILED_LOCAL_REPAIR_REQUIRED":
            break
    _report_rows(nodes, runs)
    _write_markdown_reports(nodes, runs)
    failures = [row for row in runs.values() if row["status"] == "FAILED_LOCAL_REPAIR_REQUIRED"]
    execution_status = (
        "CPU_STAGE_COMPLETE" if only and not failures
        else "PHASE_B_ALL_AVAILABLE_CPU_RUNS_COMPLETE"
        if not failures and len(runs) == len(nodes)
        else "PHASE_B_LOCAL_REPAIR_REQUIRED"
    )
    return {
        "status": execution_status,
        "runs_recorded": len(runs),
        "runs_planned": len(nodes),
        "local_failures": len(failures),
        "checkpoint": _relative(CHECKPOINT),
    }


def status(plan_path: str | Path = DEFAULT_PLAN) -> dict[str, Any]:
    nodes = _load_plan(plan_path)
    checkpoint = _load_checkpoint()
    runs = checkpoint.get("runs", {})
    return {
        "schema": "certvic.cvpr.cpu_execution_status.v1",
        "runs_planned": len(nodes),
        "runs_recorded": len(runs),
        "counts": {
            value: sum(row.get("status") == value for row in runs.values())
            for value in sorted(ALLOWED_STATUSES)
        },
        "next_runnable": next(
            (node.run_id for node in nodes if node.run_id not in runs), None
        ),
        "gpu_commands_launched": False,
        "paper_evidence": False,
    }
