"""Build the remaining CertVIC Kaggle notebooks, bundles, and runbooks.

This is a preparation step only. It creates executable Kaggle/IPYNB runbooks for
the remaining V7 GPU work, deterministic upload bundles, and local ingest docs.
It does not run diffusion or VLM inference and it does not create model results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "dist/kaggle_remaining_runs"
KAGGLE_NB = REPO / "notebooks/kaggle"
RUNBOOKS = REPO / "docs/runbooks"
TOP_ZIP = REPO / "dist/certvic_remaining_kaggle_runbooks.zip"
ZIP_DATE = (2026, 1, 1, 0, 0, 0)

RUN_TAGS = ("spurious", "perception_scaled", "polarity", "mechanism")
CONTROL_TAGS = {"spurious", "perception_scaled"}
DIAGNOSTIC_TAGS = {"polarity", "mechanism"}
PROVIDERS = {
    "qwen2_5_vl_7b": {
        "title": "Qwen2.5-VL-7B",
        "repo_id": "Qwen/Qwen2.5-VL-7B-Instruct",
        "cache": "/kaggle/working/hf_models/qwen2_5_vl_7b",
        "notebook": "vlm_qwen2_5_vl_7b_T4x2_parallel.ipynb",
        "pins": [
            "transformers==4.49.0",
            "accelerate>=0.34",
            "sentencepiece",
            "huggingface_hub>=0.24",
            "qwen-vl-utils",
            "bitsandbytes>=0.45.0",
        ],
    },
    "internvl_8b": {
        "title": "InternVL2-8B",
        "repo_id": "OpenGVLab/InternVL2-8B",
        "cache": "/kaggle/working/hf_models/internvl_8b",
        "notebook": "vlm_internvl_8b_T4x2_parallel.ipynb",
        "pins": [
            "transformers==4.37.2",
            "tokenizers==0.15.2",
            "huggingface_hub==0.23.4",
            "accelerate==0.30.1",
            "timm==0.9.12",
            "einops",
            "sentencepiece",
        ],
    },
    "llava_onevision_7b": {
        "title": "LLaVA-OneVision-7B",
        "repo_id": "llava-hf/llava-onevision-qwen2-7b-ov-hf",
        "cache": "/kaggle/working/hf_models/llava_onevision_7b",
        "notebook": "vlm_llava_onevision_7b_T4x2_parallel.ipynb",
        "pins": [
            "transformers==4.49.0",
            "accelerate>=0.34",
            "sentencepiece",
            "huggingface_hub>=0.24",
            "bitsandbytes>=0.45.0",
        ],
    },
}

BUNDLES = {
    "spurious": {
        "zip": "certvic_spurious_flip_control.zip",
        "task": "pilot_eval_tasks_reviewed.jsonl",
        "source": REPO / "data/edits/spurious_flip_control",
        "kind": "control_TaskItem",
        "pairs": 94,
        "generations": 188,
    },
    "perception_scaled": {
        "zip": "certvic_perception_control_scaled.zip",
        "task": "pilot_eval_tasks_reviewed.jsonl",
        "source": REPO / "data/edits/perception_control_scaled",
        "kind": "control_TaskItem",
        "pairs": 369,
        "generations": 738,
    },
    "mechanism": {
        "zip": "certvic_mechanism_probes.zip",
        "task": "tasks.jsonl",
        "kind": "diagnostic_flat",
        "rows": 364,
        "generations": 364,
        "families": ("context_suppression", "object_list", "region_focused", "two_step"),
        "excluded_families": ("original_vs_edited",),
    },
    "polarity": {
        "zip": "certvic_polarity_ablations.zip",
        "task": "tasks.jsonl",
        "kind": "diagnostic_flat",
        "rows": 728,
        "generations": 728,
        "families": ("negative", "pixel_only", "positive", "short"),
        "excluded_families": (),
    },
}

BUILDER_DOC_FILES = (
    "README_RUN_ORDER.md",
    "INPUTS_MATRIX.md",
    "OUTPUTS_MATRIX.md",
    "LOCAL_INGEST_COMMANDS.md",
    "RUN_TIME_ESTIMATES.md",
    "manifest.json",
)


def _clean_owned_outputs(out: Path) -> None:
    """Remove only artifacts produced by this builder.

    ``dist/kaggle_remaining_runs`` is also used by independent packages such as
    the V11 spurious-V2 control.  Treating the directory itself as disposable
    silently deleted those packages whenever this builder (or its tests) ran.
    """

    owned = [out / name for name in BUILDER_DOC_FILES]
    owned.extend(out / spec["zip"] for spec in BUNDLES.values())
    owned.extend(out / "notebooks" / meta["notebook"] for meta in PROVIDERS.values())
    owned.append(out / "notebooks" / "diffusion_main_scale_T4x2_TEMPLATE.ipynb")
    for path in owned:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
    notebook_dir = out / "notebooks"
    if notebook_dir.is_dir() and not any(notebook_dir.iterdir()):
        notebook_dir.rmdir()


def _package_paths(out: Path, manifest: dict) -> list[Path]:
    """Return the explicit builder-owned payload for the aggregate ZIP."""

    paths = [out / name for name in BUILDER_DOC_FILES]
    paths.extend(out / entry["file"] for entry in manifest["notebooks"])
    paths.extend(out / entry["bundle"] for entry in manifest["bundles"])
    return sorted(set(paths))


def _md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.strip("\n")}


def _code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip("\n"),
    }


def _notebook(cells: list[dict]) -> dict:
    for idx, cell in enumerate(cells):
        cell["id"] = f"cell{idx:02d}"
    return {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=ZIP_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def _zip_bytes(zf: zipfile.ZipFile, name: str, data: bytes | str) -> None:
    if isinstance(data, str):
        data = data.encode("utf-8")
    zf.writestr(_zip_info(name), data)


def _zip_file(zf: zipfile.ZipFile, path: Path, name: str) -> None:
    _zip_bytes(zf, name, path.read_bytes())


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _jsonl(rows: list[dict]) -> str:
    return "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n"


def _portable_probe_path(raw: str | None, role: str = "") -> str | None:
    if not raw:
        return raw
    posix = raw.replace("\\", "/")
    base = Path(raw).name
    role = role.lower()
    if role == "original" or "/orig/" in posix:
        return f"__PROBE__/orig/{base}"
    return f"__PROBE__/{base}"


def _portable_probe_row(row: dict) -> dict:
    out = dict(row)
    role = str(out.get("image_variant") or out.get("image_role") or "").lower()
    if out.get("original_image_path"):
        out["original_image_path"] = _portable_probe_path(out["original_image_path"], "original")
    if out.get("edited_image_path"):
        out["edited_image_path"] = _portable_probe_path(out["edited_image_path"], "edited")
    if out.get("image_path"):
        out["image_path"] = _portable_probe_path(out["image_path"], role)
    return out


def _manifest_for_bundle(
    bundle_name: str,
    run_tag: str,
    kind: str,
    task_name: str,
    task_bytes: bytes,
    image_files: dict[str, bytes],
    expected_rows: int,
    expected_generations: int,
    families: tuple[str, ...] = (),
    excluded_families: tuple[str, ...] = (),
) -> dict:
    files = {
        task_name: {"sha256": _sha256_bytes(task_bytes), "bytes": len(task_bytes)},
        **{name: {"sha256": _sha256_bytes(data), "bytes": len(data)} for name, data in sorted(image_files.items())},
    }
    return {
        "schema": "certvic.kaggle_remaining_bundle.v1",
        "bundle": bundle_name,
        "run_tag": run_tag,
        "kind": kind,
        "task_file": task_name,
        "expected_rows": expected_rows,
        "expected_generations_per_model": expected_generations,
        "image_files": len(image_files),
        "runnable_families": list(families),
        "excluded_families": list(excluded_families),
        "paper_evidence": False,
        "produced_model_results": False,
        "contains_model_weights": False,
        "contains_predictions": False,
        "files": files,
    }


def build_control_bundle(run_tag: str, out_path: Path) -> dict:
    spec = BUNDLES[run_tag]
    source = spec["source"]
    task_path = source / spec["task"]
    rows = _read_jsonl(task_path)
    if len(rows) != spec["pairs"]:
        raise RuntimeError(f"{run_tag}: expected {spec['pairs']} task pairs, found {len(rows)}")
    task_bytes = _jsonl(rows).encode("utf-8")
    image_files: dict[str, bytes] = {}
    for path in sorted(source.glob("*.jpg")) + sorted((source / "orig").glob("*.jpg")):
        image_files[path.relative_to(source).as_posix()] = path.read_bytes()
    manifest = _manifest_for_bundle(
        spec["zip"],
        run_tag,
        spec["kind"],
        spec["task"],
        task_bytes,
        image_files,
        expected_rows=spec["pairs"],
        expected_generations=spec["generations"],
    )
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        _zip_bytes(zf, spec["task"], task_bytes)
        _zip_bytes(zf, "bundle_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        for name, data in sorted(image_files.items()):
            _zip_bytes(zf, name, data)
    return {
        "run_tag": run_tag,
        "bundle": spec["zip"],
        "kind": spec["kind"],
        "task_file": spec["task"],
        "rows": spec["pairs"],
        "generations_per_model": spec["generations"],
        "image_files": len(image_files),
        "sha256": _sha256(out_path),
    }


def _probe_image_bytes(row: dict, image_src: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for key, role in (("original_image_path", "original"), ("edited_image_path", "edited"), ("image_path", "")):
        raw = row.get(key)
        if not raw:
            continue
        portable = _portable_probe_path(raw, role or str(row.get("image_variant") or row.get("image_role") or ""))
        if not portable:
            continue
        rel = portable.replace("__PROBE__/", "")
        src = image_src / rel
        if src.exists():
            out[rel] = src.read_bytes()
    return out


def build_probe_bundle(run_tag: str, out_path: Path) -> dict:
    spec = BUNDLES[run_tag]
    image_src = REPO / "data/edits/main_real_200"
    if run_tag == "mechanism":
        root = REPO / "data/results/main_real_200/mechanism_probes"
        task_files = [root / family / "tasks.jsonl" for family in spec["families"]]
    elif run_tag == "polarity":
        root = REPO / "data/results/main_real_200/prompt_ablations"
        task_files = [root / family / "tasks.jsonl" for family in spec["families"]]
    else:
        raise ValueError(run_tag)
    rows: list[dict] = []
    image_files: dict[str, bytes] = {}
    for task_file in task_files:
        for row in _read_jsonl(task_file):
            family = row.get("probe_family") or row.get("ablation_family")
            if family in spec["excluded_families"]:
                raise RuntimeError(f"{run_tag}: excluded family leaked into bundle: {family}")
            rows.append(_portable_probe_row(row))
            image_files.update(_probe_image_bytes(row, image_src))
    if len(rows) != spec["rows"]:
        raise RuntimeError(f"{run_tag}: expected {spec['rows']} diagnostic rows, found {len(rows)}")
    task_bytes = _jsonl(rows).encode("utf-8")
    manifest = _manifest_for_bundle(
        spec["zip"],
        run_tag,
        spec["kind"],
        spec["task"],
        task_bytes,
        image_files,
        expected_rows=spec["rows"],
        expected_generations=spec["generations"],
        families=spec["families"],
        excluded_families=spec["excluded_families"],
    )
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        _zip_bytes(zf, spec["task"], task_bytes)
        _zip_bytes(zf, "bundle_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        for name, data in sorted(image_files.items()):
            _zip_bytes(zf, name, data)
    return {
        "run_tag": run_tag,
        "bundle": spec["zip"],
        "kind": spec["kind"],
        "task_file": spec["task"],
        "rows": spec["rows"],
        "generations_per_model": spec["generations"],
        "families": list(spec["families"]),
        "excluded_families": list(spec["excluded_families"]),
        "image_files": len(image_files),
        "sha256": _sha256(out_path),
    }


def _install_cell(provider: str) -> dict:
    pins = ", ".join(repr(p) for p in PROVIDERS[provider]["pins"])
    return _code(
        f"""
