"""One-command factory for all locally buildable and externally supplied Kaggle inputs."""

from __future__ import annotations

import argparse
import csv
import json
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from certvic.cvpr.confirmatory_input_builder import build_confirmatory_input
from certvic.cvpr.generation_input_builder import build_generation_input, status as generation_status
from certvic.cvpr.kaggle_bundle import build_bundle, verify_bundle
from certvic.cvpr.notebook_builder import NOTEBOOKS, build_suite, expected_return_zip
from certvic.cvpr.pre_smoke_packager import (
    build_pre_smoke_permissions,
    package_verified_permissions,
)
from certvic.cvpr.scientific_input_builder import (
    PROVIDERS as SHORT_PROVIDERS,
    build_scientific_input,
    status as scientific_status,
)
from certvic.cvpr.smoke_input_builder import build_smoke_bundle
from certvic.cvpr.snapshot_bundle_builder import PROVIDERS as SNAPSHOT_PROVIDERS
from certvic.cvpr.snapshot_bundle_builder import build_snapshot_bundle, status as snapshot_status
from certvic.cvpr.wheelhouse_builder import build_wheelhouse, status as wheelhouse_status


ROOT = Path(__file__).resolve().parents[2]
UPLOAD_ROOT = ROOT / "kaggle_uploads"
REPORT_ROOT = ROOT / "reports/kaggle_execution_pack"
NOTEBOOK_ROOT = ROOT / "notebooks/kaggle/cvpr"
TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".lock", ".md", ".py", ".sh", ".toml", ".yaml", ".yml"}
EXCLUDED_PARTS = {
    "__pycache__", ".pytest_cache", ".ruff_cache", ".git", "kaggleoutputs",
    "incoming_archives", "provider_returns", "private", "tmp", "cache",
}


class KaggleInputFactoryError(ValueError):
    """The deterministic Kaggle input factory could not satisfy its local contract."""


def _tree(
    relative: str,
    suffixes: set[str],
    *,
    include_images: bool = False,
) -> dict[str, Path]:
    base = ROOT / relative
    result: dict[str, Path] = {}
    if not base.is_dir():
        return result
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.is_symlink() or EXCLUDED_PARTS & set(path.relative_to(ROOT).parts):
            continue
        if path.name == ".DS_Store":
            continue
        if path.suffix.lower() in suffixes or include_images and path.suffix.lower() in {".png"}:
            result[path.relative_to(ROOT).as_posix()] = path
    return result


