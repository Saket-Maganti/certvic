from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from certvic.v9.spurious_v2_quality import summarize_quality  # noqa: E402
from certvic.validation.edit_detectability import (  # noqa: E402
    detectability_score,
    paired_features,
)
V1_TASKS = ROOT / "data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl"
V8_1_ALL = ROOT / "data/results/main_real_200/v8_1_qwen_spurious_forensics/qwen_spurious_all_items.jsonl"
OUT_DIR = ROOT / "data/edits/spurious_v2_control"
RESULT_DIR = ROOT / "data/results/main_real_200/v9_mega_upgrade"
BUNDLE = ROOT / "dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip"
ZIP_DATE = (2026, 1, 1, 0, 0, 0)
EXPECTED_FROZEN_ITEMS = 30


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _zip_file(zf: zipfile.ZipFile, path: Path, archive_name: str) -> None:
    """Write a byte-stable ZIP member independent of host mtimes/mode bits."""
    info = zipfile.ZipInfo(archive_name, date_time=ZIP_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zf.writestr(info, path.read_bytes())


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _safe_float(value, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _require_frozen_selection(selected: list[dict]) -> None:
    if len(selected) != EXPECTED_FROZEN_ITEMS:
        raise RuntimeError(
            "Spurious V2 preflight selected "
            f"{len(selected)} items, expected the frozen {EXPECTED_FROZEN_ITEMS}; "
            "refusing to overwrite canonical V2 artifacts"
        )


def _copy_or_reencode_jpeg(src: Path, dst: Path) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image

        with Image.open(src) as image:
            rgb = image.convert("RGB")
            rgb.save(dst, format="JPEG", quality=95, optimize=False)
        return "pillow_jpeg_quality_95"
    except Exception:
        shutil.copy2(src, dst)
        return "copy2_fallback_no_reencode"


def _write_spurious_v2_notebooks() -> list[str]:
    """Generate the dedicated V2 notebooks from the working T4x2 worker spine.

    The previous hand-written notebooks called the intentionally scaffold-only
    OpenVLMProvider directly, ran the two shards sequentially, and accepted any
    nonempty shard as complete. Reusing the remaining-run worker cells keeps the
    provider implementations, true T4x2 launch, structural resume checks, and
    fail-closed merge in one source.
    """
    from scripts.build_remaining_kaggle_runbooks import (
        PROVIDERS,
        _code,
        _download_cell,
        _gpu_cell,
        _install_cell,
        _launch_cell,
        _md,
        _notebook,
        _worker_script_cell,
    )

    notebooks = {
        "qwen2_5_vl_7b": "vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb",
        "internvl_8b": "vlm_internvl_8b_spurious_v2_T4x2.ipynb",
        "llava_onevision_7b": "vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb",
    }
    out_dir = ROOT / "notebooks/kaggle"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for provider, name in notebooks.items():
        config_cell = _code(
            f'''
# Frozen Spurious V2 inputs and safe archive discovery.
import glob, hashlib, json, os, shutil, sys, zipfile
from pathlib import Path

OUTPUT_DIR = "/kaggle/working"
MODEL_CACHE_DIR = "{PROVIDERS[provider]["cache"]}"
MODEL_REVISION = None    # REQUIRED: exact 40-character Hugging Face commit SHA
PROVIDER = "{provider}"
RUN_TAG = "spurious_v2"
RUN_MODE = "control"
ALLOW_INTERNVL_TWO_WORKER = False

def _find_exactly_one(name):
    roots = [Path("/kaggle/input")] if Path("/kaggle/input").exists() else [Path.cwd()]
    matches = sorted({{path.resolve() for root in roots for path in root.rglob(name)}})
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {{name}}, found {{len(matches)}}: {{matches}}")
    return matches[0]

def _materialize(path, destination):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    marker = destination / ".source_sha256"
    if marker.exists() and marker.read_text().strip() == digest:
        print("reuse hash-matched extraction", destination)
        return destination
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    with zipfile.ZipFile(path) as zf:
        root = destination.resolve()
        for info in zf.infolist():
            target = (destination / info.filename).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"Unsafe ZIP member {{info.filename!r}}")
        zf.extractall(destination)
    marker.write_text(digest + "\\n")
    return destination

code_zip = _find_exactly_one("certvic_kaggle_main200_bundle.zip")
v2_zip = _find_exactly_one("certvic_spurious_v2_control.zip")
CODE_BUNDLE_SHA256 = hashlib.sha256(code_zip.read_bytes()).hexdigest()
CONTROL_BUNDLE_SHA256 = hashlib.sha256(v2_zip.read_bytes()).hexdigest()
CERTVIC_ROOT = _materialize(code_zip, Path(OUTPUT_DIR) / "certvic_code")
BUNDLE_INPUT = _materialize(v2_zip, Path(OUTPUT_DIR) / "certvic_spurious_v2")
CERTVIC_DIR = str(CERTVIC_ROOT)
if not (CERTVIC_ROOT / "certvic/eval/run_eval.py").exists():
    raise RuntimeError("Code bundle is missing certvic/eval/run_eval.py")
sys.path.insert(0, CERTVIC_DIR)
import certvic
print("PROVIDER / RUN_TAG:", PROVIDER, RUN_TAG)
print("CODE_BUNDLE_SHA256:", CODE_BUNDLE_SHA256)
print("CONTROL_BUNDLE_SHA256:", CONTROL_BUNDLE_SHA256)
print("certvic import:", certvic.__file__)
'''
        )
        prepare_cell = _code(
            r'''
# Validate the frozen 30-item task set, remap paths, and make deterministic shards.
import hashlib, json
from pathlib import Path

task_path = BUNDLE_INPUT / "data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl"
bundle_manifest_path = BUNDLE_INPUT / "data/edits/spurious_v2_control/bundle_manifest.json"
if not task_path.exists() or not bundle_manifest_path.exists():
    raise RuntimeError("Spurious V2 bundle is missing the task file or bundle manifest")
bundle_manifest = json.loads(bundle_manifest_path.read_text())
task_sha256 = hashlib.sha256(task_path.read_bytes()).hexdigest()
expected_task_sha256 = (bundle_manifest.get("source_hashes") or {}).get("task_file_sha256")
if task_sha256 != expected_task_sha256:
    raise RuntimeError(f"Spurious V2 task hash mismatch: {task_sha256} != {expected_task_sha256}")

image_entries = bundle_manifest.get("image_entries") or []
if len(image_entries) != 60:
    raise RuntimeError(f"Spurious V2 expected 60 hash-locked images, found {len(image_entries)}")
for entry in image_entries:
    image_path = BUNDLE_INPUT / str(entry.get("path"))
    if not image_path.is_file():
        raise RuntimeError(f"Spurious V2 image missing: {entry.get('path')}")
    if image_path.stat().st_size != int(entry.get("bytes", -1)):
        raise RuntimeError(f"Spurious V2 image size mismatch: {entry.get('path')}")
    observed = hashlib.sha256(image_path.read_bytes()).hexdigest()
    if observed != entry.get("sha256"):
        raise RuntimeError(f"Spurious V2 image hash mismatch: {entry.get('path')}")

rows = [json.loads(line) for line in task_path.read_text().splitlines() if line.strip()]
if len(rows) != 30:
    raise RuntimeError(f"Spurious V2 expected 30 task rows, found {len(rows)}")
item_ids = [str(row.get("item_id")) for row in rows]
if len(set(item_ids)) != len(item_ids) or any(item_id in {"", "None"} for item_id in item_ids):
    raise RuntimeError("Spurious V2 task IDs are missing or duplicated")

prepared = []
missing = []
for row in rows:
    record = dict(row)
    for key in ("original_image_path", "edited_image_path"):
        record[key] = str(BUNDLE_INPUT / str(record[key]))
        if not Path(record[key]).is_file():
            missing.append(record[key])
    prepared.append(record)
if missing:
    raise RuntimeError(f"Missing {len(missing)} referenced images; first={missing[:3]}")

ROW_ORDER = {row["item_id"]: index for index, row in enumerate(prepared)}
shards = {0: prepared[0::2], 1: prepared[1::2]}
SHARD_TASKS = {}
SHARD_EXPECT = {}
for shard in (0, 1):
    destination = Path(OUTPUT_DIR) / f"tasks_{PROVIDER}_{RUN_TAG}_shard{shard}.jsonl"
    destination.write_text("\n".join(json.dumps(row, sort_keys=True) for row in shards[shard]) + "\n")
    SHARD_TASKS[shard] = str(destination)
    SHARD_EXPECT[shard] = 2 * len(shards[shard])
EXPECTED_PREDS_BY_TAG = {"spurious_v2": 60}

CFG = str(Path(OUTPUT_DIR) / f"kaggle_{PROVIDER}_{RUN_TAG}.yaml")
Path(CFG).write_text(
    "mode: kaggle_open_vlm\n"
    f"provider_name: {PROVIDER}\n"
    f"provider: {PROVIDER}\n"
    f"model_id: {MODEL_CACHE_DIR}\n"
    f"model_version: {MODEL_REVISION}\n"
    "device: cuda\n"
    "dtype: bfloat16\n"
    "batch_size: 1\n"
    "max_new_tokens: 16\n"
    "temperature: 0.0\n"
    "paid_services_enabled: false\n"
    f"run_tag: {RUN_TAG}\n"
)
print("task_sha256:", task_sha256)
print("shards:", {shard: len(values) for shard, values in shards.items()})
'''
        )
        notebook = _notebook(
            [
                _md(
                    f"""# CertVIC Spurious V2 -- {PROVIDERS[provider]['title']} T4x2

Runs the frozen 30-item retrospective stricter-control diagnostic on Kaggle.
The items were selected from the 94-item V1 pool after V1 outcomes existed, so
this run cannot be treated as an independent confirmatory V2. This is a real
provider-output collection step, but the output remains `paper_evidence=false`.
Shard0 and shard1
run concurrently on two GPUs where provider memory permits; the one-GPU and
InternVL shared-model fallbacks are explicit. The local builder executes no
model and creates no predictions."""
                ),
                _install_cell(provider),
                config_cell,
                _gpu_cell(),
                _download_cell(provider),
                prepare_cell,
                _worker_script_cell(provider),
                _launch_cell(),
                _md(
                    "Download `<provider>_spurious_v2_preds.zip` and run "
                    "`python3 scripts/import_v9_spurious_v2_outputs.py --input-dir "
                    "kaggleoutputs/v9_spurious_v2`. The importer requires the v2 runtime "
                    "manifest, source hashes, exact 60-row key set, strict parses, provider, "
                    "run tag, and conflict-free canonical destination."
                ),
            ]
        )
        path = out_dir / name
        path.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8")
        written.append(str(path.relative_to(ROOT)))
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic strict Spurious V2 control package.")
    parser.add_argument("--min-distance-px", type=float, default=75.0)
    parser.add_argument("--max-detectability-score", type=float, default=0.12)
    parser.add_argument("--seed", type=int, default=9009)
    args = parser.parse_args()

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    images_dir = OUT_DIR / "images"
    orig_dir = images_dir / "orig"
    ctrl_dir = images_dir / "control"
    orig_dir.mkdir(parents=True, exist_ok=True)
    ctrl_dir.mkdir(parents=True, exist_ok=True)

    v1_rows = {row["item_id"]: row for row in _load_jsonl(V1_TASKS)}
    audit_rows = _load_jsonl(V8_1_ALL)
    candidates = []
    exclusions = []
    for audit in audit_rows:
        item_id = audit["item_id"]
        task = v1_rows.get(item_id)
        if not task:
            exclusions.append({"item_id": item_id, "reason": "missing_v1_task"})
            continue
        reasons = []
        if bool(audit.get("patch_bbox_intersects_object_bbox")):
            reasons.append("patch_bbox_intersects_target_bbox")
        if _safe_float(audit.get("patch_target_mask_overlap_pixels")) > 0:
            reasons.append("patch_target_mask_overlap_positive")
        if _safe_float(audit.get("patch_object_bbox_distance_px")) < args.min_distance_px:
            reasons.append("distance_below_threshold")
        score = audit.get("detectability_score")
        if score is not None and score != "" and float(score) > args.max_detectability_score:
            reasons.append("detectability_above_threshold")
        if reasons:
            exclusions.append({"item_id": item_id, "reason": ",".join(reasons)})
            continue
        merged = dict(task)
        merged.update(
            {
                "target_object": audit.get("target_object"),
                "patch_bbox_xyxy": audit.get("patch_bbox_xyxy"),
                "target_bbox_xyxy": audit.get("target_bbox_xyxy"),
                "patch_object_bbox_distance_px": audit.get("patch_object_bbox_distance_px"),
                "patch_target_mask_overlap_pixels": audit.get("patch_target_mask_overlap_pixels"),
                "patch_bbox_intersects_object_bbox": audit.get("patch_bbox_intersects_object_bbox"),
                "detectability_score": audit.get("detectability_score"),
                "spurious_v2_seed": args.seed,
                "spurious_v2_policy": "filtered_from_v1_strict_geometry_salience",
            }
        )
        candidates.append(merged)

    by_class: dict[str, list[dict]] = defaultdict(list)
    for row in candidates:
        by_class[row.get("target_object", "unknown")].append(row)
    selected = []
    # Deterministic class-balanced order without discarding feasible items.
    for cls in sorted(by_class):
        selected.extend(sorted(by_class[cls], key=lambda row: row["item_id"]))

    _require_frozen_selection(selected)

    task_path = OUT_DIR / "pilot_eval_tasks_reviewed.jsonl"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    output_rows = []
    reencode_modes = set()
    for row in selected:
        item_id = row["item_id"]
        src_orig = ROOT / "data/edits/spurious_flip_control/orig" / f"{item_id}.jpg"
        src_ctrl = ROOT / "data/edits/spurious_flip_control" / f"{item_id}.jpg"
        dst_orig = orig_dir / f"{item_id}.jpg"
        dst_ctrl = ctrl_dir / f"{item_id}.jpg"
        reencode_modes.add(_copy_or_reencode_jpeg(src_orig, dst_orig))
        reencode_modes.add(_copy_or_reencode_jpeg(src_ctrl, dst_ctrl))
        out = dict(row)
        out["original_image_path"] = f"data/edits/spurious_v2_control/images/orig/{item_id}.jpg"
        out["edited_image_path"] = f"data/edits/spurious_v2_control/images/control/{item_id}.jpg"
        out["metadata"] = dict(out.get("metadata", {}))
        v11_pair_features = paired_features(str(dst_orig), str(dst_ctrl))
        if v11_pair_features is None:
            raise RuntimeError(f"unable to compute V11 detectability for {item_id}")
        out["metadata"].update(
            {
                "control": "spurious_v2_retrospective_stricter_control",
                "evidence_status": "DIAGNOSTIC_ONLY",
                "paper_evidence": False,
                "retrospective_post_selection": True,
                "independent_confirmatory_set": False,
                "min_distance_px": args.min_distance_px,
                "max_detectability_score": args.max_detectability_score,
                "original_image_sha256": _sha256(dst_orig),
                "edited_image_sha256": _sha256(dst_ctrl),
                "v11_detectability_score": round(
                    detectability_score(v11_pair_features), 8
                ),
                "v11_detectability_method": "certvic.validation.edit_detectability.paired_features_v11",
            }
        )
        output_rows.append(out)
    task_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in output_rows))

    quality = summarize_quality(output_rows, min_distance_px=args.min_distance_px)
    gallery_path = OUT_DIR / "spurious_v2_examples_gallery.html"
    gallery_path.write_text(
        "<!doctype html><html><body><h1>Spurious V2 Examples</h1>"
        + "".join(
            f"<section><h2>{row['item_id']}</h2>"
            f"<p>{row.get('target_object')} distance={row.get('patch_object_bbox_distance_px')}</p>"
            f"<img width='320' src='images/orig/{row['item_id']}.jpg'>"
            f"<img width='320' src='images/control/{row['item_id']}.jpg'></section>"
            for row in output_rows[:12]
        )
        + "</body></html>"
    )
    v11_detectability_scores = [
        float(row["metadata"]["v11_detectability_score"]) for row in output_rows
    ]
    manifest = {
        "schema": "certvic.v9.spurious_v2_manifest.v1",
        "prompt_file": "03_SPURIOUS_V2_STRICT_CONTROL_BUILDER.md",
        "source_task_file": str(V1_TASKS.relative_to(ROOT)),
        "source_audit_file": str(V8_1_ALL.relative_to(ROOT)),
        "n_source_items": len(audit_rows),
        "n_items": len(output_rows),
        "target_n_requested": "200-300",
        "target_n_local_status": "INSUFFICIENT_LOCAL_CANDIDATES_MAX_FEASIBLE_FILTERED_SET",
        "evidence_class": "DIAGNOSTIC_ONLY",
        "design_status": "RETROSPECTIVE_POST_OUTCOME_V1_SUBSET",
        "independent_confirmatory_set": False,
        "v1_outcomes_existed_before_selection": True,
        "v11_detectability_scores_complete": True,
        "v11_detectability_score_count": len(output_rows),
        "v11_detectability_score_min": min(v11_detectability_scores),
        "v11_detectability_score_max": max(v11_detectability_scores),
        "v11_detectability_score_mean": sum(v11_detectability_scores)
        / len(v11_detectability_scores),
        "v11_detectability_score_role": "post_selection_pre_provider_diagnostic_no_retroactive_exclusion",
        "deterministic_seed": args.seed,
        "min_distance_px": args.min_distance_px,
        "max_detectability_score": args.max_detectability_score,
        "jpeg_policy": sorted(reencode_modes),
        "task_file": str(task_path.relative_to(ROOT)),
        "images_dir": str(images_dir.relative_to(ROOT)),
        "examples_gallery": str(gallery_path.relative_to(ROOT)),
        "selected_items": [
            {
                "item_id": row["item_id"],
                "original": {
                    "path": row["original_image_path"],
                    "sha256": row["metadata"]["original_image_sha256"],
                    "bytes": (ROOT / row["original_image_path"]).stat().st_size,
                },
                "edited": {
                    "path": row["edited_image_path"],
                    "sha256": row["metadata"]["edited_image_sha256"],
                    "bytes": (ROOT / row["edited_image_path"]).stat().st_size,
                },
            }
            for row in output_rows
        ],
        "excluded_items": exclusions,
        "quality_report": "data/results/main_real_200/v9_mega_upgrade/spurious_v2_quality_report.json",
        "paper_evidence": False,
    }
    (OUT_DIR / "spurious_v2_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    image_files = sorted(images_dir.rglob("*.jpg"))
    image_entries = [
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in image_files
    ]
    bundle_manifest = {
        "schema": "certvic.v10_1.spurious_v2_bundle_manifest.v1",
        "bundle_file": str(BUNDLE.relative_to(ROOT)),
        "task_file": str(task_path.relative_to(ROOT)),
        "task_rows": len(output_rows),
        "image_files": [str(path.relative_to(ROOT)) for path in image_files],
        "image_entries": image_entries,
        "n_image_files": len(image_files),
        "spurious_v2_manifest": str((OUT_DIR / "spurious_v2_manifest.json").relative_to(ROOT)),
        "examples_gallery": str(gallery_path.relative_to(ROOT)),
        "expected_provider_outputs": [
            "pred_qwen2_5_vl_7b_spurious_v2_merged.jsonl",
            "pred_internvl_8b_spurious_v2_merged.jsonl",
            "pred_llava_onevision_7b_spurious_v2_merged.jsonl",
        ],
        "expected_provider_zip_outputs": [
            "qwen2_5_vl_7b_spurious_v2_preds.zip",
            "internvl_8b_spurious_v2_preds.zip",
            "llava_onevision_7b_spurious_v2_preds.zip",
        ],
        "produced_model_results": False,
        "evidence_class": "DIAGNOSTIC_ONLY",
        "design_status": "RETROSPECTIVE_POST_OUTCOME_V1_SUBSET",
        "public_redistribution_allowed": False,
        "release_status": "PRIVATE_LOCAL_OR_USER_CONTROLLED_KAGGLE_INPUT_ONLY_PENDING_LICENSE_REVIEW",
        "paper_evidence": False,
        "source_hashes": {
            "task_file_sha256": _sha256(task_path),
            "spurious_v2_manifest_sha256": _sha256(OUT_DIR / "spurious_v2_manifest.json"),
            "examples_gallery_sha256": _sha256(gallery_path),
        },
    }
    (OUT_DIR / "bundle_manifest.json").write_text(json.dumps(bundle_manifest, indent=2, sort_keys=True) + "\n")
    report = dict(manifest)
    report.update(quality)
    (RESULT_DIR / "spurious_v2_quality_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (RESULT_DIR / "SPURIOUS_V2_QUALITY_REPORT.md").write_text(
        "# Retrospective Spurious V2 Diagnostic Quality Report\n\n"
        f"- Source candidates: `{len(audit_rows)}`\n"
        f"- V2 retained items: `{len(output_rows)}`\n"
        f"- Requested target: `200-300`; local status: `{manifest['target_n_local_status']}`\n"
        f"- Min bbox distance enforced: `{args.min_distance_px}` px\n"
        f"- Bbox overlap count: `{quality['bbox_overlap_count']}`\n"
        f"- Mask overlap count: `{quality['mask_overlap_count']}`\n"
        f"- Quality pass: `{str(quality['quality_pass']).lower()}`\n"
        f"- Examples gallery: `{gallery_path.relative_to(ROOT)}`\n"
        f"- Bundle: `{BUNDLE.relative_to(ROOT)}`\n\n"
        "This is a retrospective dataset/build artifact selected from the V1 pool after V1 outcomes existed. "
        "It contains no VLM predictions, is diagnostic only, and is not paper evidence.\n"
    )

    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(BUNDLE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in [task_path, OUT_DIR / "spurious_v2_manifest.json", OUT_DIR / "bundle_manifest.json", gallery_path]:
            _zip_file(zf, path, path.relative_to(ROOT).as_posix())
        for path in image_files:
            _zip_file(zf, path, path.relative_to(ROOT).as_posix())
    notebooks = _write_spurious_v2_notebooks()
    (BUNDLE.parent / "SPURIOUS_V2_INPUTS_MATRIX.md").write_text(
        "# Retrospective Spurious V2 Diagnostic Inputs Matrix\n\n"
        "| Input | Required | Purpose |\n"
        "| --- | --- | --- |\n"
        "| `dist/certvic_kaggle_main200_bundle.zip` | yes | CertVIC package code/configs |\n"
        "| `dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip` | yes | Retrospective diagnostic tasks/images; private/user-controlled input pending license review |\n"
        "| Internet ON | yes unless model cache attached | Download packages/model weights |\n"
        "| Secrets | no | No paid/provider credentials used |\n"
    )
    (BUNDLE.parent / "SPURIOUS_V2_LOCAL_INGEST_COMMANDS.md").write_text(
        "# Retrospective Spurious V2 Diagnostic Local Ingest Commands\n\n"
        "```bash\n"
        "mkdir -p kaggleoutputs/v9_spurious_v2\n"
        "# place qwen2_5_vl_7b_spurious_v2_preds.zip, internvl_8b_spurious_v2_preds.zip, and llava_onevision_7b_spurious_v2_preds.zip there\n"
        "python3 scripts/import_v9_spurious_v2_outputs.py --input-dir kaggleoutputs/v9_spurious_v2 --out-dir data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest\n"
        "python3 -m pytest -q tests/test_v9_spurious_v2_ingest_decision.py\n"
        "```\n\n"
        "The importer must keep `paper_evidence=false` even when all files are valid: this 30-item set is a "
        "retrospective post-outcome V1 subset and can only support diagnostic sensitivity analysis.\n"
    )
    print(
        json.dumps(
            {
                "n_items": len(output_rows),
                "bundle": str(BUNDLE.relative_to(ROOT)),
                "notebooks": notebooks,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