# Install provider-specific runtime dependencies before importing transformers.
import os, subprocess, sys
DEPS_SENTINEL = "/kaggle/working/.certvic_deps_{provider}"
if not os.path.exists(DEPS_SENTINEL):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", {pins}], check=True)
    open(DEPS_SENTINEL, "w").write("ok\\n")
    print("installed pinned stack for {provider}")
else:
    print("dependency sentinel exists:", DEPS_SENTINEL)
"""
    )


def _config_cell(provider: str) -> dict:
    cache = PROVIDERS[provider]["cache"]
    return _code(
        f"""
# Editable configuration and input auto-detection.
import glob, json, os, sys, zipfile
from pathlib import Path

CERTVIC_DIR = None       # parent directory containing certvic/
BUNDLE_INPUT = None      # bundle directory or .zip; auto-detected when None
OUTPUT_DIR = "/kaggle/working"
MODEL_CACHE_DIR = "{cache}"
MODEL_REVISION = None    # REQUIRED: exact 40-character Hugging Face commit SHA
PROVIDER = "{provider}"
RUN_TAG = None           # one of: spurious, perception_scaled, polarity, mechanism
ALLOW_INTERNVL_TWO_WORKER = False  # advanced only; default is safer shared T4x2 sequential mode

RUN_TAGS = {list(RUN_TAGS)!r}
BUNDLE_BY_TAG = {{
    "spurious": "certvic_spurious_flip_control.zip",
    "perception_scaled": "certvic_perception_control_scaled.zip",
    "polarity": "certvic_polarity_ablations.zip",
    "mechanism": "certvic_mechanism_probes.zip",
}}

def _find_certvic_parent():
    for p in glob.glob("/kaggle/input/**/certvic/eval/run_eval.py", recursive=True):
        return str(Path(p).parents[2])
    return None

def _materialize_zip(path):
    path = str(path)
    if not path.endswith(".zip"):
        return path
    dest = Path(OUTPUT_DIR) / ("bundle_" + Path(path).stem)
    marker = dest / ".unzipped"
    if not marker.exists():
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as zf:
            zf.extractall(dest)
        marker.write_text("ok\\n")
    return str(dest)

def _bundle_tag_from_manifest(directory):
    manifest = Path(directory) / "bundle_manifest.json"
    if manifest.exists():
        return json.loads(manifest.read_text()).get("run_tag")
    name = Path(directory).name
    for tag, zip_name in BUNDLE_BY_TAG.items():
        if tag in name or zip_name.replace(".zip", "") in name:
            return tag
    return None

def _find_bundle():
    candidates = []
    for p in glob.glob("/kaggle/input/**/*.zip", recursive=True):
        if Path(p).name in BUNDLE_BY_TAG.values():
            candidates.append(p)
    for p in glob.glob("/kaggle/input/**/bundle_manifest.json", recursive=True):
        candidates.append(str(Path(p).parent))
    for name in ("pilot_eval_tasks_reviewed.jsonl", "tasks.jsonl"):
        for p in glob.glob(f"/kaggle/input/**/{{name}}", recursive=True):
            candidates.append(str(Path(p).parent))
    tagged = []
    for c in sorted(set(candidates)):
        directory = _materialize_zip(c)
        tag = _bundle_tag_from_manifest(directory)
        if tag:
            tagged.append((tag, directory))
    if RUN_TAG:
        matches = [directory for tag, directory in tagged if tag == RUN_TAG]
        if matches:
            return sorted(matches, key=len)[0], RUN_TAG
    if len(tagged) == 1:
        return tagged[0][1], tagged[0][0]
    raise RuntimeError("Attach exactly one remaining-run task bundle or set BUNDLE_INPUT and RUN_TAG.")

CERTVIC_DIR = CERTVIC_DIR or _find_certvic_parent()
if BUNDLE_INPUT:
    BUNDLE_INPUT = _materialize_zip(BUNDLE_INPUT)
    RUN_TAG = RUN_TAG or _bundle_tag_from_manifest(BUNDLE_INPUT)
else:
    BUNDLE_INPUT, RUN_TAG = _find_bundle()
if RUN_TAG not in RUN_TAGS:
    raise RuntimeError(f"RUN_TAG must be one of {{RUN_TAGS}}, got {{RUN_TAG!r}}")
if not CERTVIC_DIR:
    raise RuntimeError("Attach the CertVIC code bundle, e.g. dist/certvic_kaggle_main200_bundle.zip.")

sys.path.insert(0, CERTVIC_DIR)
import certvic
print("CERTVIC_DIR      :", CERTVIC_DIR)
print("BUNDLE_INPUT     :", BUNDLE_INPUT)
print("OUTPUT_DIR       :", OUTPUT_DIR)
print("MODEL_CACHE_DIR  :", MODEL_CACHE_DIR)
print("PROVIDER / RUN_TAG:", PROVIDER, RUN_TAG)
print("certvic import   :", certvic.__file__)
"""
    )


def _gpu_cell() -> dict:
    return _code(
        """
# GPU inventory. Kaggle setting should be Accelerator = GPU T4 x2.
import json, torch
GPU_COUNT = torch.cuda.device_count()
print("torch.cuda.device_count() =", GPU_COUNT)
GPU_INFO = []
for i in range(GPU_COUNT):
    props = torch.cuda.get_device_properties(i)
    mem_gb = round(props.total_memory / (1024 ** 3), 2)
    GPU_INFO.append({"index": i, "name": props.name, "memory_gb": mem_gb})
    print(f"GPU {i}: {props.name} | {mem_gb} GiB")
if GPU_COUNT < 1:
    raise RuntimeError("No CUDA GPU detected. In Kaggle choose Accelerator = GPU T4 x2.")
if GPU_COUNT == 1:
    print("WARNING: only one GPU detected; both deterministic shards will run sequentially on GPU0.")
if GPU_COUNT >= 2:
    print("T4x2 path available: worker 0 uses CUDA_VISIBLE_DEVICES=0 and worker 1 uses CUDA_VISIBLE_DEVICES=1.")
"""
    )


def _download_cell(provider: str) -> dict:
    repo_id = PROVIDERS[provider]["repo_id"]
    return _code(
        f"""
# Download one exact model revision. Internet must be ON for first run.
import os, re
from huggingface_hub import snapshot_download

MODEL_REPO_ID = "{repo_id}"
if not isinstance(MODEL_REVISION, str) or not re.fullmatch(r"[0-9a-f]{{40}}", MODEL_REVISION):
    raise RuntimeError(
        "Set MODEL_REVISION in the configuration cell to an exact 40-character "
        "Hugging Face commit SHA before any provider run."
    )

def _hf_token():
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret("HF_TOKEN")
    except Exception:
        return os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