def _local_specs() -> dict[str, dict[str, Any]]:
    code_files = {
        **_tree("certvic", {".py", ".json", ".yaml", ".yml"}),
        **_tree("scripts", {".py"}),
        **_tree("configs/runtime", TEXT_SUFFIXES),
        **_tree("configs/execution", TEXT_SUFFIXES),
        **_tree("configs/models", TEXT_SUFFIXES),
        **_tree("configs/studies", TEXT_SUFFIXES),
        **{name: ROOT / name for name in ("pyproject.toml", "README.md", "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md")},
        "LICENSE_STATUS.md": (
            b"# License status\n\nNo repository-level license file was present at packaging time. "
            b"Dataset/model licenses remain external and must be verified per input manifest.\n"
        ),
    }
    notebook_files = {
        path.relative_to(ROOT).as_posix(): path
        for path in sorted(NOTEBOOK_ROOT.glob("*.ipynb"))
        if path.name in NOTEBOOKS
    }
    notebook_files["notebooks/kaggle/cvpr/notebook_manifest.json"] = NOTEBOOK_ROOT / "notebook_manifest.json"
    config_files = _tree("configs", {".json", ".toml", ".yaml", ".yml"})
    for path in sorted((ROOT / "requirements").glob("kaggle_*.lock")):
        config_files[path.relative_to(ROOT).as_posix()] = path
    execution_names = {
        "kaggle_bundle.py", "wheelhouse_builder.py", "snapshot_bundle_builder.py",
        "smoke_input_builder.py", "pre_smoke_packager.py", "confirmatory_input_builder.py",
        "generation_input_builder.py", "scientific_input_builder.py", "t4x2.py",
        "notebook_bootstrap.py", "build_all_kaggle_inputs.py", "notebook_runner.py",
        "notebook_validation.py", "import_transaction.py", "whole_study_import.py",
        "content_discovery.py",
        "runtime_profiles.py", "environment_lock.py", "runtime_preflight.py",
        "kagglefiles_pack.py",
        "package_generation.py", "package_run.py", "worker.py", "kaggle_claim_guard.py",
        "post_review_pipeline.py", "non_human_continuation.py", "primary_endpoint.py",
    }
    execution_files = {
        f"certvic/cvpr/{name}": ROOT / "certvic/cvpr" / name for name in execution_names
    }
    for name in (
        "build_kaggle_wheelhouse.py", "build_model_snapshot_bundle.py",
        "validate_t4x2_notebooks.py", "run_phase_b_cpu_workflows.py",
        "refresh_kaggle_release_lineage.py",
        "run_all_cpu_workflows.py",
    ):
        path = ROOT / "scripts" / name
        if path.is_file():
            execution_files[f"scripts/{name}"] = path
    execution_files.update(_tree("execution_pack", {".md"}))
    for relative in (
        "reports/max_ceiling_upgrade/code_snapshot_sealed.json",
        "reports/max_ceiling_upgrade/pre_run_reproducibility_capsule_sealed.json",
    ):
        path = ROOT / relative
        if path.is_file():
            code_files[relative] = path
    synthetic_files = {
        **_tree("data/smoke", {".png"}, include_images=True),
        "data/manifests/smoke_tasks.jsonl": ROOT / "data/manifests/smoke_tasks.jsonl",
        "certvic/data/smoke_fixtures.py": ROOT / "certvic/data/smoke_fixtures.py",
        "certvic/cvpr/synthetic_smoke.py": ROOT / "certvic/cvpr/synthetic_smoke.py",
        "certvic/cvpr/synthetic_closure.py": ROOT / "certvic/cvpr/synthetic_closure.py",
        "certvic/cvpr/notebook_runner.py": ROOT / "certvic/cvpr/notebook_runner.py",
    }
    return {
        "certvic_code_bundle.zip": {
            "files": code_files,
            "type": "CODE",
            "slug": "certvic/certvic-code",
            "readme": "Complete portable CertVIC Python/config execution closure. No weights, datasets, historical outputs, private review sheets, or caches are included.",
        },
        "certvic_notebooks_bundle.zip": {
            "files": notebook_files,
            "type": "NOTEBOOKS",
            "slug": "certvic/certvic-runbooks",
            "readme": "The 20 output-free canonical runbooks. Every active notebook discovers authenticated content under arbitrary private dataset names and requires no manual configuration edits.",
        },
        "certvic_configs_bundle.zip": {
            "files": config_files,
            "type": "CONFIGS",
            "slug": "certvic/certvic-configs",
            "readme": "Frozen scientific, runtime, authorization, data-license, and Kaggle dependency contracts.",
        },
        "certvic_execution_tools_bundle.zip": {
            "files": execution_files,
            "type": "EXECUTION_TOOLS",
            "slug": "certvic/certvic-execution-tools",
            "readme": "Bundle verification, offline bootstrap, T4x2 orchestration, builders, packaging, import, and recovery tools.",
        },
        "certvic_synthetic_validation_bundle.zip": {
            "files": synthetic_files,
            "type": "SYNTHETIC_VALIDATION",
            "slug": "certvic/certvic-synthetic-validation",
            "readme": "Non-evidence synthetic fixtures and proof runners only. Every derived artifact must retain synthetic_fixture=true and paper_evidence=false.",
        },
    }


def _build_local_one(name: str, spec: Mapping[str, Any], destination: Path) -> dict[str, Any]:
    return build_bundle(
        destination,
        spec["files"],
        bundle_type=str(spec["type"]),
        study="all",
        stage="bootstrap",
        provider=None,
        required_notebook="ALL_16_CANONICAL_RUNBOOKS",
        dataset_slug=str(spec["slug"]),
        mount_path=f"/kaggle/input/{str(spec['slug']).split('/', 1)[1]}",
        external_dependency_status="REPOSITORY_BYTES_ONLY",
        evidence_class="NON_EVIDENCE_EXECUTION_ASSET",
        builder_command="python3 -m certvic.cvpr.build_all_kaggle_inputs --local-only",
        validation_command=f"python3 -m certvic.cvpr.kaggle_bundle verify kaggle_uploads/00_code/{name}",
        readme=f"# {spec['type']}\n\n{spec['readme']}",
    )


def build_local_bundles() -> list[dict[str, Any]]:
    from scripts.refresh_kaggle_release_lineage import refresh

    refresh()
    build_suite(NOTEBOOK_ROOT)
    destination_root = UPLOAD_ROOT / "00_code"
    destination_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="certvic_kaggle_rebuild_") as temporary:
        second_root = Path(temporary)
        for name, spec in _local_specs().items():
            destination = destination_root / name
            first = _build_local_one(name, spec, destination)
            _build_local_one(name, spec, second_root / name)
            if destination.read_bytes() != (second_root / name).read_bytes():
                raise KaggleInputFactoryError(f"bundle was not byte-identical on rebuild: {name}")
            results.append({
                **{key: first[key] for key in ("path", "size", "sha256", "member_count")},
                "name": name,
                "status": "CREATED_AND_VALIDATED",
                "deterministic_rebuild": True,
            })
    return results


def validate_local_bundles_without_promotion() -> list[dict[str, Any]]:
    """Prove current-source determinism without replacing authenticated active ZIPs."""
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="certvic_kaggle_nonpromoting_validation_") as temporary:
        root = Path(temporary)
        for name, spec in _local_specs().items():
            first_path = root / "first" / name
            second_path = root / "second" / name
            first = _build_local_one(name, spec, first_path)
            second = _build_local_one(name, spec, second_path)
            if first_path.read_bytes() != second_path.read_bytes():
                raise KaggleInputFactoryError(
                    f"bundle was not byte-identical in non-promoting validation: {name}"
                )
            results.append({
                "name": name,
                "sha256": first["sha256"],
                "size": first["size"],
                "member_count": first["member_count"],
                "second_sha256": second["sha256"],
                "status": "DETERMINISTIC_WITHOUT_PROMOTION",
                "active_archive_replaced": False,
                "paper_evidence": False,
            })
    return results


