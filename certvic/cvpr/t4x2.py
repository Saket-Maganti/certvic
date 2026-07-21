"""Deterministic two-T4 orchestration, sharding, seed, fallback, and resume contracts."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


SEED_SCHEMA = "certvic.kaggle.seed_manifest.v1"
EXPECTED_ACCELERATOR = "NVIDIA T4"
OOM_FALLBACK_LADDER = (
    "REDUCE_BATCH_SIZE",
    "SWITCH_TO_APPROVED_ATTENTION_IMPLEMENTATION",
    "USE_CONSERVATIVE_DTYPE_AND_CONFIG",
    "SINGLE_GPU_SEQUENTIAL_FALLBACK",
    "STOP_AND_REPORT",
)


class T4x2Error(RuntimeError):
    """The accelerator, seed, shard, or worker contract is invalid."""


@dataclass(frozen=True)
class AcceleratorPlan:
    mode: str
    gpu_ids: tuple[int, ...]
    device_names: tuple[str, ...]
    parallel_workers: int
    sequential_shards: bool
    expected_shards: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "certvic.kaggle.t4x2_plan.v1",
            "mode": self.mode,
            "gpu_ids": list(self.gpu_ids),
            "device_names": list(self.device_names),
            "parallel_workers": self.parallel_workers,
            "sequential_shards": self.sequential_shards,
            "expected_shards": self.expected_shards,
            "oom_fallback_ladder": list(OOM_FALLBACK_LADDER),
            "paper_evidence": False,
        }


def _torch_inventory() -> list[str]:
    try:
        import torch
    except ImportError:
        return []
    if not torch.cuda.is_available():
        return []
    return [str(torch.cuda.get_device_name(index)) for index in range(torch.cuda.device_count())]


def detect_topology(
    *,
    device_names: Sequence[str] | None = None,
    allow_single_t4: bool = True,
    require_exact_t4: bool = True,
    logical_shards: int = 2,
) -> AcceleratorPlan:
    """Return the only permitted topology or fail before any model load."""
    names = tuple(device_names if device_names is not None else _torch_inventory())
    if not names:
        raise T4x2Error("KAGGLE_GPU_00_ZERO_GPU_FAIL_BEFORE_MODEL_LOAD")
    unexpected = [name for name in names if EXPECTED_ACCELERATOR.lower() not in name.lower()]
    if unexpected and require_exact_t4:
        raise T4x2Error(f"KAGGLE_GPU_01_UNEXPECTED_ACCELERATOR: {unexpected}")
    if len(names) > 2:
        raise T4x2Error(f"KAGGLE_GPU_02_UNEXPECTED_GPU_COUNT: {len(names)}")
    if len(names) == 2:
        return AcceleratorPlan(
            mode="T4X2_DUAL_SHARD_PARALLEL",
            gpu_ids=(0, 1),
            device_names=names,
            parallel_workers=2,
            sequential_shards=False,
            expected_shards=logical_shards,
        )
    if not allow_single_t4:
        raise T4x2Error("KAGGLE_GPU_03_SINGLE_T4_FALLBACK_DISABLED")
    return AcceleratorPlan(
        mode="SINGLE_T4_VALIDATED_SEQUENTIAL_FALLBACK",
        gpu_ids=(0,),
        device_names=names,
        parallel_workers=1,
        sequential_shards=True,
        expected_shards=logical_shards,
    )


def _seed(parent: int | str, level: str, identity: str) -> int:
    payload = f"certvic.seed.v1\0{parent}\0{level}\0{identity}".encode("utf-8")
    # Keep values accepted by NumPy, Torch, and Python random while retaining 63 bits.
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & ((1 << 63) - 1)


def derive_seed_manifest(
    *,
    global_seed: int,
    study: str,
    provider: str,
    gpu_id: int,
    shard_id: int,
    task_ids: Iterable[str],
    attempts: int = 1,
) -> dict[str, Any]:
    """Derive the full prospective hierarchy without reading any outcome."""
    if global_seed < 0 or gpu_id < 0 or shard_id < 0 or attempts < 1:
        raise T4x2Error("seed inputs must be non-negative and attempts must be positive")
    global_value = _seed(global_seed, "global", str(global_seed))
    study_value = _seed(global_value, "study", study)
    provider_value = _seed(study_value, "provider", provider)
    gpu_value = _seed(provider_value, "gpu", str(gpu_id))
    shard_value = _seed(gpu_value, "shard", str(shard_id))
    tasks: dict[str, Any] = {}
    observed: set[int] = {global_value, study_value, provider_value, gpu_value, shard_value}
    for task_id in sorted(set(str(value) for value in task_ids)):
        task_value = _seed(shard_value, "task", task_id)
        attempt_values = [
            _seed(task_value, "generation_attempt", str(attempt)) for attempt in range(attempts)
        ]
        if task_value in observed or any(value in observed for value in attempt_values) or (
            len(set(attempt_values)) != len(attempt_values)
        ):
            raise T4x2Error("KAGGLE_SEED_01_COLLISION_DETECTED")
        observed.update([task_value, *attempt_values])
        tasks[task_id] = {
            "task_seed": task_value,
            "generation_attempt_seeds": attempt_values,
        }
    return {
        "schema": SEED_SCHEMA,
        "algorithm": "sha256_namespaced_63bit_v1",
        "global_seed_input": global_seed,
        "global_seed": global_value,
        "study": study,
        "study_seed": study_value,
        "provider": provider,
        "provider_seed": provider_value,
        "gpu_id": gpu_id,
        "gpu_seed": gpu_value,
        "shard_id": shard_id,
        "shard_seed": shard_value,
        "tasks": tasks,
        "collision_check": "PASS",
        "prospective": True,
        "paper_evidence": False,
    }


def write_seed_manifest(path: str | Path, manifest: Mapping[str, Any]) -> Path:
    if manifest.get("schema") != SEED_SCHEMA or manifest.get("collision_check") != "PASS":
        raise T4x2Error("refusing to write invalid seed manifest")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(dict(manifest), indent=2, sort_keys=True) + "\n")
    return destination


def assign_shards(item_ids: Iterable[str], *, num_shards: int = 2) -> dict[int, list[str]]:
    if num_shards < 1:
        raise T4x2Error("num_shards must be positive")
    result = {index: [] for index in range(num_shards)}
    for item_id in sorted(set(str(value) for value in item_ids)):
        shard = int.from_bytes(hashlib.sha256(item_id.encode("utf-8")).digest()[:8], "big") % num_shards
        result[shard].append(item_id)
    return result


def shard_is_complete(
    path: str | Path,
    *,
    expected_ids: Iterable[str],
    id_key: str = "item_id",
) -> bool:
    source = Path(path)
    if not source.is_file():
        return False
    try:
        rows = [json.loads(line) for line in source.read_text().splitlines() if line]
    except (OSError, json.JSONDecodeError):
        return False
    observed = [str(row.get(id_key, "")) for row in rows]
    expected = sorted(set(str(value) for value in expected_ids))
    return len(observed) == len(set(observed)) and sorted(observed) == expected


def launch_workers(
    plan: AcceleratorPlan,
    commands: Mapping[int, Sequence[str]],
    *,
    log_dir: str | Path,
    runner: Callable[..., Any] = subprocess.Popen,
) -> list[dict[str, Any]]:
    """Launch two pinned processes or run both logical shards sequentially on one T4."""
    if set(commands) != set(range(plan.expected_shards)):
        raise T4x2Error("worker command set does not cover the deterministic shard plan")
    root = Path(log_dir)
    root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    if plan.mode == "T4X2_DUAL_SHARD_PARALLEL":
        active = []
        for shard, gpu in enumerate(plan.gpu_ids):
            stdout = (root / f"shard_{shard}.stdout.log").open("w")
            stderr = (root / f"shard_{shard}.stderr.log").open("w")
            environment = {**os.environ, "CUDA_VISIBLE_DEVICES": str(gpu)}
            process = runner(list(commands[shard]), env=environment, stdout=stdout, stderr=stderr)
            active.append((shard, gpu, process, stdout, stderr))
        for shard, gpu, process, stdout, stderr in active:
            exit_code = int(process.wait())
            stdout.close()
            stderr.close()
            records.append({"shard": shard, "gpu": gpu, "exit_code": exit_code})
    else:
        for shard in range(plan.expected_shards):
            stdout = (root / f"shard_{shard}.stdout.log").open("w")
            stderr = (root / f"shard_{shard}.stderr.log").open("w")
            environment = {**os.environ, "CUDA_VISIBLE_DEVICES": "0"}
            process = runner(list(commands[shard]), env=environment, stdout=stdout, stderr=stderr)
            exit_code = int(process.wait())
            stdout.close()
            stderr.close()
            records.append({"shard": shard, "gpu": 0, "exit_code": exit_code})
            if exit_code:
                break
    failures = [row for row in records if row["exit_code"]]
    if failures:
        raise T4x2Error(f"KAGGLE_WORKER_01_SHARD_FAILURE: {failures}")
    return records