revision_marker = os.path.join(MODEL_CACHE_DIR, ".certvic_model_revision")
if os.path.exists(os.path.join(MODEL_CACHE_DIR, "config.json")):
    if not os.path.exists(revision_marker):
        raise RuntimeError("Cached model has no CertVIC revision marker; use a fresh cache directory.")
    cached_revision = open(revision_marker).read().strip()
    if cached_revision != MODEL_REVISION:
        raise RuntimeError(
            f"Cached model revision {{cached_revision!r}} != locked {{MODEL_REVISION!r}}; "
            "use a fresh cache directory."
        )
    print("reusing cached model:", MODEL_CACHE_DIR)
else:
    print("downloading", MODEL_REPO_ID, "revision", MODEL_REVISION, "->", MODEL_CACHE_DIR)
    snapshot_download(
        repo_id=MODEL_REPO_ID,
        revision=MODEL_REVISION,
        local_dir=MODEL_CACHE_DIR,
        token=_hf_token(),
    )
    open(revision_marker, "w").write(MODEL_REVISION + "\\n")
assert os.path.exists(os.path.join(MODEL_CACHE_DIR, "config.json")), "model download missing config.json"
assert open(revision_marker).read().strip() == MODEL_REVISION, "model revision marker mismatch"
"""
    )


def _prepare_tasks_cell() -> dict:
    return _code(
        """
# Prepare portable task shards. Control bundles use TaskItem/run_eval; diagnostics use the flat loop.
import json, os
from pathlib import Path

MODE_BY_TAG = {
    "spurious": "control",
    "perception_scaled": "control",
    "polarity": "diagnostic",
    "mechanism": "diagnostic",
}
EXPECTED_ROWS_BY_TAG = {"spurious": 94, "perception_scaled": 369, "polarity": 728, "mechanism": 364}
EXPECTED_PREDS_BY_TAG = {"spurious": 188, "perception_scaled": 738, "polarity": 728, "mechanism": 364}
TASK_FILE_BY_MODE = {"control": "pilot_eval_tasks_reviewed.jsonl", "diagnostic": "tasks.jsonl"}
RUN_MODE = MODE_BY_TAG[RUN_TAG]
TASK_FILE = TASK_FILE_BY_MODE[RUN_MODE]
task_path = Path(BUNDLE_INPUT) / TASK_FILE
if not task_path.exists():
    raise RuntimeError(f"Expected {TASK_FILE} in {BUNDLE_INPUT}")
rows = [json.loads(line) for line in task_path.read_text().splitlines() if line.strip()]
if len(rows) != EXPECTED_ROWS_BY_TAG[RUN_TAG]:
    raise RuntimeError(f"{RUN_TAG}: expected {EXPECTED_ROWS_BY_TAG[RUN_TAG]} rows, found {len(rows)}")

def _remap_control_path(raw, variant):
    base = os.path.basename(str(raw).replace("__CTRL__/", ""))
    if variant == "original":
        return str(Path(BUNDLE_INPUT) / "orig" / base)
    return str(Path(BUNDLE_INPUT) / base)

def _remap_probe_path(raw, role):
    raw = str(raw or "")
    base = os.path.basename(raw.replace("__PROBE__/", ""))
    if role == "original" or "/orig/" in raw or raw.startswith("__PROBE__/orig/"):
        return str(Path(BUNDLE_INPUT) / "orig" / base)
    return str(Path(BUNDLE_INPUT) / base)

prepared = []
missing = []
if RUN_MODE == "control":
    for row in rows:
        r = dict(row)
        r["original_image_path"] = _remap_control_path(r["original_image_path"], "original")
        r["edited_image_path"] = _remap_control_path(r["edited_image_path"], "edited")
        for key in ("original_image_path", "edited_image_path"):
            if not Path(r[key]).exists():
                missing.append(r[key])
        prepared.append(r)
else:
    for idx, row in enumerate(rows):
        family = row.get("probe_family") or row.get("ablation_family")
        if family == "original_vs_edited" or row.get("evidence_status") == "SPEC_BLOCKED":
            raise RuntimeError("SPEC_BLOCKED mechanism family original_vs_edited is excluded and refused.")
        r = dict(row)
        r["_row_index"] = idx
        if r.get("original_image_path"):
            r["original_image_path"] = _remap_probe_path(r["original_image_path"], "original")
        if r.get("edited_image_path"):
            r["edited_image_path"] = _remap_probe_path(r["edited_image_path"], "edited")
        if r.get("image_path"):
            role = str(r.get("image_variant") or r.get("image_role") or "").lower()
            r["image_path"] = _remap_probe_path(r["image_path"], role)
        img = r.get("image_path")
        if not img:
            role = str(r.get("image_role") or "edited").lower()
            img = r.get("original_image_path") if role == "original" else r.get("edited_image_path")
        if not img or not Path(img).exists():
            missing.append(str(img))
        prepared.append(r)
if missing:
    raise RuntimeError(f"Missing {len(missing)} referenced image files, first={missing[:3]}")

ROW_ORDER = {row["item_id"]: i for i, row in enumerate(prepared)}
shards = {0: [], 1: []}
for i, row in enumerate(prepared):
    shards[i % 2].append(row)

SHARD_TASKS = {}
SHARD_EXPECT = {}
for shard in (0, 1):
    dst = Path(OUTPUT_DIR) / f"tasks_{PROVIDER}_{RUN_TAG}_shard{shard}.jsonl"
    dst.write_text("\\n".join(json.dumps(row, sort_keys=True) for row in shards[shard]) + "\\n")
    SHARD_TASKS[shard] = str(dst)
    SHARD_EXPECT[shard] = (2 * len(shards[shard])) if RUN_MODE == "control" else len(shards[shard])
    print(f"shard{shard}: {len(shards[shard])} task rows -> expected {SHARD_EXPECT[shard]} predictions")
print("RUN_MODE:", RUN_MODE, "| expected merged predictions:", EXPECTED_PREDS_BY_TAG[RUN_TAG])

CFG = str(Path(OUTPUT_DIR) / f"kaggle_{PROVIDER}_{RUN_TAG}.yaml")
Path(CFG).write_text(
    "mode: kaggle_open_vlm\\n"
    f"provider_name: {PROVIDER}\\n"
    f"provider: {PROVIDER}\\n"
    f"model_id: {MODEL_CACHE_DIR}\\n"
    f"model_version: {MODEL_REVISION}\\n"
    "device: cuda\\n"
    "dtype: bfloat16\\n"
    "batch_size: 1\\n"
    "max_new_tokens: 16\\n"
    "temperature: 0.0\\n"
    "paid_services_enabled: false\\n"
)
print("wrote config:", CFG)
"""
    )


def _worker_script_cell(provider: str) -> dict:
    if provider == "internvl_8b":
        return _internvl_worker_script_cell()
    return _code(
        r'''
# Write the subprocess worker. Each worker owns one shard and one CUDA visibility mask.
from pathlib import Path
WORKER_CODE = r"""
import json, os, sys, time, traceback
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYTHONUNBUFFERED", "1")
sys.path.insert(0, os.environ["CERTVIC_DIR"])

PROVIDER = os.environ["PROVIDER"]
RUN_TAG = os.environ["RUN_TAG"]
RUN_MODE = os.environ["RUN_MODE"]
MODEL_DIR = os.environ["MODEL_CACHE_DIR"]
MODEL_REVISION = os.environ["MODEL_REVISION"]
TASKS_SHARD = os.environ["TASKS_SHARD"]
OUT_PATH = os.environ["OUT_PATH"]
CFG = os.environ["CFG"]
SHARD = int(os.environ["SHARD"])

import torch
from PIL import Image
from certvic.eval.parse import parse_answer
import certvic.providers.open_vlm as ovlm

def _progress(state):
    state["n"] += 1
    if state["n"] <= 2 or state["n"] % 20 == 0:
        dt = max(time.time() - state["t0"], 1e-6)
        print(f"[{PROVIDER} {RUN_TAG} shard{SHARD}] {state['n']} generations | {state['n'] / dt:.3f} gen/s", flush=True)

def _load_qwen():
    from transformers import AutoProcessor, BitsAndBytesConfig
    try:
        from transformers import Qwen2_5_VLForConditionalGeneration as Model
    except Exception:
        from transformers import AutoModelForImageTextToText as Model
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    model = Model.from_pretrained(MODEL_DIR, device_map={"": 0}, quantization_config=bnb,
                                  low_cpu_mem_usage=True).eval()
    processor = AutoProcessor.from_pretrained(MODEL_DIR, max_pixels=768 * 768)
    state = {"n": 0, "t0": time.time()}

    @torch.inference_mode()
    def answer(self, image_path, prompt):
        image = Image.open(image_path).convert("RGB")
        msgs = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}]}]
        text = processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[text], images=[image], return_tensors="pt").to(model.device)
        out = model.generate(**inputs, max_new_tokens=16, do_sample=False)
        _progress(state)
        return processor.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
    return answer