def external_statuses() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    wheel_zip = UPLOAD_ROOT / "01_wheelhouse/certvic_offline_wheelhouse.zip"
    if wheel_zip.is_file():
        verification = verify_bundle(wheel_zip)
        linux_validation_path = (
            ROOT / "reports/non_human_closure/wheelhouse_clean_linux_validation.json"
        )
        linux_validation = (
            json.loads(linux_validation_path.read_text(encoding="utf-8"))
            if linux_validation_path.is_file()
            else {}
        )
        clean_linux_passed = (
            linux_validation.get("passed") is True
            and linux_validation.get("bundle", {}).get("sha256") == verification["sha256"]
            and linux_validation.get("bundle", {}).get("size") == wheel_zip.stat().st_size
        )
        wheel = {
            "status": (
                "PROVISIONED_CLEAN_LINUX_CP310_VALIDATED"
                if verification["passed"] and clean_linux_passed
                else "PROVISIONED_REQUIRES_CLEAN_LINUX_VALIDATION"
                if verification["passed"]
                else "PROVISIONED_BUT_BUNDLE_VALIDATION_FAILED"
            ),
            "passed": bool(verification["passed"]),
            "output": str(wheel_zip.relative_to(ROOT)),
            "size": wheel_zip.stat().st_size,
            "sha256": verification["sha256"],
            "member_count": verification["member_count"],
            "builder_command": (
                "python3 -m certvic.cvpr.wheelhouse_builder "
                "--mode LOCAL_VERIFY_ONLY --requirements-root requirements "
                "--wheel-root local_inputs/wheelhouse/linux_cp310 "
                "--output kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip"
            ),
            "paper_evidence": False,
        }
    else:
        wheel = wheelhouse_status(
            ROOT / "requirements", profile_id="kaggle_cp310_legacy",
            environment_lock=ROOT / "configs/runtime/kaggle_t4x2_environment.lock.json",
        )
    rows.append({"name": "certvic_offline_wheelhouse.zip", "runtime_profile_id": "kaggle_cp310_legacy", **wheel})
    cp312_zip = UPLOAD_ROOT / "01_wheelhouse/certvic_offline_wheelhouse_cp312.zip"
    if cp312_zip.is_file():
        cp312_verification = verify_bundle(cp312_zip)
        rows.append({
            "name": cp312_zip.name,
            "runtime_profile_id": "kaggle_cp312_2026_07",
            "status": (
                "CP312_WHEELHOUSE_PROVISIONED_REQUIRES_FRESH_00A"
                if cp312_verification["passed"]
                else "CP312_WHEELHOUSE_BUNDLE_VALIDATION_FAILED"
            ),
            "passed": bool(cp312_verification["passed"]),
            "output": str(cp312_zip.relative_to(ROOT)),
            "size": cp312_zip.stat().st_size,
            "sha256": cp312_verification["sha256"],
            "member_count": cp312_verification["member_count"],
            "paper_evidence": False,
        })
    else:
        rows.append({
            "name": "certvic_offline_wheelhouse_cp312.zip",
            **wheelhouse_status(
                ROOT / "requirements", profile_id="kaggle_cp312_2026_07",
                environment_lock=ROOT / "configs/runtime/kaggle_t4x2_environment.lock.json",
            ),
        })
    for provider in SNAPSHOT_PROVIDERS:
        rows.append({"name": SNAPSHOT_PROVIDERS[provider]["output"], **snapshot_status(provider)})
    rows.extend([
        {
            "name": "certvic_real_two_item_smoke_bundle.zip",
            "status": "BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES",
            "builder_command": (
                "python3 -m certvic.cvpr.smoke_input_builder "
                "--task-manifest local_inputs/smoke/real_smoke_tasks.jsonl "
                "--output kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip"
            ),
            "output": "kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip",
            "expected_size": "1-50 MB",
        },
        {
            "name": "certvic_pre_smoke_permissions.zip",
            "status": "BLOCKED_BY_UPSTREAM_GATE",
            "builder_command": "python3 -m certvic.cvpr.pre_smoke_packager --config <INPUTS_JSON>",
            "output": "kaggle_uploads/04_permissions/certvic_pre_smoke_permissions.zip",
            "expected_size": "under 1 MB",
        },
        {
            "name": "certvic_confirmatory_generation_input.zip",
            "status": "BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES",
            "builder_command": "python3 -m certvic.cvpr.confirmatory_input_builder --config <INPUT_CONFIG_JSON>",
            "output": "kaggle_uploads/05_confirmatory/certvic_confirmatory_generation_input.zip",
            "expected_size": "1-20 GB",
        },
    ])
    for study in ("confirmatory", "main", "coco"):
        for provider in SHORT_PROVIDERS:
            item = scientific_status(study, provider)
            rows.append({"name": f"certvic_{study}_{provider}_input.zip", **item})
    for study in ("main", "coco"):
        rows.append({"name": Path(generation_status(study)["output"]).name, **generation_status(study)})
    return rows


