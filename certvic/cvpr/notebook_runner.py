"""Execute notebooks through nbclient with injection, logs, and clean-output guarantees."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import shutil
import tempfile
import traceback
from pathlib import Path
from typing import Any

from certvic.cvpr.ceiling_common import atomic_json, repository_root, sha256_file


class NotebookRunnerError(RuntimeError):
    """Notebook execution or artifact collection failed."""


def _imports() -> tuple[Any, Any, Any]:
    try:
        import nbformat
        from nbclient import NotebookClient
        from nbclient.exceptions import CellExecutionError
    except ImportError as error:  # pragma: no cover - environment-dependent
        raise NotebookRunnerError("nbclient and nbformat are required for notebook execution") from error
    return nbformat, NotebookClient, CellExecutionError


def _load_config(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    source = Path(path)
    if source.suffix.lower() == ".json":
        value = json.loads(source.read_text(encoding="utf-8"))
    else:
        import yaml

        value = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise NotebookRunnerError("injected notebook config must be a mapping")
    return value


def _clear_outputs(notebook: Any) -> Any:
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    return notebook


def _execute_synthetic_fallback(
    notebook_path: Path,
    output_dir: Path,
    *,
    config: dict[str, Any],
    workdir: Path,
) -> dict[str, Any]:
    """Execute synthetic proof cells when the optional Jupyter engine is unavailable."""
    if config.get("synthetic") is not True and config.get("synthetic_fixture") is not True:
        raise NotebookRunnerError(
            "in-process fallback is restricted to explicit synthetic proof notebooks"
        )
    try:
        import nbformat
    except ImportError as error:  # pragma: no cover - nbformat is a project optional dependency
        raise NotebookRunnerError("nbformat is required for synthetic notebook proof") from error
    output_dir.mkdir(parents=True, exist_ok=True)
    notebook = nbformat.read(notebook_path, as_version=4)
    notebook.cells.insert(0, nbformat.v4.new_code_cell(
        "import json\nCERTVIC_CONFIG = json.loads(" + repr(json.dumps(config, sort_keys=True)) + ")",
        metadata={"tags": ["certvic-injected-config"]},
    ))
    namespace: dict[str, Any] = {"__name__": "__certvic_synthetic_notebook__"}
    failure: dict[str, Any] | None = None
    prior = Path.cwd()
    try:
        os.chdir(workdir)
        execution_count = 0
        for index, cell in enumerate(notebook.cells):
            if cell.cell_type != "code":
                continue
            execution_count += 1
            cell.execution_count = execution_count
            stdout = io.StringIO()
            stderr = io.StringIO()
            try:
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    exec(compile(cell.source, f"{notebook_path.name}:cell-{index}", "exec"), namespace)
            except Exception as error:
                failure = {
                    "error_code": "SYNTHETIC_CELL_EXECUTION_FAILED",
                    "cell_index": index,
                    "message": f"{type(error).__name__}: {error}\n{traceback.format_exc()}"[-4000:],
                }
                cell.outputs = [nbformat.v4.new_output(
                    "error",
                    ename=type(error).__name__,
                    evalue=str(error),
                    traceback=traceback.format_exc().splitlines(),
                )]
                break
            outputs = []
            if stdout.getvalue():
                outputs.append(nbformat.v4.new_output("stream", name="stdout", text=stdout.getvalue()))
            if stderr.getvalue():
                outputs.append(nbformat.v4.new_output("stream", name="stderr", text=stderr.getvalue()))
            cell.outputs = outputs
    finally:
        os.chdir(prior)
    executed_path = output_dir / "executed.ipynb"
    nbformat.write(notebook, executed_path)
    cleaned_path = output_dir / "cleaned.ipynb"
    nbformat.write(_clear_outputs(nbformat.from_dict(json.loads(nbformat.writes(notebook)))), cleaned_path)
    artifacts: list[dict[str, Any]] = []
    for pattern in config.get("artifact_globs", []):
        if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise NotebookRunnerError(f"unsafe artifact pattern: {pattern}")
        for artifact in sorted(workdir.glob(pattern)):
            if artifact.is_file():
                target = output_dir / "artifacts" / artifact.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(artifact, target)
                artifacts.append({
                    "name": target.name,
                    "size": target.stat().st_size,
                    "sha256": sha256_file(target),
                })
    report = {
        "schema": "certvic.cvpr.notebook_execution.v1",
        "status": "PASS" if failure is None else "FAIL",
        "source_sha256": sha256_file(notebook_path),
        "config": config,
        "cell_logs": [{
            "cell_index": index,
            "execution_count": cell.get("execution_count"),
            "output_count": len(cell.get("outputs", [])),
            "failed": any(output.get("output_type") == "error" for output in cell.get("outputs", [])),
        } for index, cell in enumerate(notebook.cells) if cell.cell_type == "code"],
        "failure": failure,
        "artifacts": artifacts,
        "cleaned_notebook_sha256": sha256_file(cleaned_path),
        "actual_execution_engine": "IN_PROCESS_PYTHON_SYNTHETIC_FALLBACK",
        "paper_evidence": False,
    }
    atomic_json(output_dir / "execution_report.json", report)
    return report


def execute_notebook(
    notebook_path: str | Path,
    output_dir: str | Path,
    *,
    config: dict[str, Any] | None = None,
    timeout: int = 600,
    workdir: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(notebook_path).resolve()
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    execution_root = Path(workdir).resolve() if workdir else source.parent
    try:
        nbformat, notebook_client, cell_execution_error = _imports()
    except NotebookRunnerError:
        return _execute_synthetic_fallback(
            source,
            destination,
            config=dict(config or {}),
            workdir=execution_root,
        )
    notebook = nbformat.read(source, as_version=4)
    injected = dict(config or {})
    if injected:
        cell = nbformat.v4.new_code_cell(
            "import json\nCERTVIC_CONFIG = json.loads(" + repr(json.dumps(injected, sort_keys=True)) + ")",
            metadata={"tags": ["certvic-injected-config"]},
        )
        notebook.cells.insert(0, cell)
    failure: dict[str, Any] | None = None
    try:
        client = notebook_client(
            notebook,
            timeout=timeout,
            kernel_name="python3",
            resources={"metadata": {"path": str(execution_root)}},
            allow_errors=False,
        )
        client.execute()
    except cell_execution_error as error:
        failed_index = next(
            (
                index
                for index, cell in enumerate(notebook.cells)
                if cell.cell_type == "code" and any(
                    output.get("output_type") == "error" for output in cell.get("outputs", [])
                )
            ),
            None,
        )
        failure = {
            "error_code": "NOTEBOOK_CELL_EXECUTION_FAILED",
            "cell_index": failed_index,
            "message": str(error)[-4000:],
        }
    except Exception as error:  # pragma: no cover - kernel/environment boundary
        failure = {
            "error_code": "NOTEBOOK_EXECUTION_ENGINE_FAILED",
            "cell_index": None,
            "message": f"{type(error).__name__}: {error}"[-4000:],
        }

    executed_path = destination / "executed.ipynb"
    nbformat.write(notebook, executed_path)
    cleaned_path = destination / "cleaned.ipynb"
    nbformat.write(_clear_outputs(nbformat.from_dict(json.loads(nbformat.writes(notebook)))), cleaned_path)
    cell_logs = []
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            cell_logs.append({
                "cell_index": index,
                "execution_count": cell.get("execution_count"),
                "output_count": len(cell.get("outputs", [])),
                "failed": any(
                    output.get("output_type") == "error" for output in cell.get("outputs", [])
                ),
            })
    artifacts: list[dict[str, Any]] = []
    for pattern in injected.get("artifact_globs", []):
        if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise NotebookRunnerError(f"unsafe artifact pattern: {pattern}")
        for artifact in sorted(execution_root.glob(pattern)):
            if artifact.is_file():
                target = destination / "artifacts" / artifact.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(artifact, target)
                artifacts.append({
                    "name": target.name,
                    "size": target.stat().st_size,
                    "sha256": sha256_file(target),
                })
    report = {
        "schema": "certvic.cvpr.notebook_execution.v1",
        "status": "PASS" if failure is None else "FAIL",
        "source_sha256": sha256_file(source),
        "config": injected,
        "cell_logs": cell_logs,
        "failure": failure,
        "artifacts": artifacts,
        "cleaned_notebook_sha256": sha256_file(cleaned_path),
        "actual_execution_engine": "nbclient",
        "paper_evidence": False,
    }
    atomic_json(destination / "execution_report.json", report)
    return report


SYNTHETIC_ROUTES = (
    "00A",
    "00B",
    "00C2_qwen",
    "00C2_internvl",
    "00C2_llava",
    "confirmatory_generation",
    "scientific_provider",
    "post_run",
)


def execute_synthetic_suite(output_dir: str | Path, *, timeout: int = 120) -> dict[str, Any]:
    nbformat, _, _ = _imports()
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="certvic_notebook_proof_") as temporary:
        root = Path(temporary)
        for route in SYNTHETIC_ROUTES:
            route_root = root / route
            route_root.mkdir()
            notebook_path = route_root / f"{route}.ipynb"
            notebook = nbformat.v4.new_notebook(cells=[
                nbformat.v4.new_code_cell(
                    "from pathlib import Path\n"
                    "import json\n"
                    "assert CERTVIC_CONFIG['synthetic'] is True\n"
                    "Path('proof.json').write_text(json.dumps({"
                    f"'route': {route!r}, 'paper_evidence': False"
                    "}, sort_keys=True) + '\\n', encoding='utf-8')"
                )
            ])
            nbformat.write(notebook, notebook_path)
            result = execute_notebook(
                notebook_path,
                destination / route,
                config={"synthetic": True, "route": route, "artifact_globs": ["proof.json"]},
                timeout=timeout,
                workdir=route_root,
            )
            rows.append({"route": route, "status": result["status"], "failure": result["failure"]})
    suite = {
        "schema": "certvic.cvpr.synthetic_notebook_suite.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "routes": rows,
        "actual_execution_engine": "nbclient",
        "paper_evidence": False,
    }
    atomic_json(destination / "synthetic_suite_report.json", suite)
    return suite


def _kaggle_proof_routes() -> list[dict[str, str]]:
    from certvic.cvpr.notebook_builder import NOTEBOOKS, expected_return_zip

    routes: list[dict[str, str]] = []
    for notebook_name, (stage, configured_provider) in NOTEBOOKS.items():
        providers = [configured_provider]
        for provider in providers:
            return_zip = expected_return_zip(notebook_name, stage, provider).format(
                PROVIDER=provider
            )
            routes.append({
                "notebook": notebook_name,
                "stage": stage,
                "provider": provider,
                "return_zip": return_zip,
                "route": f"{Path(notebook_name).stem}__{provider}",
            })
    routes.append({
        "notebook": "POST_RUN_TRANSACTIONAL_HANDOFF",
        "stage": "post_run",
        "provider": "all",
        "return_zip": "post_run_handoff_proof.zip",
        "route": "post_run_transactional_handoff",
    })
    return routes


def execute_kaggle_runbook_suite(
    output_dir: str | Path,
    *,
    notebook_root: str | Path | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    """Execute 21 CPU proof routes covering all 20 canonical runbooks and handoff."""
    try:
        import nbformat
    except ImportError as error:  # pragma: no cover
        raise NotebookRunnerError("nbformat is required for Kaggle runbook proof") from error
    from certvic.cvpr.ceiling_common import atomic_json
    from certvic.cvpr.notebook_builder import build_suite

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(notebook_root) if notebook_root else repository_root() / "notebooks/kaggle/cvpr"
    build_suite(root)
    results: list[dict[str, Any]] = []
    proof_source = '''from pathlib import Path
import hashlib
import json
import zipfile
from certvic.cvpr.t4x2 import assign_shards, derive_seed_manifest, detect_topology
from certvic.cvpr.content_discovery import discover_authenticated_input

cfg = CERTVIC_CONFIG
mounted = discover_authenticated_input(
    "SYNTHETIC_ZERO_EDIT_MOUNT", roots=cfg["fixture_input_root"],
    materialization_root=cfg["fixture_working_root"],
)
assert mounted["discovery_policy"] == "CONTENT_AUTHENTICATED_ANY_LOCATION"
assert mounted["owner_binding_required"] is False
assert Path(mounted["observed_dataset_folder"]).resolve() == Path(
    cfg["observed_dataset_folder"]
).resolve()
dual = detect_topology(device_names=["NVIDIA T4", "NVIDIA T4"]).as_dict()
single = detect_topology(device_names=["NVIDIA T4"]).as_dict()
tasks = [f"synthetic-{index}" for index in range(4)]
assignment = assign_shards(tasks, num_shards=2)
seed = derive_seed_manifest(global_seed=12013, study=cfg["stage"], provider=cfg["provider"],
                            gpu_id=0, shard_id=0, task_ids=tasks, attempts=2)
members = {
    "predictions_or_generated_artifacts.jsonl": "".join(json.dumps({"item_id": item,
        "synthetic_fixture": True, "paper_evidence": False}, sort_keys=True) + "\\n" for item in tasks).encode(),
    "runtime_manifest.json": json.dumps({"schema": "certvic.kaggle.synthetic_runtime.v1",
        "notebook_sha256": cfg["notebook_sha256"], "dual_gpu": dual,
        "single_gpu_fallback": single, "synthetic_fixture": True, "paper_evidence": False},
        sort_keys=True).encode() + b"\\n",
    "environment_manifest.json": json.dumps({"network_used": False, "internet_disabled": True,
        "synthetic_fixture": True, "paper_evidence": False}, sort_keys=True).encode() + b"\\n",
    "snapshot_manifest.json": json.dumps({"provider": cfg["provider"], "model_bytes": False,
        "synthetic_fixture": True, "paper_evidence": False}, sort_keys=True).encode() + b"\\n",
    "task_bundle_manifest.json": json.dumps({"tasks": tasks, "assignment": assignment,
        "synthetic_fixture": True, "paper_evidence": False}, sort_keys=True).encode() + b"\\n",
    "seed_manifest.json": json.dumps(seed, sort_keys=True).encode() + b"\\n",
    "validation_report.json": json.dumps({"passed": True, "canonical_return": cfg["return_zip"],
        "synthetic_fixture": True, "paper_evidence": False}, sort_keys=True).encode() + b"\\n",
    "authorization_proof.json": json.dumps({"execution_class": "SYNTHETIC_NOTEBOOK_PROOF_ONLY",
        "synthetic_fixture": True, "paper_evidence": False}, sort_keys=True).encode() + b"\\n",
    "logs.txt": b"CPU synthetic proof; no GPU/model/scientific execution.\\n",
    "resume_state.json": json.dumps({"complete_shards": [0, 1], "synthetic_fixture": True,
        "paper_evidence": False}, sort_keys=True).encode() + b"\\n",
}
members["hash_manifest.json"] = json.dumps({"files": {name: hashlib.sha256(payload).hexdigest()
    for name, payload in sorted(members.items())}, "paper_evidence": False}, sort_keys=True).encode() + b"\\n"
with zipfile.ZipFile(cfg["return_zip"], "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for name, payload in sorted(members.items()):
        info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, payload)
Path("seed_manifest.json").write_bytes(members["seed_manifest.json"])
print({"status": "SYNTHETIC_RUNBOOK_PROOF_PASSED", "return_zip": cfg["return_zip"]})
'''
    with tempfile.TemporaryDirectory(prefix="certvic_kaggle_runbook_proof_") as temporary:
        proof_root = Path(temporary)
        for route_index, route in enumerate(_kaggle_proof_routes()):
            canonical = root / route["notebook"]
            if route["stage"] == "post_run":
                canonical_hash = hashlib.sha256(b"POST_RUN_TRANSACTIONAL_HANDOFF").hexdigest()
            else:
                canonical_hash = sha256_file(canonical)
                notebook = json.loads(canonical.read_text())
                text = "".join("".join(cell.get("source", [])) for cell in notebook["cells"])
                required = ["paper_evidence", "CANONICAL_RETURN_ZIP"]
                if route["stage"] in {"generation", "evaluation", "real_model_smoke"}:
                    required += ["derive_seed_manifest", "detect_topology"]
                missing = [marker for marker in required if marker not in text]
                if missing:
                    raise NotebookRunnerError(
                        f"canonical runbook is missing proof markers: {route['notebook']}: {missing}"
                    )
            workdir = proof_root / route["route"]
            workdir.mkdir()
            account_index = route_index % 4 + 1
            fixture_input_root = workdir / f"account-{account_index}/input"
            fixture_input = (
                fixture_input_root
                / f"arbitrary-owner-title-{account_index}"
                / "nested"
                / route["route"]
            )
            fixture_input.mkdir(parents=True)
            from certvic.cvpr.kaggle_bundle import build_bundle

            build_bundle(
                fixture_input / ("payload.dat" if route_index % 2 else "opaque-content"),
                {"fixture/mount.json": b'{"synthetic_fixture": true}\n'},
                bundle_type="SYNTHETIC_ZERO_EDIT_MOUNT",
                study="synthetic",
                stage="notebook_proof",
                provider=None,
                required_notebook=route["notebook"],
                dataset_slug="recommended/label-only",
                mount_path="/kaggle/input/recommended-label-only",
                external_dependency_status="SYNTHETIC_FIXTURE",
                evidence_class="SYNTHETIC_FIXTURE",
                builder_command="certvic.cvpr.notebook_runner",
                readme="Synthetic mount-flow proof only.",
            )
            proof_notebook = nbformat.v4.new_notebook(cells=[
                nbformat.v4.new_markdown_cell(
                    f"# Synthetic proof for {route['notebook']}\n\n"
                    "synthetic_fixture=true; paper_evidence=false"
                ),
                nbformat.v4.new_code_cell(proof_source),
            ])
            proof_path = workdir / "proof.ipynb"
            nbformat.write(proof_notebook, proof_path)
            report = execute_notebook(
                proof_path,
                destination / route["route"],
                config={
                    **route,
                    "notebook_sha256": canonical_hash,
                    "fixture_input_root": str(fixture_input_root),
                    "fixture_working_root": str(workdir / "kaggle/working/materialized"),
                    "simulated_account": account_index,
                    "observed_dataset_folder": str(
                        fixture_input_root / f"arbitrary-owner-title-{account_index}"
                    ),
                    "synthetic_fixture": True,
                    "artifact_globs": [route["return_zip"], "seed_manifest.json"],
                },
                timeout=timeout,
                workdir=workdir,
            )
            artifacts = {row["name"]: row for row in report["artifacts"]}
            results.append({
                **route,
                "notebook_sha256": canonical_hash,
                "status": report["status"],
                "return_zip_sha256": artifacts.get(route["return_zip"], {}).get("sha256"),
                "actual_execution_engine": report.get("actual_execution_engine", "nbclient"),
                "failure": report["failure"],
                "synthetic_fixture": True,
                "paper_evidence": False,
            })
    covered = {row["notebook"] for row in results if row["stage"] != "post_run"}
    suite = {
        "schema": "certvic.kaggle.synthetic_runbook_suite.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL",
        "canonical_notebooks_covered": len(covered),
        "executed_routes": len(results),
        "simulated_kaggle_accounts": 4,
        "routes": results,
        "actual_execution_engines": sorted({
            str(row["actual_execution_engine"]) for row in results
        }),
        "synthetic_fixture": True,
        "paper_evidence": False,
    }
    atomic_json(destination / "synthetic_runbook_suite_report.json", suite)
    return suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute a CertVIC notebook with nbclient")
    parser.add_argument("notebook", nargs="?")
    parser.add_argument("--root")
    parser.add_argument("--config")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--workdir")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--synthetic-suite", action="store_true")
    parser.add_argument("--kaggle-runbook-suite", action="store_true")
    args = parser.parse_args(argv)
    base = repository_root(args.root)
    out = Path(args.out_dir)
    if not out.is_absolute():
        out = base / out
    if args.kaggle_runbook_suite:
        result = execute_kaggle_runbook_suite(out, timeout=args.timeout)
    elif args.synthetic_suite:
        result = execute_synthetic_suite(out, timeout=args.timeout)
    else:
        if not args.notebook:
            parser.error("notebook is required unless --synthetic-suite is used")
        notebook = Path(args.notebook)
        if not notebook.is_absolute():
            notebook = base / notebook
        config_path = Path(args.config) if args.config else None
        if config_path is not None and not config_path.is_absolute():
            config_path = base / config_path
        workdir = Path(args.workdir) if args.workdir else None
        if workdir is not None and not workdir.is_absolute():
            workdir = base / workdir
        result = execute_notebook(
            notebook,
            out,
            config=_load_config(config_path),
            timeout=args.timeout,
            workdir=workdir,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