def _load_llava():
    import transformers
    from transformers import AutoProcessor, BitsAndBytesConfig, LlavaOnevisionForConditionalGeneration
    transformers.logging.set_verbosity_error()
    processor = AutoProcessor.from_pretrained(MODEL_DIR)
    if hasattr(processor, "image_processor"):
        try:
            processor.image_processor.image_grid_pinpoints = [[384, 384]]
            print("set processor.image_processor.image_grid_pinpoints = [[384, 384]]", flush=True)
        except Exception as exc:
            print("image_grid_pinpoints not set:", repr(exc), flush=True)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    model = LlavaOnevisionForConditionalGeneration.from_pretrained(
        MODEL_DIR, device_map={"": 0}, quantization_config=bnb, low_cpu_mem_usage=True
    ).eval()
    pad_token_id = processor.tokenizer.eos_token_id
    state = {"n": 0, "t0": time.time()}

    @torch.inference_mode()
    def answer(self, image_path, prompt):
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((384, 384))
        conv = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
        text = processor.apply_chat_template(conv, add_generation_prompt=True)
        inputs = processor(images=image, text=text, return_tensors="pt").to(model.device, torch.float16)
        out = model.generate(**inputs, max_new_tokens=16, do_sample=False, pad_token_id=pad_token_id)
        _progress(state)
        return processor.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    return answer

def _load_internvl():
    import math
    import torchvision.transforms as T
    from torchvision.transforms.functional import InterpolationMode
    from transformers import AutoModel, AutoTokenizer

    IMAGENET_MEAN, IMAGENET_STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)
    MAX_TILES = 1

    def build_transform(size):
        return T.Compose([
            T.Lambda(lambda img: img.convert("RGB") if img.mode != "RGB" else img),
            T.Resize((size, size), interpolation=InterpolationMode.BICUBIC),
            T.ToTensor(),
            T.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ])

    def split_model(num_layers=32):
        n = torch.cuda.device_count()
        if n <= 1:
            return "auto"
        per = math.ceil(num_layers / (n - 0.5))
        alloc = [per] * n
        alloc[0] = math.ceil(per * 0.5)
        device_map, layer = {}, 0
        for gpu, count in enumerate(alloc):
            for _ in range(count):
                if layer < num_layers:
                    device_map[f"language_model.model.layers.{layer}"] = gpu
                    layer += 1
        for key in ["vision_model", "mlp1", "language_model.model.tok_embeddings",
                    "language_model.model.embed_tokens", "language_model.output",
                    "language_model.model.norm", "language_model.model.rotary_emb",
                    "language_model.lm_head", f"language_model.model.layers.{num_layers - 1}"]:
            device_map[key] = 0
        return device_map

    def load_image(path, input_size=448):
        img = Image.open(path).convert("RGB")
        img.thumbnail((448, 448))
        transform = build_transform(input_size)
        return torch.stack([transform(img)])

    ngpu = torch.cuda.device_count()
    kwargs = dict(torch_dtype=torch.bfloat16, low_cpu_mem_usage=True, trust_remote_code=True)
    if ngpu >= 2:
        print("InternVL shared T4x2 mode: bf16 split_model/device_map, no BitsAndBytesConfig.", flush=True)
        model = AutoModel.from_pretrained(MODEL_DIR, device_map=split_model(), **kwargs).eval()
    else:
        print("InternVL single visible GPU fallback: device_map='auto' with CPU offload; no bitsandbytes/triton.", flush=True)
        offload = "/kaggle/working/internvl_offload"
        os.makedirs(offload, exist_ok=True)
        model = AutoModel.from_pretrained(
            MODEL_DIR, device_map="auto", max_memory={0: "14GiB", "cpu": "32GiB"},
            offload_folder=offload, **kwargs
        ).eval()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True, use_fast=False)
    gen = dict(max_new_tokens=16, do_sample=False)
    state = {"n": 0, "t0": time.time()}

    @torch.inference_mode()
    def answer(self, image_path, prompt):
        pv = load_image(image_path).to(torch.bfloat16).cuda()
        raw = str(model.chat(tokenizer, pv, "<image>\n" + prompt, gen)).strip()
        _progress(state)
        return raw
    return answer

def _patch_provider():
    if PROVIDER == "qwen2_5_vl_7b":
        answer = _load_qwen()
    elif PROVIDER == "llava_onevision_7b":
        answer = _load_llava()
    elif PROVIDER == "internvl_8b":
        answer = _load_internvl()
    else:
        raise RuntimeError(f"unsupported provider {PROVIDER}")
    def _mark_loaded(self):
        self.model_version = MODEL_REVISION
    ovlm.OpenVLMProvider.load = _mark_loaded
    ovlm.OpenVLMProvider.answer = answer

def _prediction_id(row):
    family = row.get("probe_family") or row.get("ablation_family") or "na"
    variant = row.get("image_variant") or row.get("image_role") or "na"
    return f"{RUN_TAG}:{row.get('_row_index')}:{family}:{row.get('item_id')}:{variant}"

def _diagnostic_loop():
    rows = [json.loads(line) for line in Path(TASKS_SHARD).read_text().splitlines() if line.strip()]
    done = set()
    out = Path(OUT_PATH)
    if out.exists():
        for line in out.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line).get("prediction_id"))
    with out.open("a", encoding="utf-8") as handle:
        for row in rows:
            pid = _prediction_id(row)
            if pid in done:
                continue
            family = row.get("probe_family") or row.get("ablation_family")
            if family == "original_vs_edited" or row.get("evidence_status") == "SPEC_BLOCKED":
                raise RuntimeError("Refusing SPEC_BLOCKED diagnostic family original_vs_edited.")
            role = str(row.get("image_variant") or row.get("image_role") or "edited").lower()
            image_path = row.get("image_path")
            if not image_path:
                image_path = row.get("original_image_path") if role == "original" else row.get("edited_image_path")
            prompt = row.get("prompt") or row.get("question") or row.get("question_original")
            raw = ovlm.OpenVLMProvider.answer(None, image_path, prompt)
            parsed = parse_answer(raw, row.get("answer_format", "yes_no"), strict=True)
            record = {
                "prediction_id": pid,
                "_row_index": row.get("_row_index"),
                "run_id": f"remaining_{PROVIDER}_{RUN_TAG}_shard{SHARD}",
                "item_id": row["item_id"],
                "image_variant": role,
                "provider_name": PROVIDER,
                "provider_type": "open_local",
                "model_name": MODEL_DIR,
                "model_version": MODEL_REVISION,
                "prompt": prompt,
                "raw_output": raw,
                "parsed_answer": parsed.parsed_answer,
                "parse_ok": parsed.parse_ok,
                "parse_confidence": parsed.parse_confidence,
                "latency_s": 0.0,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "evidence_status": "DIAGNOSTIC_NON_EVIDENCE",
                "metadata": {
                    "probe_family": row.get("probe_family"),
                    "ablation_family": row.get("ablation_family"),
                    "polarity": row.get("polarity"),
                    "gold_answer": row.get("gold_answer"),
                    "base_gold": row.get("base_gold"),
                    "shard": SHARD,
                },
            }
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()

def main():
    print("worker starting", json.dumps({
        "provider": PROVIDER,
        "run_tag": RUN_TAG,
        "run_mode": RUN_MODE,
        "shard": SHARD,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "torch_cuda_device_count": torch.cuda.device_count(),
    }, sort_keys=True), flush=True)
    _patch_provider()
    if RUN_MODE == "control":
        from certvic.eval.run_eval import run_eval
        run_prefix = "v9" if RUN_TAG == "spurious_v2" else "remaining"
        summary = run_eval(
            config_path=CFG,
            tasks_path=TASKS_SHARD,
            out_path=OUT_PATH,
            provider_name=PROVIDER,
            run_id=f"{run_prefix}_{PROVIDER}_{RUN_TAG}_shard{SHARD}",
            num_shards=1,
            strict_leakage=True,
            evidence_run=(RUN_TAG != "spurious_v2"),
            fail_fast=False,
            overwrite=False,
        )
        print(json.dumps(summary, sort_keys=True), flush=True)
    else:
        _diagnostic_loop()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
"""
Path("/kaggle/working/certvic_vlm_worker.py").write_text(WORKER_CODE)
print("wrote /kaggle/working/certvic_vlm_worker.py")
'''
    )


def _internvl_worker_script_cell() -> dict:
    return _code(
        r'''
# Write the InternVL subprocess worker. No 4-bit quantization config, no bitsandbytes/triton dependency.
from pathlib import Path
WORKER_CODE = r"""
import json, math, os, sys, time, traceback
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYTHONUNBUFFERED", "1")
sys.path.insert(0, os.environ["CERTVIC_DIR"])

PROVIDER = os.environ["PROVIDER"]
RUN_TAG = os.environ["RUN_TAG"]
RUN_MODE = os.environ["RUN_MODE"]
MODEL_DIR = os.environ["MODEL_CACHE_DIR"]
MODEL_REVISION = os.environ["MODEL_REVISION"]
TASKS_SHARD = os.environ["TASKS_SHARD"]
OUT_PATH = os.environ["OUT_PATH"]
CFG = os.environ["CFG"]
SHARD = int(os.environ["SHARD"])

import torch
import torchvision.transforms as T
from PIL import Image
from torchvision.transforms.functional import InterpolationMode
from transformers import AutoModel, AutoTokenizer
from certvic.eval.parse import parse_answer
import certvic.providers.open_vlm as ovlm

def _progress(state):
    state["n"] += 1
    if state["n"] <= 2 or state["n"] % 20 == 0:
        dt = max(time.time() - state["t0"], 1e-6)
        print(f"[{PROVIDER} {RUN_TAG} shard{SHARD}] {state['n']} generations | {state['n'] / dt:.3f} gen/s", flush=True)