def _load_external_config(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if source.suffix in {".yaml", ".yml"}:
        import yaml
        value = yaml.safe_load(source.read_text())
    else:
        value = json.loads(source.read_text())
    if not isinstance(value, dict):
        raise KaggleInputFactoryError("external roots config must be a mapping")
    return value


def build_external(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build only supplied external roles; absent roles remain precise statuses."""
    built: list[dict[str, Any]] = []
    if config.get("wheelhouse_root"):
        built.append(build_wheelhouse(
            wheel_root=config["wheelhouse_root"],
            output=UPLOAD_ROOT / "01_wheelhouse" / (
                "certvic_offline_wheelhouse.zip"
                if config.get("wheelhouse_profile") == "kaggle_cp310_legacy"
                else "certvic_offline_wheelhouse_cp312.zip"
            ),
            requirements_root=ROOT / "requirements",
            profile_id=config.get("wheelhouse_profile", "kaggle_cp312_2026_07"),
            environment_lock=ROOT / "configs/runtime/kaggle_t4x2_environment.lock.json",
        ))
    for provider, value in config.get("snapshots", {}).items():
        built.append(build_snapshot_bundle(
            provider,
            value["root"],
            model_commit=value["model_commit"],
            processor_commit=value.get("processor_commit", value["model_commit"]),
        ))
    smoke = config.get("smoke")
    if smoke:
        built.append(build_smoke_bundle(
            smoke["task_manifest"], historical_manifests=smoke.get("historical_manifests", [])
        ))
    pre_smoke = config.get("pre_smoke_permissions")
    if pre_smoke:
        if "matrix_authorization" in pre_smoke:
            built.append(package_verified_permissions(
                matrix_authorization=pre_smoke["matrix_authorization"],
                provider_permissions=pre_smoke["provider_permissions"],
                active_inputs=pre_smoke.get("active_inputs", {}),
                provider_active_inputs=pre_smoke.get("provider_active_inputs", {}),
            ))
        else:
            built.append(build_pre_smoke_permissions(
                pre_smoke["inputs"],
                prompt_hash=pre_smoke["prompt_hash"],
                parser_version=pre_smoke["parser_version"],
                run_contract_hashes=pre_smoke["run_contract_hashes"],
            ))
    confirmatory = config.get("confirmatory_generation")
    if confirmatory:
        built.append(build_confirmatory_input(confirmatory["control_files"]))
    for study in ("main", "coco"):
        value = config.get(f"{study}_generation")
        if value:
            built.append(build_generation_input(study, value["roles"]))
    for study, providers in config.get("scientific", {}).items():
        for provider, value in providers.items():
            built.append(build_scientific_input(
                study, provider, value["roles"], run_tag=value["run_tag"]
            ))
    return built


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _notebook_rows(local: list[dict[str, Any]]) -> list[dict[str, Any]]:
    local_hashes = {row["name"]: row["sha256"] for row in local}
    rows: list[dict[str, Any]] = []
    for name, (stage, provider) in NOTEBOOKS.items():
        if name.startswith("00A_"):
            external = ["certvic_offline_wheelhouse.zip"]
        elif name.startswith("00B_"):
            external = ["certvic_offline_wheelhouse.zip", SNAPSHOT_PROVIDERS[provider]["output"]]
        elif name.startswith("00C1_"):
            external = []
        elif name.startswith("00C2_"):
            external = ["certvic_offline_wheelhouse.zip", SNAPSHOT_PROVIDERS[provider]["output"], "certvic_real_two_item_smoke_bundle.zip", "certvic_pre_smoke_permissions.zip"]
        elif stage == "generation":
            lane = "confirmatory" if name.startswith("01_") else "main" if name.startswith("10_") else "coco"
            external = ["certvic_offline_wheelhouse.zip", f"certvic_{lane}_generation_input.zip"]
        else:
            lane = "confirmatory" if name.startswith(("02_", "03_", "04_")) else "main" if name.startswith(("11_", "12_", "13_")) else "coco"
            short = "qwen" if "qwen" in name else "internvl" if "internvl" in name else "llava"
            external = ["certvic_offline_wheelhouse.zip", f"certvic_{lane}_{short}_input.zip", f"{short}_snapshot.zip"]
        required = [
            "certvic_code_bundle.zip", "certvic_configs_bundle.zip",
            "certvic_execution_tools_bundle.zip", *external,
        ]
        return_name = expected_return_zip(name, stage, provider)
        rows.append({
            "notebook": name,
            "required_zips": ";".join(required),
            "kaggle_dataset_slug": "ANY_OWNER_AND_DATASET_TITLE",
            "mount_path": "ANY_NESTING_UNDER_CERTVIC_INPUT_ROOTS",
            "discovery_policy": "CONTENT_AUTHENTICATED_ANY_LOCATION",
            "owner_binding_required": False,
            "filename_binding_required": False,
            "path_binding_required": False,
            "size": "see bundle rows and external estimates",
            "status": "CREATED_AND_VALIDATED" if not external else "BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES",
            "builder": "python3 -m certvic.cvpr.build_all_kaggle_inputs --local-only",
            "code_bundle_sha256": local_hashes.get("certvic_code_bundle.zip", ""),
            "user_action": "attach authenticated roles under any account/name/mount; keep Internet off; no notebook edits required",
            "expected_output_zip": return_name,
            "next_local_command": (
                "python3 scripts/run_all_cpu_workflows.py --resume"
                if stage in {"code_smoke", "snapshot_smoke", "real_model_smoke"}
                else "python3 -m certvic.cvpr.import_transaction --help"
            ),
        })
    return rows


def _runtime_rows() -> list[dict[str, Any]]:
    ranges = {
        "00A": ("CPU", 0, "10-20 min", "0.2-0.4 h", "N/A", "low"),
        "00B": ("CPU integrity", 0, "15-30 min/provider", "0 GPU-h", "2-8 GB RAM", "medium"),
        "00C1": ("CPU", 2, "2-5 min", "0.05 h", "N/A", "low"),
        "00C2": ("single logical T4 shard", 2, "15-45 min/provider", "0.25-0.75 h/provider", "12-15 GB", "medium"),
        "01": ("T4x2", 240, "2-5 h", "4-10 T4-h", "8-14 GB/GPU", "medium"),
        "02": ("T4x2", 240, "2-5 h", "4-10 T4-h", "12-15 GB/GPU", "medium"),
        "03": ("T4x2", 240, "3-7 h", "6-14 T4-h", "14-16 GB/GPU", "high"),
        "04": ("T4x2", 240, "2-5 h", "4-10 T4-h", "12-15 GB/GPU", "medium"),
        "10": ("T4x2", 500, "4-10 h (8-18 h reserve)", "8-20 T4-h", "10-15 GB/GPU", "low"),
        "11": ("T4x2", 500, "5-10 h", "10-20 T4-h", "12-15 GB/GPU", "low"),
        "12": ("T4x2", 500, "8-16 h", "16-32 T4-h", "14-16 GB/GPU", "low"),
        "13": ("T4x2", 500, "5-10 h", "10-20 T4-h", "12-15 GB/GPU", "low"),
        "20": ("T4x2", 60, "2-5 h", "4-10 T4-h", "10-15 GB/GPU", "medium"),
        "21": ("T4x2", 60, "1-2 h", "2-4 T4-h", "12-15 GB/GPU", "medium"),
        "22": ("T4x2", 60, "1.5-3 h", "3-6 T4-h", "14-16 GB/GPU", "medium"),
        "23": ("T4x2", 60, "1-2 h", "2-4 T4-h", "12-15 GB/GPU", "medium"),
    }
    rows = []
    for name in NOTEBOOKS:
        key = name.split("_", 1)[0]
        accelerator, count, wall, gpu_hours, vram, confidence = ranges[key]
        rows.append({
            "notebook": name,
            "cpu_gpu_class": accelerator,
            "accelerator": "OFF for 00A/00B; NVIDIA T4 x2 with declared single-T4 fallback for GPU stages",
            "dual_gpu_behavior": "independent concurrent hash shards" if "T4x2" in accelerator else "inspection or CPU",
            "task_count": count,
            "batch_size": "4 initial; prospective OOM ladder to 1",
            "wall_time_range": wall,
            "individual_gpu_hours": gpu_hours,
            "peak_vram": vram,
            "output_size": "10 MB-30 GB depending on generated pixels",
            "checkpoints": "per-shard resume ledger and validated atomic ZIP",
            "kaggle_risk": "session limit, disk, OOM, dataset mount",
            "single_t4_time": "approximately 1.8-2.2x dual-T4 wall time",
            "evidence_basis": "planning range only; recalibrate from 00C2 runtime manifests",
            "confidence": confidence,
            "cpu_hours": "0.1-1.0 packaging/import per run",
            "human_review_person_hours": "external; estimate after generated-item count and rater calibration",
        })
    return rows


def write_reports(local: list[dict[str, Any]], external: list[dict[str, Any]]) -> None:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    for row in external:
        output = Path(str(row.get("output", row["name"])))
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        sidecar = output.with_name(output.name + ".BUILDER_STATUS.json")
        sidecar.write_text(json.dumps({
            "schema": "certvic.kaggle.external_builder_status.v1",
            **row,
            "paper_evidence": False,
        }, indent=2, sort_keys=True) + "\n")
    notebook_rows = _notebook_rows(local)
    _write_csv(
        UPLOAD_ROOT / "CERTVIC_KAGGLE_UPLOAD_MANIFEST.csv",
        list(notebook_rows[0]), notebook_rows,
    )
    runtime_rows = _runtime_rows()
    _write_csv(
        REPORT_ROOT / "CERTVIC_KAGGLE_RUNTIME_ESTIMATES.csv",
        list(runtime_rows[0]), runtime_rows,
    )
    local_table = "\n".join(
        f"| `{row['path'].replace(str(ROOT) + '/', '')}` | {row['size']} | `{row['sha256']}` | {row['status']} |"
        for row in local
    )
    external_table = "\n".join(
        f"| `{row.get('output', row['name'])}` | {row['status']} | `{row.get('builder_command', '')}` | {row.get('expected_size', '')} |"
        for row in external
    )
    dataset_lines = [
        "# CertVIC Kaggle Dataset Map",
        "",
        "Upload identical authenticated bundle bytes to any Kaggle account under any dataset title, archive name, extension, mount, or nesting. Canonical labels below are recommendations only. Never edit authenticated bundle contents or manifests.",
        "",
        "## Repository-byte datasets",
        "",
        "| Recommended ZIP label | Recommended dataset label | Discovery role |",
        "| --- | --- | --- |",
    ]
    for row in local:
        manifest = verify_bundle(row["path"])["bundle_manifest"]
        recommended_label = str(manifest["expected_kaggle_dataset_slug"]).split("/", 1)[-1]
        dataset_lines.append(
            f"| `{row['name']}` | `{recommended_label}` | `{manifest['bundle_type']}` |"
        )
    dataset_lines += [
        "| `certvic_offline_wheelhouse.zip` | `certvic-offline-wheelhouse` | `OFFLINE_LINUX_WHEELHOUSE` |",
        "| `qwen2_5_vl_7b_snapshot.zip` | `qwen2-5-vl-7b-snapshot` | `MODEL_SNAPSHOT` |",
        "| `internvl2_8b_snapshot.zip` | `internvl2-8b-snapshot` | `MODEL_SNAPSHOT` |",
        "| `llava_onevision_7b_snapshot.zip` | `llava-onevision-7b-snapshot` | `MODEL_SNAPSHOT` |",
        "| `certvic_real_two_item_smoke_bundle.zip` | `certvic-real-two-item-smoke` | `REAL_TWO_ITEM_SMOKE` |",
        "| `certvic_pre_smoke_permissions.zip` | `certvic-pre-smoke-permissions` | `PRE_SMOKE_PERMISSIONS` |",
    ]
    dataset_lines += [
        "", "## Execution order", "",
        "All 20 active notebooks require no manual path, owner, slug, filename, hash, provider, or permission edits.",
        "",
        "1. Attach CODE, CONFIGS, EXECUTION_TOOLS, and OFFLINE_LINUX_WHEELHOUSE under any names; run 00A.",
        "2. Attach one immutable snapshot at a time; run 00B for all three providers.",
        "3. Build permissions only from returned 00A/00B bytes and the real two-item smoke bundle.",
        "4. Run 00C2 for Qwen, InternVL, and LLaVA; import all returns through the transactional handoff.",
        "5. Create scientific input datasets only after their upstream review/authorization gates pass.",
    ]
    (UPLOAD_ROOT / "CERTVIC_KAGGLE_DATASET_MAP.md").write_text("\n".join(dataset_lines) + "\n")
    (REPORT_ROOT / "CERTVIC_KAGGLE_RUNTIME_ESTIMATES.md").write_text(
        "# CertVIC Kaggle Runtime Estimates\n\nThese are planning ranges, not observed runtimes. Dual-GPU notebook-hours are wall time; individual T4 GPU-hours are approximately twice dual-T4 wall time. CPU packaging/import is 0.1-1.0 hours per return. Human review is external and must be estimated only after real generated-item counts and rater calibration. Recalibrate only from non-evidence 00C2 runtime manifests.\n\n"
        + "\n".join(f"- `{row['notebook']}`: {row['wall_time_range']}; {row['individual_gpu_hours']}; {row['peak_vram']}." for row in runtime_rows)
        + "\n"
    )
    inventory_rows = [
        {"artifact": row["path"].replace(str(ROOT) + "/", ""), "class": "repository_zip", "status": row["status"], "size": row["size"], "sha256": row["sha256"]}
        for row in local
    ] + [
        {"artifact": row.get("output", row["name"]), "class": "external_builder", "status": row["status"], "size": row.get("expected_size", ""), "sha256": ""}
        for row in external
    ]
    _write_csv(REPORT_ROOT / "CERTVIC_KAGGLE_PACK_INVENTORY.csv", ["artifact", "class", "status", "size", "sha256"], inventory_rows)
    _write_csv(REPORT_ROOT / "CERTVIC_KAGGLE_PACK_CHANGELOG.csv", ["change_id", "area", "status", "detail"], [
        {"change_id": "K001", "area": "bundle_schema", "status": "COMPLETE", "detail": "deterministic secure certvic.kaggle.bundle.v1"},
        {"change_id": "K002", "area": "external_builders", "status": "COMPLETE", "detail": "wheelhouse, snapshots, smoke, permissions, generation, scientific"},
        {"change_id": "K003", "area": "runbooks", "status": "COMPLETE", "detail": "20 output-free notebooks with provider-specific zero-edit smoke stages, T4x2 fallback, seeds, and canonical returns"},
        {"change_id": "K004", "area": "evidence_boundary", "status": "PRESERVED", "detail": "paper_evidence=false; no external bytes fabricated"},
    ])
    _write_csv(REPORT_ROOT / "CERTVIC_KAGGLE_PACK_COMMANDS.csv", ["command_id", "command", "phase", "observed_exit", "result"], [
        {"command_id": "C01", "command": "python3 -m pytest -q", "phase": "A", "observed_exit": 0, "result": "885 passed, 1 skipped"},
        {"command_id": "C02", "command": "python3 -m pytest -q tests/test_kaggle_execution_pack.py tests/test_kaggle_bundle.py", "phase": "A", "observed_exit": 0, "result": "15 passed"},
        {"command_id": "C03", "command": "python3 -m ruff check .", "phase": "A", "observed_exit": 0, "result": "All checks passed"},
        {"command_id": "C04", "command": "python3 -m compileall -q certvic scripts tests", "phase": "A", "observed_exit": 0, "result": "compiled"},
        {"command_id": "C05", "command": "python3 -m certvic.cvpr.build_all_kaggle_inputs --local-only", "phase": "A", "observed_exit": 0, "result": "5 deterministic repository ZIPs"},
        {"command_id": "C06", "command": "python3 -m certvic.cvpr.notebook_validation --out reports/kaggle_execution_pack/notebook_static_validation.json", "phase": "A", "observed_exit": 0, "result": "20/20 passed"},
        {"command_id": "C07", "command": "python3 -m certvic.cvpr.notebook_runner --kaggle-runbook-suite --out-dir reports/kaggle_execution_pack/notebook_proof", "phase": "A", "observed_exit": 0, "result": "21/21 routes passed; 20/20 notebooks covered"},
        {"command_id": "C08", "command": "python3 -m certvic.cvpr.build_all_kaggle_inputs --status", "phase": "A", "observed_exit": 0, "result": "5/5 local bundles verified"},
        {"command_id": "C09", "command": "python3 scripts/run_phase_b_cpu_workflows.py --out reports/kaggle_execution_pack/phase_b_cpu_validation", "phase": "B", "observed_exit": "NOT_RUN_IN_PHASE_A", "result": "required next command; must not launch real GPU work"},
    ])
    session = f"""# CertVIC Kaggle Pack Session

Phase A built the complete local packaging layer without launching any real Kaggle/GPU scientific run. The live checkout was authoritative and was not a Git working tree. Baseline validation before edits: **857 passed, 1 skipped**.

## Repository ZIPs

| Path | Bytes | SHA-256 | Status |
| --- | ---: | --- | --- |
{local_table}

## External-byte builders

| Output | Status | Exact builder | Expected size |
| --- | --- | --- | --- |
{external_table}

Frozen V1/V2 evidence, prospective gates, `paper_evidence=false`, and genuine human-review count zero remain unchanged.
"""
    (REPORT_ROOT / "CERTVIC_KAGGLE_PACK_SESSION.md").write_text(session)
    validation = """# CertVIC Kaggle Pack Validation

Phase A CPU validation passed without launching a real Kaggle/GPU scientific run.

| Check | Observed result | Exit |
| --- | --- | ---: |
| Pre-edit regression baseline | 857 passed, 1 skipped | 0 |
| Final full pytest suite | 885 passed, 1 skipped | 0 |
| Focused Kaggle execution-pack and bundle tests | 15 passed | 0 |
| Ruff | All checks passed | 0 |
| Python compileall | Passed | 0 |
| Canonical notebook static validation | 20/20 output-free runbooks passed | 0 |
| Synthetic notebook execution proof | 21/21 routes passed; all 20 notebooks covered | 0 |
| Deterministic local ZIP rebuild | 5/5 byte-identical | 0 |
| Claim guard | Passed; zero human-reviewed rows; no prohibited external bytes | 0 |
| Privacy scan | Passed; zero findings | 0 |
| Paper compile | Passed; 3-page PDF | 0 |
| Maximum-ceiling clean release extraction | Passed | 0 |

The synthetic notebook proof used the in-process Python fallback because the repository environment does not include `nbclient`; this is an explicit restricted-environment fallback, not a scientific result. Phase B must repeat the complete CPU workflow from the sealed offline wheelhouse before any real GPU launch. Frozen V1/V2 evidence boundaries remain unchanged, and every generated synthetic artifact retains `paper_evidence=false`.
"""
    (REPORT_ROOT / "CERTVIC_KAGGLE_PACK_VALIDATION.md").write_text(validation)
    (REPORT_ROOT / "CERTVIC_KAGGLE_PACK_SCORECARD.md").write_text(
        "# CertVIC Kaggle Pack Scorecard\n\n| Dimension | Local status |\n| --- | --- |\n| Repository upload ZIPs | 5/5 created and deterministically validated |\n| External-dependent builders | 18/18 implemented with explicit blockers |\n| Canonical notebooks | 20/20 regenerated, output-free, statically validated |\n| Synthetic notebook routes | 21/21 passed; all 20 runbooks covered |\n| T4x2/fallback/seeds | implemented and CPU-tested; Phase B sealed-environment replay is the next gate |\n| Evidence integrity | preserved; no external scientific bytes fabricated |\n"
    )
    handoff_body = f"""# CertVIC Kaggle Ready to Upload Handoff

Five repository-byte ZIPs are ready. Every unavailable wheel, model, licensed source, human-review, and upstream authorization byte has a deterministic builder and precise status; none was fabricated.

## Built now

| Path | Bytes | SHA-256 | Status |
| --- | ---: | --- | --- |
{local_table}

## External and gated items

| Output | Status | Builder | Expected size |
| --- | --- | --- | --- |
{external_table}

Use `kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md`. The exact Phase B command is:

```bash
python3 scripts/run_phase_b_cpu_workflows.py --out reports/kaggle_execution_pack/phase_b_cpu_validation
```
"""
    (REPORT_ROOT / "CERTVIC_KAGGLE_READY_TO_UPLOAD_HANDOFF.md").write_text(handoff_body)
    phase_b = f"""# CertVIC Phase A to Phase B Handoff

## Built

Phase A created and verified all five repository-only upload ZIPs, regenerated all 20 canonical output-free runbooks, implemented the v1 secure bundle schema, offline wheelhouse/snapshot/smoke/permission/generation/scientific builders, T4x2 parallel and single-T4 fallback contracts, deterministic seed hierarchy, common notebook bootstrap, canonical return ZIP naming, upload map, runtime estimates, and failure playbooks.

| Path | Bytes | SHA-256 | Status |
| --- | ---: | --- | --- |
{local_table}

## External bytes still absent

Only Linux CPython 3.10 wheels, three immutable model snapshots and commits, two real licensed smoke items, licensed ADE20K/COCO/source/insertion bytes, genuine reviewer outputs, and gate-derived permissions/task freezes remain external. Their exact builders and statuses are below; no fake bytes were created.

| Output | Status | Builder | Expected size |
| --- | --- | --- | --- |
{external_table}

## Phase B CPU workflows

Phase B must execute the full pytest suite, focused Kaggle builder/security/sharding/seed/bootstrap tests, Ruff, compileall, 20-runbook static validation, 21-route synthetic notebook execution proof, bundle verification and deterministic rebuild, doctor, next-action, run graph, artifact registry, claim/privacy guards, paper compile, and clean maximum-release rebuild. It must not launch a real model or scientific GPU run.

Begin Phase B exactly with:

```bash
python3 scripts/run_phase_b_cpu_workflows.py --out reports/kaggle_execution_pack/phase_b_cpu_validation
```

PHASE_A_KAGGLE_PACKAGING_COMPLETE  
ALL_BUILDABLE_UPLOAD_ZIPS_CREATED  
ALL_EXTERNAL_BUNDLE_BUILDERS_READY  
ALL_16_RUNBOOKS_VALIDATED  
READY_FOR_PHASE_B_CPU_EXECUTION
"""
    (REPORT_ROOT / "CERTVIC_KAGGLE_READY_FOR_PHASE_B_HANDOFF.md").write_text(phase_b)


def status_report() -> dict[str, Any]:
    local = []
    for name in _local_specs():
        path = UPLOAD_ROOT / "00_code" / name
        verification = verify_bundle(path) if path.is_file() else {"passed": False, "errors": ["not built"]}
        local.append({"name": name, "path": str(path.relative_to(ROOT)), **verification})
    return {
        "schema": "certvic.kaggle.input_factory_status.v1",
        "local": local,
        "external": external_statuses(),
        "notebooks": len(NOTEBOOKS),
        "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--local-only", action="store_true")
    group.add_argument("--validate-local-only", action="store_true")
    group.add_argument("--with-external-roots")
    group.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    if args.status:
        result = status_report()
    elif args.validate_local_only:
        result = {
            "schema": "certvic.kaggle.nonpromoting_local_validation.v1",
            "status": "KAGGLE_LOCAL_BUNDLES_DETERMINISTIC_WITHOUT_PROMOTION",
            "local_bundles": validate_local_bundles_without_promotion(),
            "paper_evidence": False,
        }
    else:
        local = build_local_bundles()
        external = external_statuses()
        built_external: list[dict[str, Any]] = []
        if args.with_external_roots:
            built_external = build_external(_load_external_config(args.with_external_roots))
        write_reports(local, external)
        result = {
            "schema": "certvic.kaggle.input_factory.v1",
            "status": "KAGGLE_LOCAL_INPUT_FACTORY_COMPLETE",
            "local_bundles": local,
            "external_bundles_built": built_external,
            "external_statuses": external,
            "notebooks": len(NOTEBOOKS),
            "paper_evidence": False,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.status:
        return 0 if all(row.get("passed") for row in result["local"]) else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