def _load_internvl():
    IMAGENET_MEAN, IMAGENET_STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)

    def build_transform(size):
        return T.Compose([
            T.Lambda(lambda img: img.convert("RGB") if img.mode != "RGB" else img),
            T.Resize((size, size), interpolation=InterpolationMode.BICUBIC),
            T.ToTensor(),
            T.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ])

    def split_model(num_layers=32):
        n = torch.cuda.device_count()
        if n <= 1:
            return "auto"
        per = math.ceil(num_layers / (n - 0.5))
        alloc = [per] * n
        alloc[0] = math.ceil(per * 0.5)
        device_map, layer = {}, 0
        for gpu, count in enumerate(alloc):
            for _ in range(count):
                if layer < num_layers:
                    device_map[f"language_model.model.layers.{layer}"] = gpu
                    layer += 1
        for key in ["vision_model", "mlp1", "language_model.model.tok_embeddings",
                    "language_model.model.embed_tokens", "language_model.output",
                    "language_model.model.norm", "language_model.model.rotary_emb",
                    "language_model.lm_head", f"language_model.model.layers.{num_layers - 1}"]:
            device_map[key] = 0
        return device_map

    def load_image(path, input_size=448):
        image = Image.open(path).convert("RGB")
        image.thumbnail((448, 448))
        transform = build_transform(input_size)
        return torch.stack([transform(image)])

    visible = torch.cuda.device_count()
    kwargs = dict(torch_dtype=torch.bfloat16, low_cpu_mem_usage=True, trust_remote_code=True)
    if visible >= 2:
        print("InternVL shared T4x2 mode: bf16 split_model/device_map across both GPUs.", flush=True)
        model = AutoModel.from_pretrained(MODEL_DIR, device_map=split_model(), **kwargs).eval()
    else:
        print("InternVL single visible GPU fallback: device_map='auto' with CPU offload; slower but explicit.", flush=True)
        offload = "/kaggle/working/internvl_offload"
        os.makedirs(offload, exist_ok=True)
        model = AutoModel.from_pretrained(
            MODEL_DIR,
            device_map="auto",
            max_memory={0: "14GiB", "cpu": "32GiB"},
            offload_folder=offload,
            **kwargs,
        ).eval()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True, use_fast=False)
    gen = dict(max_new_tokens=16, do_sample=False)
    state = {"n": 0, "t0": time.time()}

    @torch.inference_mode()
    def answer(self, image_path, prompt):
        pixel_values = load_image(image_path).to(torch.bfloat16).cuda()
        raw = str(model.chat(tokenizer, pixel_values, "<image>\n" + prompt, gen)).strip()
        _progress(state)
        return raw
    return answer

def _patch_provider():
    if PROVIDER != "internvl_8b":
        raise RuntimeError(f"this worker is InternVL-only, got {PROVIDER}")
    def _mark_loaded(self):
        self.model_version = MODEL_REVISION
    ovlm.OpenVLMProvider.load = _mark_loaded
    ovlm.OpenVLMProvider.answer = _load_internvl()

def _prediction_id(row):
    family = row.get("probe_family") or row.get("ablation_family") or "na"
    variant = row.get("image_variant") or row.get("image_role") or "na"
    return f"{RUN_TAG}:{row.get('_row_index')}:{family}:{row.get('item_id')}:{variant}"

def _diagnostic_loop():
    rows = [json.loads(line) for line in Path(TASKS_SHARD).read_text().splitlines() if line.strip()]
    done = set()
    out = Path(OUT_PATH)
    if out.exists():
        for line in out.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line).get("prediction_id"))
    with out.open("a", encoding="utf-8") as handle:
        for row in rows:
            pid = _prediction_id(row)
            if pid in done:
                continue
            family = row.get("probe_family") or row.get("ablation_family")
            if family == "original_vs_edited" or row.get("evidence_status") == "SPEC_BLOCKED":
                raise RuntimeError("Refusing SPEC_BLOCKED diagnostic family original_vs_edited.")
            role = str(row.get("image_variant") or row.get("image_role") or "edited").lower()
            image_path = row.get("image_path")
            if not image_path:
                image_path = row.get("original_image_path") if role == "original" else row.get("edited_image_path")
            prompt = row.get("prompt") or row.get("question") or row.get("question_original")
            raw = ovlm.OpenVLMProvider.answer(None, image_path, prompt)
            parsed = parse_answer(raw, row.get("answer_format", "yes_no"), strict=True)
            record = {
                "prediction_id": pid,
                "_row_index": row.get("_row_index"),
                "run_id": f"remaining_{PROVIDER}_{RUN_TAG}_shard{SHARD}",
                "item_id": row["item_id"],
                "image_variant": role,
                "provider_name": PROVIDER,
                "provider_type": "open_local",
                "model_name": MODEL_DIR,
                "model_version": MODEL_REVISION,
                "prompt": prompt,
                "raw_output": raw,
                "parsed_answer": parsed.parsed_answer,
                "parse_ok": parsed.parse_ok,
                "parse_confidence": parsed.parse_confidence,
                "latency_s": 0.0,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "evidence_status": "DIAGNOSTIC_NON_EVIDENCE",
                "metadata": {
                    "probe_family": row.get("probe_family"),
                    "ablation_family": row.get("ablation_family"),
                    "polarity": row.get("polarity"),
                    "gold_answer": row.get("gold_answer"),
                    "base_gold": row.get("base_gold"),
                    "shard": SHARD,
                },
            }
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()

def main():
    print("worker starting", json.dumps({
        "provider": PROVIDER,
        "run_tag": RUN_TAG,
        "run_mode": RUN_MODE,
        "shard": SHARD,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "torch_cuda_device_count": torch.cuda.device_count(),
    }, sort_keys=True), flush=True)
    _patch_provider()
    if RUN_MODE == "control":
        from certvic.eval.run_eval import run_eval
        run_prefix = "v9" if RUN_TAG == "spurious_v2" else "remaining"
        summary = run_eval(
            config_path=CFG,
            tasks_path=TASKS_SHARD,
            out_path=OUT_PATH,
            provider_name=PROVIDER,
            run_id=f"{run_prefix}_{PROVIDER}_{RUN_TAG}_shard{SHARD}",
            num_shards=1,
            strict_leakage=True,
            evidence_run=(RUN_TAG != "spurious_v2"),
            fail_fast=False,
            overwrite=False,
        )
        print(json.dumps(summary, sort_keys=True), flush=True)
    else:
        _diagnostic_loop()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
"""
Path("/kaggle/working/certvic_vlm_worker.py").write_text(WORKER_CODE)
print("wrote InternVL-only /kaggle/working/certvic_vlm_worker.py")
'''
    )


def _launch_cell() -> dict:
    return _code(
        r'''
# Launch workers, resume complete shards, merge deterministically, and zip outputs.
import collections, hashlib, json, os, subprocess, sys, time, zipfile
from datetime import datetime, timezone
from pathlib import Path

OUTDIR = Path(OUTPUT_DIR)
WORKER = "/kaggle/working/certvic_vlm_worker.py"
OUTDIR.mkdir(parents=True, exist_ok=True)

def count_jsonl(path):
    p = Path(path)
    if not p.exists():
        return 0
    return sum(1 for line in p.read_text().splitlines() if line.strip())

def shard_out(shard):
    return str(OUTDIR / f"pred_{PROVIDER}_{RUN_TAG}_shard{shard}.jsonl")

def shard_log(shard):
    return str(OUTDIR / f"log_{PROVIDER}_{RUN_TAG}_shard{shard}.txt")

def shard_complete(shard):
    n = count_jsonl(shard_out(shard))
    return n == SHARD_EXPECT[shard]

def launch(shard, visible_devices):
    env = dict(os.environ)
    env.update({
        "CUDA_VISIBLE_DEVICES": str(visible_devices),
        "CERTVIC_DIR": CERTVIC_DIR,
        "MODEL_CACHE_DIR": MODEL_CACHE_DIR,
        "MODEL_REVISION": MODEL_REVISION,
        "PROVIDER": PROVIDER,
        "RUN_TAG": RUN_TAG,
        "RUN_MODE": RUN_MODE,
        "TASKS_SHARD": SHARD_TASKS[shard],
        "OUT_PATH": shard_out(shard),
        "CFG": CFG,
        "SHARD": str(shard),
        "PYTHONUNBUFFERED": "1",
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
    })
    log_handle = open(shard_log(shard), "a", encoding="utf-8")
    log_handle.write(f"\n=== launch {datetime.now(timezone.utc).isoformat()} CUDA_VISIBLE_DEVICES={visible_devices} ===\n")
    log_handle.flush()
    return subprocess.Popen([sys.executable, "-u", WORKER], env=env, stdout=log_handle, stderr=subprocess.STDOUT), log_handle

def wait_for(procs):
    t0 = time.time()
    while any(proc.poll() is None for proc, _handle in procs.values()):
        time.sleep(20)
        parts = []
        for shard, (proc, _handle) in sorted(procs.items()):
            status = "run" if proc.poll() is None else f"exit={proc.returncode}"
            parts.append(f"shard{shard}:{count_jsonl(shard_out(shard))}/{SHARD_EXPECT[shard]} {status}")
        print(f"[{int(time.time() - t0):4d}s {PROVIDER} {RUN_TAG}] " + " | ".join(parts), flush=True)
    for _proc, handle in procs.values():
        handle.close()
    failures = {shard: proc.returncode for shard, (proc, _handle) in procs.items() if proc.returncode != 0}
    if failures:
        for shard in failures:
            log = Path(shard_log(shard)).read_text(errors="replace")[-2000:]
            print(f"--- log tail shard{shard} ---\n{log}", flush=True)
        raise RuntimeError(f"worker failure(s): {failures}")

def run_needed_shards():
    needed = [s for s in (0, 1) if not shard_complete(s)]
    if not needed:
        print("all shard outputs already complete; skipping workers")
        return
    if PROVIDER == "internvl_8b" and GPU_COUNT >= 2 and not ALLOW_INTERNVL_TWO_WORKER:
        print("InternVL auto-fallback: two full model copies are not memory-safe on T4x2 without bitsandbytes/triton.")
        print("Running shard0 then shard1 with CUDA_VISIBLE_DEVICES=0,1 and device_map/split_model across both GPUs.")
        for shard in needed:
            proc, handle = launch(shard, "0,1")
            wait_for({shard: (proc, handle)})
        return
    if GPU_COUNT >= 2:
        print("Launching two parallel GPU workers: shard0 -> CUDA_VISIBLE_DEVICES=0, shard1 -> CUDA_VISIBLE_DEVICES=1")
        procs = {}
        for shard in needed:
            visible = "0" if shard == 0 else "1"
            procs[shard] = launch(shard, visible)
        wait_for(procs)
    else:
        print("WARNING: single-GPU fallback; running both shards sequentially on CUDA_VISIBLE_DEVICES=0.")
        for shard in needed:
            proc, handle = launch(shard, "0")
            wait_for({shard: (proc, handle)})

runtime_manifest = {
    "schema": "certvic.kaggle_remaining_runtime_manifest.v1",
    "provider": PROVIDER,
    "run_tag": RUN_TAG,
    "run_mode": RUN_MODE,
    "model_repo_id": MODEL_REPO_ID,
    "model_revision": MODEL_REVISION,
    "model_revision_marker_verified": True,
    "code_bundle_sha256": globals().get("CODE_BUNDLE_SHA256"),
    "control_bundle_sha256": globals().get("CONTROL_BUNDLE_SHA256"),
    "gpu_count_detected": GPU_COUNT,
    "gpu_info": GPU_INFO,
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "paper_evidence": False,
    "produced_model_results_by_notebook_build": False,
    "shard_expected_rows": SHARD_EXPECT,
}
run_needed_shards()
runtime_manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()

for shard in (0, 1):
    actual = count_jsonl(shard_out(shard))
    if actual != SHARD_EXPECT[shard]:
        raise RuntimeError(f"shard{shard} incomplete: expected {SHARD_EXPECT[shard]}, found {actual}")

variant_order = {"original": 0, "edited": 1}
records = []
seen = set()
for shard in (0, 1):
    for line in Path(shard_out(shard)).read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if RUN_MODE == "control":
            key = (rec.get("item_id"), rec.get("image_variant"))
            sort_key = (ROW_ORDER.get(rec.get("item_id"), 10**12), variant_order.get(rec.get("image_variant"), 9))
        else:
            key = rec.get("prediction_id")
            sort_key = (int(rec.get("_row_index", 10**12)), str(rec.get("prediction_id")))
        if key in seen:
            raise RuntimeError(f"duplicate prediction id: {key}")
        seen.add(key)
        records.append((sort_key, rec))
records.sort(key=lambda item: item[0])
expected_total = EXPECTED_PREDS_BY_TAG[RUN_TAG]
if len(records) != expected_total:
    raise RuntimeError(f"merged row count mismatch: expected {expected_total}, found {len(records)}")
if RUN_MODE == "control":
    expected_keys = {(row["item_id"], variant) for row in prepared for variant in ("original", "edited")}
    observed_keys = {(rec.get("item_id"), rec.get("image_variant")) for _key, rec in records}
    if observed_keys != expected_keys:
        missing = sorted(expected_keys - observed_keys)
        extra = sorted(observed_keys - expected_keys)
        raise RuntimeError(f"prediction key mismatch: missing={missing[:5]} extra={extra[:5]}")
    wrong_provider = [rec.get("provider_name") for _key, rec in records if rec.get("provider_name") != PROVIDER]
    if wrong_provider:
        raise RuntimeError(f"provider mismatch in merged rows: {sorted(set(wrong_provider))}")
    parse_failures = [
        (rec.get("item_id"), rec.get("image_variant"))
        for _key, rec in records
        if rec.get("parse_ok") is not True or rec.get("parsed_answer") not in {"yes", "no"}
    ]
    if parse_failures:
        raise RuntimeError(
            f"certification-critical parse failures block packaging: {parse_failures[:5]} "
            f"(n={len(parse_failures)})"
        )
merged_name = f"pred_{PROVIDER}_{RUN_TAG}_merged.jsonl" if RUN_MODE == "control" else f"pred_{PROVIDER}_{RUN_TAG}.jsonl"
merged_path = OUTDIR / merged_name
merged_path.write_text("\n".join(json.dumps(rec, sort_keys=True) for _key, rec in records) + "\n")

if RUN_TAG == "spurious_v2":
    runtime_manifest.update({
        "schema": "certvic.v11.spurious_v2.kaggle_output_manifest.v3",
        "expected_items": len(prepared),
        "expected_prediction_rows": expected_total,
        "merged_predictions": merged_name,
        "merged_predictions_sha256": hashlib.sha256(merged_path.read_bytes()).hexdigest(),
        "task_file_sha256": hashlib.sha256(Path(task_path).read_bytes()).hexdigest(),
        "canonical_results_changed": False,
    })

parse_values = [rec.get("parse_ok") for _key, rec in records if "parse_ok" in rec]
answer_counts = collections.Counter(str(rec.get("parsed_answer")) for _key, rec in records if "parsed_answer" in rec)
summary = {
    "schema": "certvic.kaggle_remaining_summary.v1",
    "provider": PROVIDER,
    "run_tag": RUN_TAG,
    "run_mode": RUN_MODE,
    "merged_file": merged_name,
    "expected_rows": expected_total,
    "actual_rows": len(records),
    "duplicates": 0,
    "parse_ok_count": sum(1 for value in parse_values if bool(value)),
    "parse_total": len(parse_values),
    "parse_ok_rate": (sum(1 for value in parse_values if bool(value)) / len(parse_values)) if parse_values else None,
    "answer_counts": dict(answer_counts),
    "paper_evidence": False,
}
summary_path = OUTDIR / f"summary_{PROVIDER}_{RUN_TAG}.json"
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
runtime_path = OUTDIR / f"runtime_manifest_{PROVIDER}_{RUN_TAG}.json"
runtime_path.write_text(json.dumps(runtime_manifest, indent=2, sort_keys=True) + "\n")

zip_path = OUTDIR / f"{PROVIDER}_{RUN_TAG}_preds.zip"
include = [merged_path, summary_path, runtime_path]
for shard in (0, 1):
    include += [Path(shard_out(shard)), Path(shard_log(shard))]
    for suffix in (".run_manifest.json", ".provider_metadata.json", ".environment.json"):
        sidecar = Path(shard_out(shard) + suffix)
        if sidecar.exists():
            include.append(sidecar)
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for path in include:
        if path.exists() and "hf_models" not in str(path):
            zf.write(path, path.name)
print("MERGED:", merged_path)
print("SUMMARY:", summary_path)
print("DOWNLOAD:", zip_path)
'''
    )


def build_vlm_notebook(provider: str) -> dict:
    meta = PROVIDERS[provider]
    internvl_note = (
        "\n\nInternVL note: this notebook avoids 4-bit quantization config and broken "
        "bitsandbytes/triton paths. By default it falls back to a shared T4x2 "
        "sequential mode when two full InternVL copies are not memory-safe."
        if provider == "internvl_8b"
        else ""
    )
    llava_note = (
        "\n\nLLaVA speed fix is included: `image.thumbnail((384, 384))`, "
        "`processor.image_processor.image_grid_pinpoints = [[384, 384]]` when supported, "
        "and pad token is set to EOS for generation."
        if provider == "llava_onevision_7b"
        else ""
    )
    cells = [
        _md(
            f"""# CertVIC remaining runs -- {meta['title']} T4x2 parallel

Runs exactly one remaining CertVIC bundle per Kaggle session: `spurious`,
`perception_scaled`, `polarity`, or `mechanism`.

Default settings: Kaggle **GPU T4 x2**, Internet ON, one provider, one task
bundle, deterministic two-shard execution. With two GPUs, shard0 runs with
`CUDA_VISIBLE_DEVICES=0` and shard1 with `CUDA_VISIBLE_DEVICES=1`. With one GPU,
both shards run sequentially on GPU0. Shard outputs, logs, summary JSON, runtime
manifest, and a download zip are written to `/kaggle/working`.

This notebook prepares predictions only when you run it on Kaggle; the local
builder does not run models and does not create model results.{internvl_note}{llava_note}"""
        ),
        _install_cell(provider),
        _config_cell(provider),
        _gpu_cell(),
        _download_cell(provider),
        _prepare_tasks_cell(),
        _worker_script_cell(provider),
        _launch_cell(),
        _md("## Local ingest\nAfter downloading `<provider>_<run_tag>_preds.zip`, use `LOCAL_INGEST_COMMANDS.md`."),
    ]
    return _notebook(cells)


def build_diffusion_template() -> dict:
    cells = [
        _md(
            """# CertVIC Main-scale diffusion -- T4x2 template

Template for later Main-500 diffusion on free Kaggle T4 x2. Do not run this
until the remaining VLM controls and go/no-go gates pass. The notebook is
structured as two deterministic GPU workers: shard0 uses
`CUDA_VISIBLE_DEVICES=0`, shard1 uses `CUDA_VISIBLE_DEVICES=1`, with a
single-GPU sequential fallback.

Expected Main-500 planning anchors: CPU planning 10-30 min, diffusion on T4x2
about 6-8 hr, quality/detectability CPU 15-60 min, human review about 20-25 hr.
This template emits no local results when generated."""
        ),
        _code(
            r'''
# Configuration placeholders. Fill these in only after Main-500 is approved.
import json, os, subprocess, sys, time, zipfile
from pathlib import Path
import torch

CERTVIC_DIR = None
PLAN_INPUT = None          # directory containing scale/edit plan JSONL files
ADE20K_INPUT = None
OUTPUT_DIR = "/kaggle/working"
RUN_TAG = "main500_diffusion"
GPU_COUNT = torch.cuda.device_count()
print("torch.cuda.device_count() =", GPU_COUNT)
for i in range(GPU_COUNT):
    p = torch.cuda.get_device_properties(i)
    print(f"GPU {i}: {p.name} | {round(p.total_memory / (1024 ** 3), 2)} GiB")
print("Template only until paths are filled; no GPU work performed here.")
'''
        ),
        _code(
            r'''
# Deterministic T4x2 worker skeleton. Uses shard-level outputs, logs, resume checks, and merge.
from pathlib import Path
import json, os, subprocess, sys, time, zipfile

WORKER = Path(OUTPUT_DIR) / "certvic_diffusion_worker.py"
WORKER.write_text("""
import os, json, sys
shard = int(os.environ['SHARD'])
print('diffusion worker placeholder', {'shard': shard, 'cuda': os.environ.get('CUDA_VISIBLE_DEVICES')}, flush=True)
# Replace this placeholder with the existing certvic.edit.engines.batch_generate call once
# the Main-500 edit plan and approved model inputs are mounted.
""")

def launch(shard, visible):
    env = dict(os.environ, SHARD=str(shard), CUDA_VISIBLE_DEVICES=str(visible), PYTHONUNBUFFERED="1")
    log = open(Path(OUTPUT_DIR) / f"log_diffusion_main_scale_shard{shard}.txt", "a")
    return subprocess.Popen([sys.executable, "-u", str(WORKER)], env=env, stdout=log, stderr=subprocess.STDOUT), log

def run_template():
    if GPU_COUNT >= 2:
        print("Would launch shard0 on CUDA_VISIBLE_DEVICES=0 and shard1 on CUDA_VISIBLE_DEVICES=1.")
    else:
        print("WARNING: single-GPU fallback would run shard0 then shard1 on CUDA_VISIBLE_DEVICES=0.")
    print("Shard outputs would be generated_shard0.jsonl / generated_shard1.jsonl and merged deterministically.")
    print("Download zip would be diffusion_main_scale_T4x2_outputs.zip, excluding model cache/weights.")

run_template()
'''
        ),
    ]
    return _notebook(cells)


def write_notebook_pair(name: str, nb: dict, manifest: dict, provider: str) -> None:
    text = json.dumps(nb, indent=1)
    dist_path = OUT / "notebooks" / name
    repo_path = KAGGLE_NB / name
    dist_path.write_text(text, encoding="utf-8")
    repo_path.write_text(text, encoding="utf-8")
    manifest["notebooks"].append(
        {
            "provider": provider,
            "file": f"notebooks/{name}",
            "repo_file": f"notebooks/kaggle/{name}",
            "sha256": _sha256(dist_path),
        }
    )


def write_docs(out: Path, manifest: dict) -> None:
    docs = {
        "README_RUN_ORDER.md": README_RUN_ORDER,
        "INPUTS_MATRIX.md": INPUTS_MATRIX,
        "OUTPUTS_MATRIX.md": OUTPUTS_MATRIX,
        "LOCAL_INGEST_COMMANDS.md": LOCAL_INGEST_COMMANDS,
        "RUN_TIME_ESTIMATES.md": RUNTIME_ESTIMATES,
    }
    for name, body in docs.items():
        (out / name).write_text(body, encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    RUNBOOKS.mkdir(parents=True, exist_ok=True)
    (RUNBOOKS / "REMAINING_GPU_CPU_RUNTIME_ESTIMATES.md").write_text(RUNTIME_ESTIMATES, encoding="utf-8")
    (RUNBOOKS / "KAGGLE_T4X2_PARALLEL_VLM_REMAINING_RUNS.md").write_text(PARALLEL_VLM_RUNBOOK, encoding="utf-8")
    (RUNBOOKS / "KAGGLE_MAIN_SCALE_T4X2_TEMPLATE.md").write_text(MAIN_SCALE_RUNBOOK, encoding="utf-8")


def main(argv: list[str] | None = None) -> dict:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    _clean_owned_outputs(OUT)
    (OUT / "notebooks").mkdir(parents=True, exist_ok=True)
    KAGGLE_NB.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema": "certvic.remaining_kaggle_runbooks.v2",
        "paper_evidence": False,
        "produced_model_results": False,
        "notebooks": [],
        "bundles": [],
        "run_tags": list(RUN_TAGS),
    }

    for provider, meta in PROVIDERS.items():
        write_notebook_pair(meta["notebook"], build_vlm_notebook(provider), manifest, provider)
    write_notebook_pair("diffusion_main_scale_T4x2_TEMPLATE.ipynb", build_diffusion_template(), manifest, "main_scale_diffusion")

    for run_tag in ("spurious", "perception_scaled"):
        out_zip = OUT / BUNDLES[run_tag]["zip"]
        manifest["bundles"].append(build_control_bundle(run_tag, out_zip))
    for run_tag in ("mechanism", "polarity"):
        out_zip = OUT / BUNDLES[run_tag]["zip"]
        manifest["bundles"].append(build_probe_bundle(run_tag, out_zip))

    write_docs(OUT, manifest)

    with zipfile.ZipFile(TOP_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in _package_paths(OUT, manifest):
            _zip_file(zf, path, f"kaggle_remaining_runs/{path.relative_to(OUT).as_posix()}")

    result = {
        "out_dir": str(OUT.relative_to(REPO)),
        "top_zip": str(TOP_ZIP.relative_to(REPO)),
        "n_notebooks": len(manifest["notebooks"]),
        "n_bundles": len(manifest["bundles"]),
        "produced_model_results": False,
    }
    print(json.dumps(result, sort_keys=True))
    return result


README_RUN_ORDER = """# Remaining Kaggle runs -- run order

This package prepares executable runbooks. It does not contain model predictions
and does not make evidence claims.

## Kaggle settings for every VLM notebook

- Accelerator: GPU T4 x2
- Internet: ON for model self-download
- One provider notebook per session
- One task bundle per session
- Output directory: `/kaggle/working`

## Priority order

1. Spurious-flip / control_irrelevant: run each VLM notebook with `certvic_spurious_flip_control.zip`, `RUN_TAG=spurious`.
2. Scaled held-out perception control: run each VLM notebook with `certvic_perception_control_scaled.zip`, `RUN_TAG=perception_scaled`.
3. Prompt-polarity ablations: run each VLM notebook with `certvic_polarity_ablations.zip`, `RUN_TAG=polarity`.
4. Mechanism probes: run each VLM notebook with `certvic_mechanism_probes.zip`, `RUN_TAG=mechanism`; `original_vs_edited` is SPEC_BLOCKED and excluded.
5. Later Main-500: only after the above and go/no-go gates, use `diffusion_main_scale_T4x2_TEMPLATE.ipynb`.

Provider notebooks:

- `notebooks/kaggle/vlm_qwen2_5_vl_7b_T4x2_parallel.ipynb`
- `notebooks/kaggle/vlm_internvl_8b_T4x2_parallel.ipynb`
- `notebooks/kaggle/vlm_llava_onevision_7b_T4x2_parallel.ipynb`

Every VLM notebook writes shard predictions, shard logs, a deterministic merged
prediction JSONL, `summary_<provider>_<run_tag>.json`,
`runtime_manifest_<provider>_<run_tag>.json`, and `<provider>_<run_tag>_preds.zip`.
"""

INPUTS_MATRIX = """# Inputs matrix

Attach the CertVIC code bundle, for example `dist/certvic_kaggle_main200_bundle.zip`,
plus exactly one task bundle.

| RUN_TAG | notebook | task bundle | Kaggle accelerator | Internet | model cache |
|---|---|---|---|---|---|
| spurious | each VLM T4x2 notebook | `certvic_spurious_flip_control.zip` | GPU T4 x2 | ON | `/kaggle/working/hf_models/...` |
| perception_scaled | each VLM T4x2 notebook | `certvic_perception_control_scaled.zip` | GPU T4 x2 | ON | `/kaggle/working/hf_models/...` |
| polarity | each VLM T4x2 notebook | `certvic_polarity_ablations.zip` | GPU T4 x2 | ON | `/kaggle/working/hf_models/...` |
| mechanism | each VLM T4x2 notebook | `certvic_mechanism_probes.zip` | GPU T4 x2 | ON | `/kaggle/working/hf_models/...` |
| main500 diffusion | `diffusion_main_scale_T4x2_TEMPLATE.ipynb` | scale plan + ADE20K inputs | GPU T4 x2 | ON | excludes model cache from output zip |

The notebooks auto-detect `CERTVIC_DIR`, `BUNDLE_INPUT`, `OUTPUT_DIR`,
`MODEL_CACHE_DIR`, provider, and `RUN_TAG`, with explicit overrides in the config cell.
"""

OUTPUTS_MATRIX = """# Outputs matrix

| RUN_TAG | shard files | merged file to ingest | zip to download |
|---|---|---|---|
| spurious | `pred_<provider>_spurious_shard0.jsonl`, `pred_<provider>_spurious_shard1.jsonl` | `pred_<provider>_spurious_merged.jsonl` | `<provider>_spurious_preds.zip` |
| perception_scaled | `pred_<provider>_perception_scaled_shard0.jsonl`, `pred_<provider>_perception_scaled_shard1.jsonl` | `pred_<provider>_perception_scaled_merged.jsonl` | `<provider>_perception_scaled_preds.zip` |
| polarity | `pred_<provider>_polarity_shard0.jsonl`, `pred_<provider>_polarity_shard1.jsonl` | `pred_<provider>_polarity.jsonl` | `<provider>_polarity_preds.zip` |
| mechanism | `pred_<provider>_mechanism_shard0.jsonl`, `pred_<provider>_mechanism_shard1.jsonl` | `pred_<provider>_mechanism.jsonl` | `<provider>_mechanism_preds.zip` |

Each zip also includes `log_<provider>_<run_tag>_shard*.txt`,
`summary_<provider>_<run_tag>.json`, and
`runtime_manifest_<provider>_<run_tag>.json`. Model caches and weights are not zipped.
"""

LOCAL_INGEST_COMMANDS = """# Local ingest and report commands

Place downloaded prediction files into these local directories before running commands:

- Spurious: `data/results/main_real_200/kaggle_spurious/`
- Scaled perception: `data/results/main_real_200/kaggle_perception_scaled/`
- Polarity: `data/results/main_real_200/kaggle_polarity/`
- Mechanism: `data/results/main_real_200/kaggle_mechanism/`

Provider/model-name pairs:

- `qwen2_5_vl_7b` -> `Qwen/Qwen2.5-VL-7B-Instruct`
- `internvl_8b` -> `OpenGVLab/InternVL2-8B`
- `llava_onevision_7b` -> `llava-hf/llava-onevision-qwen2-7b-ov-hf`

## After spurious

For each provider:

```bash
python3 scripts/pilot_report_from_raw.py \\
  --provider <provider> \\
  --model-name <model_name> \\
  --run-label <provider> \\
  --raw-spurious data/results/main_real_200/kaggle_spurious/pred_<provider>_spurious_merged.jsonl
```

Then:

```bash
python3 -m certvic.validation.edit_detectability \\
  --tasks data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl \\
  --out-dir data/results/spurious_flip_control/edit_detectability

python3 -m certvic.v7.spurious_control_integration
```

## After scaled perception

For each provider:

```bash
python3 scripts/pilot_report_from_raw.py \\
  --provider <provider> \\
  --model-name <model_name> \\
  --run-label <provider> \\
  --raw-perception-scaled data/results/main_real_200/kaggle_perception_scaled/pred_<provider>_perception_scaled_merged.jsonl
```

## After polarity

The current repo has a real ablation reporter CLI, but it reports baseline
construct-validity ablations from a `run_ablations` prediction directory; it does
not directly score the new VLM polarity JSONL by itself. Stage the downloaded
VLM files in `data/results/main_real_200/kaggle_polarity/`, then run the existing
CPU baseline/reporting path with explicit args:

```bash
python3 -m certvic.eval.run_ablations \\
  --tasks data/results/main_real_200/pilot_eval_taskitems_v2.jsonl \\
  --out-dir data/results/main_real_200/construct_validity_ablations \\
  --max-items 91 \\
  --seed 0

python3 -m certvic.reporting.ablations \\
  --pred-dir data/results/main_real_200/construct_validity_ablations \\
  --tasks data/results/main_real_200/pilot_eval_taskitems_v2.jsonl \\
  --out-dir data/results/main_real_200/construct_validity_ablation_report
```

Do not invent polarity metrics from the staged VLM JSONL until a dedicated scorer exists.

## After mechanism

For each provider:

```bash
python3 -m certvic.mechanisms.intervention_analysis \\
  --baseline data/results/main_real_200/pair_scores_v2.jsonl \\
  --intervention data/results/main_real_200/kaggle_mechanism/pred_<provider>_mechanism.jsonl \\
  --out-dir data/results/main_real_200/mechanism_<provider>
```

## Final audits

```bash
python3 scripts/build_multimodel_summary.py
python3 -m certvic.v7.post_result_reviewer_attack_audit
python3 -m certvic.v7.v7_post3model_final_audit
python3 -m certvic.validation.claim_language_guard \\
  --root docs \\
  --out data/results/claim_language_guard_after_remaining_runs.json
python3 -m certvic.security.release_privacy_audit \\
  --root . \\
  --out data/results/privacy_audit_after_remaining_runs.json
python3 -m pytest -q
```
"""

RUNTIME_ESTIMATES = """# Remaining GPU / CPU / human runtime estimates

These are conservative estimates, not results. No model outputs are produced by
building these runbooks.

## Timing anchors

- LLaVA-OneVision-7B on one Kaggle T4: 182 generations took 1689 seconds, about 0.10-0.11 generation/sec.
- 120 absent-control items = 240 generations.
- 91 intervention items = 182 generations.
- Spurious set: 94 pairs = 188 generations/model.
- Scaled perception: 369 pairs = 738 generations/model.
- Mechanism: 364 generations/model.
- Polarity: 728 generations/model.

## Per-provider estimates

| RUN_TAG | generations/model | Qwen single GPU | Qwen T4x2 | InternVL single/shared fallback | InternVL T4x2 | LLaVA single GPU | LLaVA T4x2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| spurious | 188 | ~10-20 min | ~5-12 min | ~15-30 min | ~8-20 min depending memory/load mode | ~30-45 min | ~15-30 min if true parallel; ~30-45 min if fallback |
| perception_scaled | 738 | ~30-60 min | ~15-30 min | ~40-90 min | ~20-45 min | ~2-2.5 hr | ~60-90 min if true parallel; ~2-2.5 hr if fallback |
| polarity | 728 | ~20-40 min | ~10-20 min | ~30-60 min | ~15-30 min | ~1-2 hr | ~45-75 min if true parallel; ~1-2 hr if fallback |
| mechanism | 364 | ~15-30 min | ~8-15 min | ~20-50 min | ~10-25 min | ~55 min | ~25-45 min if true parallel; ~55 min if fallback |

InternVL defaults to a safer shared T4x2 sequential mode if two model copies are
not memory-safe without bitsandbytes/triton.

## Main-scale estimates

| stage | compute | conservative estimate |
|---|---|---:|
| Main-500 planning | CPU | ~10-30 min |
| Main-500 diffusion | Kaggle GPU T4x2 | ~6-8 hr |
| Main-500 quality/detectability | CPU | ~15-60 min |
| Main-500 human review | human | ~20-25 hr |
| Main-500 VLM | Kaggle GPU | model-dependent; for projected 566 tasks, estimate from measured per-generation rates and the final reviewed count |

Main-scale remains gated. Do not run the diffusion template until the remaining
controls and go/no-go checks are satisfied.
"""

PARALLEL_VLM_RUNBOOK = """# Kaggle T4x2 parallel VLM remaining runs

Use one provider notebook per Kaggle session with GPU T4 x2 and Internet ON.
Attach the CertVIC code bundle plus exactly one remaining task bundle. The
notebooks split rows deterministically into shard0/shard1, launch two subprocess
workers when memory-safe, set `CUDA_VISIBLE_DEVICES=0` for shard0 and
`CUDA_VISIBLE_DEVICES=1` for shard1, resume complete shard outputs, merge with
duplicate checks, write summaries, and zip only predictions/logs/manifests.

Required notebooks:

- `notebooks/kaggle/vlm_qwen2_5_vl_7b_T4x2_parallel.ipynb`
- `notebooks/kaggle/vlm_internvl_8b_T4x2_parallel.ipynb`
- `notebooks/kaggle/vlm_llava_onevision_7b_T4x2_parallel.ipynb`

Supported `RUN_TAG` values: `spurious`, `perception_scaled`, `polarity`, `mechanism`.
The mechanism bundle excludes and the notebooks refuse `original_vs_edited`
when marked SPEC_BLOCKED.

The optional unified router notebook is intentionally not generated; the
provider-specific notebooks are more transparent and easier to debug.
"""

MAIN_SCALE_RUNBOOK = """# Kaggle Main-scale T4x2 template

`notebooks/kaggle/diffusion_main_scale_T4x2_TEMPLATE.ipynb` is a template for a
later Main-500 diffusion session. It uses the same T4x2 layout as the earlier
diffusion runbook: shard0 on GPU0, shard1 on GPU1, shard-level logs/outputs,
resume checks, deterministic merge, and an output zip that excludes model
caches and weights.

Do not run Main-500 diffusion until remaining controls and go/no-go gates pass.
Planning is CPU (~10-30 min), diffusion is estimated at ~6-8 hr on T4x2,
quality/detectability is CPU (~15-60 min), and human review is ~20-25 hr.
"""


if __name__ == "__main__":
    main()
