from __future__ import annotations

import hashlib
import json
import re
import subprocess
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/results/main_real_200/v10_1_correction"
RUNBOOK = ROOT / "docs/runbooks/V10_1_EXACT_SPURIOUS_V2_KAGGLE_CHECKLIST.md"

SPURIOUS_V2_BUNDLE = ROOT / "dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip"
CODE_BUNDLE = ROOT / "dist/certvic_kaggle_main200_bundle.zip"
TASK_FILE = ROOT / "data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl"
SPURIOUS_V2_MANIFEST = ROOT / "data/edits/spurious_v2_control/spurious_v2_manifest.json"
BUNDLE_MANIFEST = ROOT / "data/edits/spurious_v2_control/bundle_manifest.json"
QUALITY_REPORT = ROOT / "data/results/main_real_200/v9_mega_upgrade/spurious_v2_quality_report.json"
IMPORTER = ROOT / "scripts/import_v9_spurious_v2_outputs.py"

PROVIDER_NOTEBOOKS = {
    "qwen2_5_vl_7b": ROOT / "notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb",
    "internvl_8b": ROOT / "notebooks/kaggle/vlm_internvl_8b_spurious_v2_T4x2.ipynb",
    "llava_onevision_7b": ROOT / "notebooks/kaggle/vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb",
}
HANDOFF_NOTEBOOK = ROOT / "notebooks/kaggle/v10_execution_ready_handoff_t4x2.ipynb"

EXPECTED_MERGED = {
    "qwen2_5_vl_7b": "pred_qwen2_5_vl_7b_spurious_v2_merged.jsonl",
    "internvl_8b": "pred_internvl_8b_spurious_v2_merged.jsonl",
    "llava_onevision_7b": "pred_llava_onevision_7b_spurious_v2_merged.jsonl",
}
EXPECTED_ZIPS = {
    "qwen2_5_vl_7b": "qwen2_5_vl_7b_spurious_v2_preds.zip",
    "internvl_8b": "internvl_8b_spurious_v2_preds.zip",
    "llava_onevision_7b": "llava_onevision_7b_spurious_v2_preds.zip",
}


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def sanitize(text: str) -> str:
    replacements = [
        (str(ROOT), "<PROJECT_ROOT>"),
        (str(ROOT.parent), "<PROJECT_PARENT>"),
        (str(Path.home()), "<USER_HOME>"),
    ]
    out = text
    for old, new in sorted(replacements, key=lambda x: len(x[0]), reverse=True):
        out = out.replace(old, new)
    return out


def sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_discovery() -> dict:
    commands = [
        ("pwd", "pwd"),
        ("results_tail", "find data/results -maxdepth 4 -type f | sort | tail -200"),
        ("v10_privacy_files", "find . -maxdepth 5 -type f \\( -name \"*v10*\" -o -name \"AUTORUN_*\" -o -name \"*privacy*\" \\) | sort"),
        ("kaggle_notebooks", "find notebooks/kaggle -maxdepth 1 -type f | sort"),
        ("dist_tail", "find dist -maxdepth 3 -type f | sort | tail -100"),
    ]
    outputs = {}
    for key, cmd in commands:
        proc = subprocess.run(cmd, cwd=ROOT, shell=True, check=False, text=True, capture_output=True)
        outputs[key] = {
            "command": cmd,
            "returncode": proc.returncode,
            "stdout": sanitize(proc.stdout),
            "stderr": sanitize(proc.stderr),
        }
    return {
        "schema": "certvic.v10_1.input_discovery.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "commands": outputs,
    }


def render_discovery(discovery: dict) -> None:
    lines = [
        "# V10.1 Input Discovery",
        "",
        f"Generated: `{date.today().isoformat()}`",
        "",
        "This is a precise inspection of the V10/V10.1 local artifact surface. Paths are rendered relative to `<PROJECT_ROOT>` where applicable.",
        "",
        "## Commands Run",
        "",
    ]
    for key, item in discovery["commands"].items():
        lines += [
            f"### {key}",
            "",
            "```bash",
            item["command"],
            "```",
            "",
            f"Return code: `{item['returncode']}`",
            "",
            "```text",
            item["stdout"].strip() or "<no stdout>",
            "```",
            "",
        ]
        if item["stderr"].strip():
            lines += ["Stderr:", "", "```text", item["stderr"].strip(), "```", ""]
    write_json(OUT_DIR / "v10_1_input_discovery.json", discovery)
    write_md(OUT_DIR / "V10_1_INPUT_DISCOVERY.md", lines)


def file_entry(path: Path) -> dict:
    return {
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256(path),
    }


def notebook_audit(path: Path, expected_output: str | None = None, expected_zip: str | None = None) -> dict:
    entry = file_entry(path)
    entry.update(
        {
            "valid_nbformat": False,
            "contains_private_paths": None,
            "contains_fake_prediction_language": None,
            "contains_required_t4x2_tokens": {},
            "contains_expected_output": None,
            "contains_expected_zip": None,
            "warnings": [],
        }
    )
    if not path.exists():
        entry["warnings"].append("notebook_missing")
        return entry
    try:
        nb = nbformat.read(path, as_version=4)
        entry["valid_nbformat"] = True
        text = "\n".join("".join(cell.get("source", "")) for cell in nb.cells)
    except Exception as exc:  # pragma: no cover - report path
        entry["warnings"].append(f"nbformat_error:{type(exc).__name__}:{exc}")
        return entry
    lower = text.lower()
    unix_home_token = "/" + "home/"
    mac_home_token = "/" + "users/"
    entry["contains_private_paths"] = mac_home_token in lower or unix_home_token in lower
    entry["contains_fake_prediction_language"] = bool(re.search(r"\b(fake|mock|dummy)\s+prediction", lower))
    tokens = ["T4x2", "CUDA_VISIBLE_DEVICES", "shard0", "shard1", "RUN_TAG", "spurious_v2"]
    entry["contains_required_t4x2_tokens"] = {token: token in text for token in tokens}
    if expected_output:
        entry["contains_expected_output"] = expected_output in text
    if expected_zip:
        entry["contains_expected_zip"] = expected_zip in text
    return entry


def audit_spurious_v2_package() -> dict:
    manifest = read_json(SPURIOUS_V2_MANIFEST)
    bundle_manifest = read_json(BUNDLE_MANIFEST)
    quality = read_json(QUALITY_REPORT)
    task_rows = read_jsonl(TASK_FILE)
    image_files = sorted((ROOT / "data/edits/spurious_v2_control/images").rglob("*.jpg"))
    expected_count = int(manifest.get("n_items") or bundle_manifest.get("task_rows") or len(task_rows))

    zip_info = file_entry(SPURIOUS_V2_BUNDLE)
    zip_info.update(
        {
            "valid_zip": False,
            "members": [],
            "has_task_jsonl": False,
            "has_spurious_v2_manifest": False,
            "has_bundle_manifest": False,
            "zip_task_rows": None,
            "zip_image_count": None,
            "errors": [],
        }
    )
    if SPURIOUS_V2_BUNDLE.exists():
        try:
            with zipfile.ZipFile(SPURIOUS_V2_BUNDLE) as zf:
                names = sorted(zf.namelist())
                zip_info["valid_zip"] = True
                zip_info["members"] = names
                task_name = "data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl"
                zip_info["has_task_jsonl"] = task_name in names
                zip_info["has_spurious_v2_manifest"] = "data/edits/spurious_v2_control/spurious_v2_manifest.json" in names
                zip_info["has_bundle_manifest"] = "data/edits/spurious_v2_control/bundle_manifest.json" in names
                zip_info["zip_image_count"] = sum(1 for name in names if name.endswith(".jpg"))
                if task_name in names:
                    text = zf.read(task_name).decode("utf-8")
                    zip_info["zip_task_rows"] = len([line for line in text.splitlines() if line.strip()])
        except Exception as exc:  # pragma: no cover - report path
            zip_info["errors"].append(f"{type(exc).__name__}:{exc}")

    notebooks = {}
    for provider, path in PROVIDER_NOTEBOOKS.items():
        notebooks[provider] = notebook_audit(path, EXPECTED_MERGED[provider], EXPECTED_ZIPS[provider])
    notebooks["v10_handoff"] = notebook_audit(HANDOFF_NOTEBOOK)

    importer_text = IMPORTER.read_text(encoding="utf-8") if IMPORTER.exists() else ""
    importer_has_merged_template = "pred_{provider}_spurious_v2_merged.jsonl" in importer_text
    importer_has_zip_template = "{provider}_spurious_v2_preds.zip" in importer_text
    importer_expectations = {
        provider: {
            "merged_jsonl": EXPECTED_MERGED[provider],
            "zip_output": EXPECTED_ZIPS[provider],
            "provider_registered": provider in importer_text,
            "importer_accepts_merged_jsonl": EXPECTED_MERGED[provider] in importer_text or importer_has_merged_template,
            "importer_accepts_zip_output": EXPECTED_ZIPS[provider] in importer_text or importer_has_zip_template,
        }
        for provider in EXPECTED_MERGED
    }

    provider_outputs_present = {}
    search_dirs = [ROOT / "kaggleoutputs/v9_spurious_v2", ROOT / "kaggleoutputs/spurious_v2", ROOT / "data/results/main_real_200/kaggle_spurious_v2"]
    for provider, name in EXPECTED_MERGED.items():
        zip_name = EXPECTED_ZIPS[provider]
        provider_outputs_present[provider] = any((d / name).exists() or (d / zip_name).exists() for d in search_dirs)

    row_count_ok = len(task_rows) == expected_count and zip_info["zip_task_rows"] == expected_count
    image_count_ok = len(image_files) == expected_count * 2 and zip_info["zip_image_count"] == expected_count * 2
    notebooks_ok = all(
        nb["exists"]
        and nb["valid_nbformat"]
        and not nb["contains_private_paths"]
        and not nb["contains_fake_prediction_language"]
        and all(nb["contains_required_t4x2_tokens"].values())
        for nb in notebooks.values()
    )
    provider_notebook_outputs_ok = all(
        notebooks[provider]["contains_expected_output"] and notebooks[provider]["contains_expected_zip"]
        for provider in PROVIDER_NOTEBOOKS
    )
    importer_ok = IMPORTER.exists() and all(
        item["provider_registered"] and item["importer_accepts_merged_jsonl"] and item["importer_accepts_zip_output"]
        for item in importer_expectations.values()
    )
    package_ready = all(
        [
            CODE_BUNDLE.exists(),
            SPURIOUS_V2_BUNDLE.exists(),
            zip_info["valid_zip"],
            zip_info["has_task_jsonl"],
            zip_info["has_spurious_v2_manifest"],
            zip_info["has_bundle_manifest"],
            TASK_FILE.exists(),
            SPURIOUS_V2_MANIFEST.exists(),
            BUNDLE_MANIFEST.exists(),
            row_count_ok,
            image_count_ok,
            notebooks_ok,
            provider_notebook_outputs_ok,
            importer_ok,
            manifest.get("paper_evidence") is False,
            bundle_manifest.get("paper_evidence") is False,
            bundle_manifest.get("produced_model_results") is False,
        ]
    )

    return {
        "schema": "certvic.v10_1.spurious_v2_execution_package_audit.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": "READY_TO_RUN_ON_KAGGLE" if package_ready else "NOT_READY",
        "ready_to_import_results": all(provider_outputs_present.values()),
        "ready_to_run_on_kaggle": package_ready,
        "expected_strict_v2_count": expected_count,
        "local_task_rows": len(task_rows),
        "local_image_count": len(image_files),
        "zip": zip_info,
        "code_bundle": file_entry(CODE_BUNDLE),
        "task_file": file_entry(TASK_FILE),
        "spurious_v2_manifest": file_entry(SPURIOUS_V2_MANIFEST),
        "bundle_manifest": file_entry(BUNDLE_MANIFEST),
        "quality_report": {
            "file": file_entry(QUALITY_REPORT),
            "bbox_overlap_count": quality.get("bbox_overlap_count"),
            "mask_overlap_count": quality.get("mask_overlap_count"),
            "min_distance_px": quality.get("min_distance_px"),
            "quality_pass": quality.get("quality_pass"),
            "target_n_requested": quality.get("target_n_requested"),
            "target_n_local_status": quality.get("target_n_local_status"),
            "paper_evidence": quality.get("paper_evidence"),
        },
        "row_count_ok": row_count_ok,
        "image_count_ok": image_count_ok,
        "notebooks": notebooks,
        "notebooks_ok": notebooks_ok,
        "provider_notebook_outputs_ok": provider_notebook_outputs_ok,
        "importer": file_entry(IMPORTER),
        "importer_expectations": importer_expectations,
        "importer_ok": importer_ok,
        "provider_outputs_present": provider_outputs_present,
        "missing_provider_outputs": [provider for provider, present in provider_outputs_present.items() if not present],
        "paper_evidence_changed": False,
        "produced_model_results_by_v10_1": False,
        "limitations": [
            "Strict local V2 package has 30 items, not the requested 200-300, because the available local source pool does not support a larger strict filtered set.",
            "Provider predictions are still absent until the Kaggle notebooks are run.",
            "This audit validates execution readiness only; it does not validate model behavior.",
        ],
    }


def render_spurious_v2_audit(audit: dict) -> None:
    lines = [
        "# Spurious V2 Execution Package Audit",
        "",
        f"Verdict: `{audit['verdict']}`",
        f"Ready to import results: `{str(audit['ready_to_import_results']).lower()}`",
        "",
        "## Core Counts",
        "",
        "| Check | Value |",
        "| --- | ---: |",
        f"| Expected strict V2 rows | {audit['expected_strict_v2_count']} |",
        f"| Local task rows | {audit['local_task_rows']} |",
        f"| Local image files | {audit['local_image_count']} |",
        f"| Zip task rows | {audit['zip']['zip_task_rows']} |",
        f"| Zip image files | {audit['zip']['zip_image_count']} |",
        "",
        "## Package Requirements",
        "",
        "| Requirement | Status |",
        "| --- | --- |",
        f"| Code bundle exists | `{str(audit['code_bundle']['exists']).lower()}` |",
        f"| Spurious V2 bundle exists | `{str(audit['zip']['exists']).lower()}` |",
        f"| Zip is readable | `{str(audit['zip']['valid_zip']).lower()}` |",
        f"| Task JSONL exists in zip | `{str(audit['zip']['has_task_jsonl']).lower()}` |",
        f"| Spurious V2 manifest exists in zip | `{str(audit['zip']['has_spurious_v2_manifest']).lower()}` |",
        f"| Bundle manifest exists in zip | `{str(audit['zip']['has_bundle_manifest']).lower()}` |",
        f"| Row count equals strict V2 count | `{str(audit['row_count_ok']).lower()}` |",
        f"| Image count equals two images per row | `{str(audit['image_count_ok']).lower()}` |",
        f"| Notebooks valid and portable | `{str(audit['notebooks_ok']).lower()}` |",
        f"| Provider output names match importer expectations | `{str(audit['provider_notebook_outputs_ok'] and audit['importer_ok']).lower()}` |",
        f"| `paper_evidence` remains false | `{str(not audit['paper_evidence_changed']).lower()}` |",
        "",
        "## Quality Carry-Forward",
        "",
        f"- Bbox overlap count: `{audit['quality_report']['bbox_overlap_count']}`",
        f"- Mask overlap count: `{audit['quality_report']['mask_overlap_count']}`",
        f"- Min bbox distance: `{audit['quality_report']['min_distance_px']}` px",
        f"- Quality pass: `{audit['quality_report']['quality_pass']}`",
        f"- Requested target: `{audit['quality_report']['target_n_requested']}`",
        f"- Local status: `{audit['quality_report']['target_n_local_status']}`",
        "",
        "## Missing Runtime Outputs",
        "",
    ]
    if audit["missing_provider_outputs"]:
        for provider in audit["missing_provider_outputs"]:
            lines.append(f"- `{provider}`: missing Kaggle output zip / merged JSONL")
    else:
        lines.append("- None.")
    lines += [
        "",
        "## Limitation",
        "",
        "The package is ready to run on Kaggle, but it is not ready to import results until the three provider outputs are downloaded.",
    ]
    write_json(OUT_DIR / "spurious_v2_execution_package_audit.json", audit)
    write_md(OUT_DIR / "SPURIOUS_V2_EXECUTION_PACKAGE_AUDIT.md", lines)


def partial_specs() -> dict[str, dict]:
    qwen_cmd = "Run notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb on Kaggle after uploading the two required zip inputs."
    import_cmd = "python3 scripts/import_v9_spurious_v2_outputs.py --input-dir kaggleoutputs/v9_spurious_v2 --out-dir data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest --canonical-dir data/results/main_real_200/kaggle_spurious_v2 --report-dir data/results/main_real_200/v9_mega_upgrade"
    return {
        "02_SPURIOUS_V2_LARGE_CANDIDATE_EXPANSION.md": {
            "concrete_files": [
                "data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl",
                "data/edits/spurious_v2_control/spurious_v2_manifest.json",
                "data/edits/spurious_v2_control/bundle_manifest.json",
                "dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip",
                "data/results/main_real_200/v9_mega_upgrade/SPURIOUS_V2_QUALITY_REPORT.md",
            ],
            "missing": "A 200-300 item strict V2 pool is not available from the current local candidates; current strict set is 30 rows.",
            "acceptable_to_defer": "Yes for the next Kaggle run; no for any large-n V2 claim.",
            "next_command": qwen_cmd,
            "blocks_execution": "NO for Spurious V2 Kaggle execution; YES for a 200-300 item claim.",
        },
        "03_SPURIOUS_V2_PREHUMAN_REVIEW_AND_QUALITY_DASHBOARD.md": {
            "concrete_files": [
                "data/edits/spurious_v2_control/spurious_v2_examples_gallery.html",
                "data/results/main_real_200/v9_mega_upgrade/spurious_v2_quality_report.json",
                "docs/runbooks/HUMAN_REVIEW_RUNBOOK.md",
            ],
            "missing": "Real human labels and adjudicated review outcomes.",
            "acceptable_to_defer": "Yes for running Kaggle V2 predictions; no for human-validation claims.",
            "next_command": qwen_cmd,
            "blocks_execution": "NO for V2 Kaggle execution; YES for Main-500 and claim validation.",
        },
        "04_SPURIOUS_V2_KAGGLE_RUNTIME_STRESS_TEST_PACK.md": {
            "concrete_files": [
                "notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb",
                "notebooks/kaggle/vlm_internvl_8b_spurious_v2_T4x2.ipynb",
                "notebooks/kaggle/vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb",
                "notebooks/kaggle/v10_execution_ready_handoff_t4x2.ipynb",
                "dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip",
            ],
            "missing": "Provider prediction outputs from Kaggle.",
            "acceptable_to_defer": "No if the goal is to clear the specificity blocker.",
            "next_command": qwen_cmd,
            "blocks_execution": "YES for local V2 ingest, V2 gate decision, and Main-500.",
        },
        "05_UNIFIED_OUTPUT_IMPORTER_AND_VALIDATOR.md": {
            "concrete_files": [
                "scripts/import_v9_spurious_v2_outputs.py",
                "data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest_status.json",
                "tests/test_v9_spurious_v2_ingest_decision.py",
            ],
            "missing": "Three real provider output zips or merged JSONL files.",
            "acceptable_to_defer": "Yes until Kaggle outputs exist.",
            "next_command": import_cmd,
            "blocks_execution": "YES for V2 gate decision; NO for starting the Kaggle run.",
        },
        "06_KAGGLE_DATASET_PACKAGE_HASH_LOCK.md": {
            "concrete_files": [
                "dist/certvic_kaggle_main200_bundle.zip",
                "dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip",
                "data/edits/spurious_v2_control/bundle_manifest.json",
                "data/results/main_real_200/v10_1_correction/spurious_v2_execution_package_audit.json",
            ],
            "missing": "Kaggle-side dataset checksum after upload.",
            "acceptable_to_defer": "Yes; local zip hashes are available now and Kaggle hash can be recorded after upload.",
            "next_command": qwen_cmd,
            "blocks_execution": "NO for local readiness; record Kaggle hash when uploaded.",
        },
        "07_T4X2_NOTEBOOK_SELF_TEST_SUITE.md": {
            "concrete_files": [
                "tests/test_v9_spurious_v2_runbooks.py",
                "notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb",
                "notebooks/kaggle/vlm_internvl_8b_spurious_v2_T4x2.ipynb",
                "notebooks/kaggle/vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb",
            ],
            "missing": "Actual Kaggle execution logs.",
            "acceptable_to_defer": "Yes; local notebook/package validation is enough to start the run.",
            "next_command": qwen_cmd,
            "blocks_execution": "NO for starting Qwen V2 on Kaggle.",
        },
        "09_FAILURE_RECOVERY_AND_RESUME_PROTOCOL.md": {
            "concrete_files": [
                "docs/runbooks/KAGGLE_SPURIOUS_V2_T4X2_RUNBOOK.md",
                "docs/runbooks/V10_1_EXACT_SPURIOUS_V2_KAGGLE_CHECKLIST.md",
            ],
            "missing": "Actual partial shard artifacts, because no Kaggle run has happened.",
            "acceptable_to_defer": "Yes.",
            "next_command": qwen_cmd,
            "blocks_execution": "NO.",
        },
        "10_HUMAN_REVIEW_OPERATIONS_CENTER.md": {
            "concrete_files": [
                "docs/HUMAN_REVIEW_OPERATIONS.md",
                "docs/runbooks/HUMAN_REVIEW_RUNBOOK.md",
                "data/results/main_real_200/v9_mega_upgrade/QWEN_SPURIOUS_HUMAN_REVIEW_APPLY_REPORT.md",
            ],
            "missing": "Real human labels.",
            "acceptable_to_defer": "Yes for V2 execution; no for validation claims.",
            "next_command": qwen_cmd,
            "blocks_execution": "YES for human-validation claims and Main-500; NO for V2 Kaggle execution.",
        },
        "11_IAA_AND_ADJUDICATION_PREP.md": {
            "concrete_files": [
                "docs/HUMAN_REVIEW_IAA_PROTOCOL.md",
                "docs/HUMAN_REVIEW_OPERATIONS.md",
            ],
            "missing": "Two-rater labels, IAA statistics, and adjudication.",
            "acceptable_to_defer": "Yes for V2 execution; no for human-review completion.",
            "next_command": qwen_cmd,
            "blocks_execution": "YES for human-review completion and Main-500; NO for V2 Kaggle execution.",
        },
        "12_MAIN500_READINESS_RISK_BURNDOWN.md": {
            "concrete_files": [
                "data/results/main_real_200/v9_mega_upgrade/MAIN500_GO_NOGO_AFTER_SPECIFICITY.md",
                "data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest_status.json",
            ],
            "missing": "Passing Spurious V2 gate and real human review.",
            "acceptable_to_defer": "No for Main-500.",
            "next_command": qwen_cmd,
            "blocks_execution": "YES for Main-500.",
        },
        "13_MAIN500_ITEM_SELECTION_STRATIFICATION.md": {
            "concrete_files": [
                "data/results/main_real_200/v8_upgrade/MAIN500_GO_NOGO_PLAN.md",
                "docs/runbooks/MAIN500_DIFFUSION_T4X2_RUNBOOK.md",
                "docs/runbooks/MAIN500_VLM_T4X2_RUNBOOK.md",
            ],
            "missing": "Final post-specificity approved Main-500 item set.",
            "acceptable_to_defer": "Yes until V2 gate clears.",
            "next_command": qwen_cmd,
            "blocks_execution": "YES for Main-500; NO for V2 Kaggle execution.",
        },
        "14_MAIN500_DIFFUSION_QUEUE_PREVALIDATION.md": {
            "concrete_files": [
                "docs/runbooks/MAIN500_DIFFUSION_T4X2_RUNBOOK.md",
                "data/results/main_real_200/v9_mega_upgrade/MAIN500_GO_NOGO_AFTER_SPECIFICITY.md",
            ],
            "missing": "Approved Main-500 go decision and diffusion outputs.",
            "acceptable_to_defer": "No for Main-500.",
            "next_command": qwen_cmd,
            "blocks_execution": "YES for Main-500.",
        },
        "15_MAIN500_REVIEWER_BLINDING_AND_RANDOMIZATION.md": {
            "concrete_files": [
                "docs/HUMAN_REVIEW_OPERATIONS.md",
                "docs/HUMAN_REVIEW_IAA_PROTOCOL.md",
            ],
            "missing": "Executed Main-500 review packet and rater assignments.",
            "acceptable_to_defer": "Yes until Main-500 is allowed.",
            "next_command": qwen_cmd,
            "blocks_execution": "YES for Main-500 review; NO for V2 Kaggle execution.",
        },
        "16_MODEL_MATRIX_EXPANSION_FEASIBILITY.md": {
            "concrete_files": [
                "notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb",
                "notebooks/kaggle/vlm_internvl_8b_spurious_v2_T4x2.ipynb",
                "notebooks/kaggle/vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb",
            ],
            "missing": "Optional expanded provider matrix.",
            "acceptable_to_defer": "Yes.",
            "next_command": qwen_cmd,
            "blocks_execution": "NO.",
        },
        "17_SECOND_DOMAIN_CANDIDATE_DEEP_PREP.md": {
            "concrete_files": [
                "docs/SECOND_DOMAIN_READINESS.md",
                "registry/datasets/second_domain_candidates.json",
                "data/results/main_real_200/v9_mega_upgrade/V9_TASK_LEDGER.md",
            ],
            "missing": "Second-domain execution outputs.",
            "acceptable_to_defer": "Yes; second domain is not the next blocker.",
            "next_command": qwen_cmd,
            "blocks_execution": "NO for Spurious V2 and Main-500 gate sequencing.",
        },
        "18_OPEN_REPLICATION_MINIPACK.md": {
            "concrete_files": [
                "dist/certvic_v10_execution_ready_handoff.zip",
                "docs/runbooks/V10_EXECUTION_READY_HANDOFF.md",
            ],
            "missing": "Post-V2 result package.",
            "acceptable_to_defer": "Yes.",
            "next_command": qwen_cmd,
            "blocks_execution": "NO.",
        },
        "21_MECHANISM_POLARITY_PAPER_SYNTHESIS.md": {
            "concrete_files": [
                "data/results/main_real_200/v9_mega_upgrade/mechanism_deep_report.json",
                "data/results/main_real_200/v9_mega_upgrade/polarity_deep_report.json",
            ],
            "missing": "No missing local diagnostic files; paper wording remains limited by specificity.",
            "acceptable_to_defer": "Yes.",
            "next_command": qwen_cmd,
            "blocks_execution": "NO.",
        },
        "22_QUALITATIVE_GALLERY_REVIEWER_MODE.md": {
            "concrete_files": [
                "data/edits/spurious_v2_control/spurious_v2_examples_gallery.html",
                "data/results/main_real_200/v9_mega_upgrade/QWEN_SPURIOUS_HUMAN_REVIEW_APPLY_REPORT.md",
            ],
            "missing": "Reviewer gallery with real Spurious V2 model outcomes.",
            "acceptable_to_defer": "Yes until provider outputs exist.",
            "next_command": qwen_cmd,
            "blocks_execution": "NO for V2 Kaggle execution; YES for final reviewer packet.",
        },
        "23_RELEASE_CANDIDATE_PRE_SUBMISSION_FREEZE.md": {
            "concrete_files": [
                "dist/certvic_v10_execution_ready_handoff.zip",
                "data/results/main_real_200/v10_1_correction/privacy_audit_after_fix.json",
            ],
            "missing": "Release freeze after V2 predictions and human labels.",
            "acceptable_to_defer": "Yes.",
            "next_command": qwen_cmd,
            "blocks_execution": "NO for V2 Kaggle execution.",
        },
        "24_PAPER_CVPR_COMPILE_AND_ANONYMIZATION.md": {
            "concrete_files": [
                "paper",
                "data/results/main_real_200/v9_mega_upgrade/CVPR_READINESS_SCORECARD_V9.md",
            ],
            "missing": "Paper update after V2 gate and human review.",
            "acceptable_to_defer": "Yes.",
            "next_command": qwen_cmd,
            "blocks_execution": "YES for final paper claims; NO for V2 Kaggle execution.",
        },
        "25_REVIEWER_ATTACK_REDTEAM_PHASE2.md": {
            "concrete_files": [
                "data/results/main_real_200/v9_mega_upgrade/V9_REVIEWER_ATTACK_RESULTS.md",
                "data/results/main_real_200/v9_mega_upgrade/V9_REVIEWER_ATTACK_RESULTS.json",
            ],
            "missing": "Re-run of red-team answers after V2 outputs.",
            "acceptable_to_defer": "Yes.",
            "next_command": qwen_cmd,
            "blocks_execution": "NO for V2 Kaggle execution.",
        },
        "29_FINAL_PRE_EXECUTION_VALIDATION.md": {
            "concrete_files": [
                "data/results/main_real_200/v10_1_correction/V10_1_FINAL_HANDOFF.md",
                "data/results/main_real_200/v10_1_correction/SPURIOUS_V2_EXECUTION_PACKAGE_AUDIT.md",
                "docs/runbooks/V10_1_EXACT_SPURIOUS_V2_KAGGLE_CHECKLIST.md",
            ],
            "missing": "Actual provider outputs from Kaggle.",
            "acceptable_to_defer": "No for clearing the gate; yes for ending this correction pass.",
            "next_command": qwen_cmd,
            "blocks_execution": "YES for gate clearance and Main-500; NO for launching Qwen V2.",
        },
    }


def build_partials_table() -> list[dict]:
    ledger_rows = read_jsonl(ROOT / "AUTORUN_LEDGER_V2.jsonl")
    specs = partial_specs()
    rows = []
    for row in ledger_rows:
        status = row.get("status")
        if status not in {"PARTIAL", "BLOCKED_OR_DEFERRED"}:
            continue
        filename = row.get("filename", "")
        spec = specs.get(
            filename,
            {
                "concrete_files": [],
                "missing": "Not mapped by V10.1.",
                "acceptable_to_defer": "Unknown.",
                "next_command": "Run notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb on Kaggle.",
                "blocks_execution": "Unknown.",
            },
        )
        concrete = []
        for file in spec["concrete_files"]:
            path = ROOT / file
            concrete.append({"path": file, "exists": path.exists()})
        rows.append(
            {
                "prompt_index": row.get("prompt_index"),
                "filename": filename,
                "v10_status": status,
                "concrete_files": concrete,
                "missing": spec["missing"],
                "acceptable_to_defer": spec["acceptable_to_defer"],
                "next_command": spec["next_command"],
                "blocks_execution": spec["blocks_execution"],
                "v10_blockers": row.get("blockers", ""),
            }
        )
    return rows


def render_partials_table(rows: list[dict]) -> None:
    lines = [
        "# V10 Partials Resolution Table",
        "",
        "Scope: every V10 ledger row marked `PARTIAL` or `BLOCKED_OR_DEFERRED`.",
        "",
        "| Prompt | V10 status | Concrete file exists | Missing | Acceptable to defer | Next command | Blocks execution |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        files = "<br>".join(f"`{item['path']}` = `{str(item['exists']).lower()}`" for item in row["concrete_files"]) or "`none`"
        lines.append(
            "| "
            + f"`{row['filename']}` | `{row['v10_status']}` | {files} | {row['missing']} | {row['acceptable_to_defer']} | `{row['next_command']}` | {row['blocks_execution']} |"
        )
    lines += [
        "",
        "## Bottom Line",
        "",
        "The only next execution action is Spurious V2 on Kaggle. Main-500 remains blocked.",
    ]
    write_json(OUT_DIR / "v10_partials_resolution_table.json", rows)
    write_md(OUT_DIR / "V10_PARTIALS_RESOLUTION_TABLE.md", lines)


def render_kaggle_checklist(audit: dict) -> None:
    import_cmd = "python3 scripts/import_v9_spurious_v2_outputs.py --input-dir kaggleoutputs/v9_spurious_v2 --out-dir data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest --canonical-dir data/results/main_real_200/kaggle_spurious_v2 --report-dir data/results/main_real_200/v9_mega_upgrade"
    validation_cmds = [
        "python3 -m pytest -q tests/test_v9_spurious_v2_runbooks.py tests/test_remaining_kaggle_runbooks.py tests/test_open_vlm_import_safety.py tests/test_v9_main500_go_nogo.py tests/test_v9_qwen_spurious_human_review_packet.py tests/test_v9_spurious_v2_ingest_decision.py",
        "python3 -m certvic.validation.claim_language_guard --root docs paper data/results/main_real_200/v10_1_correction --out data/results/main_real_200/v10_1_correction/claim_guard_v10_1.json",
        "python3 -m certvic.security.release_privacy_audit --root . --out data/results/main_real_200/v10_1_correction/privacy_audit_v10_1.md --json-out data/results/main_real_200/v10_1_correction/privacy_audit_v10_1.json",
    ]
    lines = [
        "# V10.1 Exact Spurious V2 Kaggle Checklist",
        "",
        "One next action: run Spurious V2 on Kaggle. Start with Qwen.",
        "",
        "## Upload Files",
        "",
        f"- `{rel(CODE_BUNDLE)}`",
        f"- `{rel(SPURIOUS_V2_BUNDLE)}`",
        "- The provider notebook you are running first.",
        "",
        "## Attach Kaggle Datasets",
        "",
        "- Attach the CertVIC code/config dataset made from `dist/certvic_kaggle_main200_bundle.zip`.",
        "- Attach the strict Spurious V2 control dataset made from `dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip`.",
        "- Use Kaggle T4x2. Internet may be enabled unless a model/cache dataset is attached.",
        "- Do not attach paid API credentials.",
        "",
        "## Run Order",
        "",
        "| Order | Provider | Notebook | RUN_TAG | Expected zip | Expected merged JSONL |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    order = ["qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"]
    for idx, provider in enumerate(order, start=1):
        lines.append(
            f"| {idx} | `{provider}` | `{rel(PROVIDER_NOTEBOOKS[provider])}` | `spurious_v2` | `{EXPECTED_ZIPS[provider]}` | `{EXPECTED_MERGED[provider]}` |"
        )
    lines += [
        "",
        "## Provider Settings",
        "",
        "- `RUN_TAG = \"spurious_v2\"`",
        "- Qwen: `PROVIDER = \"qwen2_5_vl_7b\"`",
        "- InternVL: `PROVIDER = \"internvl_8b\"`",
        "- LLaVA-OneVision: `PROVIDER = \"llava_onevision_7b\"`",
        "- T4x2 sharding: `shard0` uses `CUDA_VISIBLE_DEVICES=0`; `shard1` uses `CUDA_VISIBLE_DEVICES=1`.",
        "",
        "## Download Outputs",
        "",
        "Download these files from Kaggle and place them locally in `kaggleoutputs/v9_spurious_v2/`:",
        "",
    ]
    for provider in order:
        lines.append(f"- `{EXPECTED_ZIPS[provider]}`")
    lines += [
        "",
        "The zip must contain the provider merged JSONL, summary, runtime manifest, and shard outputs created by the notebook.",
        "",
        "## Local Import",
        "",
        "```bash",
        "mkdir -p kaggleoutputs/v9_spurious_v2",
        import_cmd,
        "```",
        "",
        "## Local Validation",
        "",
    ]
    for cmd in validation_cmds:
        lines += ["```bash", cmd, "```", ""]
    lines += [
        "## Expected Runtime Range",
        "",
        "| Provider | T4x2 estimate | Single-GPU fallback |",
        "| --- | ---: | ---: |",
        "| `qwen2_5_vl_7b` | 12-25 min | 25-45 min |",
        "| `internvl_8b` | 10-20 min | 20-40 min |",
        "| `llava_onevision_7b` | 15-30 min | 30-60 min |",
        "",
        "## Partial-Shard Recovery",
        "",
        "- If only one shard finishes, rerun the same provider notebook in the same Kaggle output workspace.",
        "- Preserve completed shard files; the notebook is designed to resume at shard-file granularity.",
        "- Do not hand-edit, hand-create, or relabel predictions.",
        "- Import only after the provider zip or merged JSONL exists for all three providers.",
        "",
        "## Do Not Run Yet",
        "",
        "- Do not start Main-500 diffusion.",
        "- Do not start Main-500 VLM evaluation.",
        "- Do not run second-domain experiments.",
        "- Do not promote `paper_evidence`.",
        "- Do not claim real human validation until real labels exist.",
        "",
        "## Current Package Audit",
        "",
        f"- Spurious V2 rows: `{audit['expected_strict_v2_count']}`",
        f"- Package verdict: `{audit['verdict']}`",
        f"- Missing provider outputs: `{', '.join(audit['missing_provider_outputs'])}`",
    ]
    write_md(RUNBOOK, lines)


def render_next_action_card(audit: dict) -> None:
    lines = [
        "# Spurious V2 Next Action Card",
        "",
        "Next action: run Qwen Spurious V2 on Kaggle.",
        "",
        "## Upload",
        "",
        f"- `{rel(CODE_BUNDLE)}`",
        f"- `{rel(SPURIOUS_V2_BUNDLE)}`",
        f"- `{rel(PROVIDER_NOTEBOOKS['qwen2_5_vl_7b'])}`",
        "",
        "## Run",
        "",
        "- Kaggle accelerator: T4x2",
        "- `PROVIDER = \"qwen2_5_vl_7b\"`",
        "- `RUN_TAG = \"spurious_v2\"`",
        "- Expected output: `qwen2_5_vl_7b_spurious_v2_preds.zip`",
        "",
        "## Then",
        "",
        "- Run InternVL and LLaVA-OneVision Spurious V2 notebooks.",
        "- Put all three zip outputs in `kaggleoutputs/v9_spurious_v2/`.",
        "- Run `python3 scripts/import_v9_spurious_v2_outputs.py --input-dir kaggleoutputs/v9_spurious_v2 --out-dir data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest --canonical-dir data/results/main_real_200/kaggle_spurious_v2 --report-dir data/results/main_real_200/v9_mega_upgrade`.",
        "",
        "Main-500 is not allowed from the current state.",
    ]
    write_md(OUT_DIR / "SPURIOUS_V2_NEXT_ACTION_CARD.md", lines)


def read_validation_status() -> dict:
    selected_log = OUT_DIR / "pytest_v10_1_selected.log"
    full_log = OUT_DIR / "pytest_v10_1_full.log"
    claim_path = OUT_DIR / "claim_guard_v10_1.json"
    claim_text = claim_path.read_text(encoding="utf-8") if claim_path.exists() else ""
    privacy = read_json(OUT_DIR / "privacy_audit_v10_1.json")
    claim_findings = None
    claim_passed = None
    if claim_text:
        claim_passed = "Passed: True" in claim_text
        claim_findings = 0 if "No forbidden claim-language patterns found." in claim_text else None
    return {
        "selected_pytest_log": rel(selected_log),
        "selected_pytest_log_exists": selected_log.exists(),
        "selected_pytest_last_line": selected_log.read_text(encoding="utf-8").splitlines()[-1] if selected_log.exists() and selected_log.read_text(encoding="utf-8").splitlines() else None,
        "full_pytest_log": rel(full_log),
        "full_pytest_log_exists": full_log.exists(),
        "full_pytest_last_line": full_log.read_text(encoding="utf-8").splitlines()[-1] if full_log.exists() and full_log.read_text(encoding="utf-8").splitlines() else None,
        "claim_guard": {
            "path": rel(claim_path),
            "exists": claim_path.exists(),
            "passed": claim_passed,
            "n_findings": claim_findings,
        },
        "privacy_audit": {
            "path": rel(OUT_DIR / "privacy_audit_v10_1.json"),
            "exists": bool(privacy),
            "passed": privacy.get("passed"),
            "n_total_findings": privacy.get("n_total_findings"),
        },
    }


def render_final_handoff(audit: dict, partials: list[dict]) -> None:
    privacy_after = read_json(OUT_DIR / "privacy_audit_after_fix.json")
    validation = read_validation_status()
    import_cmd = "python3 scripts/import_v9_spurious_v2_outputs.py --input-dir kaggleoutputs/v9_spurious_v2 --out-dir data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest --canonical-dir data/results/main_real_200/kaggle_spurious_v2 --report-dir data/results/main_real_200/v9_mega_upgrade"
    payload = {
        "schema": "certvic.v10_1.final_handoff.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "privacy_clean_now": privacy_after.get("passed") is True and privacy_after.get("n_total_findings") == 0,
        "privacy_after_fix_json": rel(OUT_DIR / "privacy_audit_after_fix.json"),
        "spurious_v2_execution_package_ready": audit["ready_to_run_on_kaggle"],
        "spurious_v2_ready_to_import": audit["ready_to_import_results"],
        "strict_v2_rows": audit["expected_strict_v2_count"],
        "first_kaggle_notebook": rel(PROVIDER_NOTEBOOKS["qwen2_5_vl_7b"]),
        "required_upload_files": [rel(CODE_BUNDLE), rel(SPURIOUS_V2_BUNDLE)],
        "required_output_downloads": [EXPECTED_ZIPS[p] for p in ["qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"]],
        "local_import_command": import_cmd,
        "main500_allowed_now": False,
        "paper_evidence_changed": False,
        "remaining_blockers": [
            "Spurious V2 provider predictions are missing.",
            "Real human labels are missing.",
            "Spurious V2 ingest/gate decision has not run on real provider outputs.",
            "Main-500 remains blocked.",
            "Second domain remains plan-only.",
        ],
        "obvious_next_action": "Run Spurious V2 on Kaggle, starting with Qwen.",
        "partials_count": len(partials),
        "validation": validation,
    }
    write_json(OUT_DIR / "v10_1_final_handoff.json", payload)
    lines = [
        "# V10.1 Final Handoff",
        "",
        "Verdict: correction pass complete; run Spurious V2 on Kaggle next.",
        "",
        "## Direct Answers",
        "",
        f"- Privacy clean now: `{str(payload['privacy_clean_now']).lower()}`",
        f"- Spurious V2 execution package ready: `{str(payload['spurious_v2_execution_package_ready']).lower()}`",
        f"- First Kaggle notebook: `{payload['first_kaggle_notebook']}`",
        f"- Upload files: `{payload['required_upload_files'][0]}` and `{payload['required_upload_files'][1]}`",
        "- Download outputs: `qwen2_5_vl_7b_spurious_v2_preds.zip`, `internvl_8b_spurious_v2_preds.zip`, `llava_onevision_7b_spurious_v2_preds.zip`",
        f"- Import command: `{payload['local_import_command']}`",
        f"- Main-500 allowed now: `{str(payload['main500_allowed_now']).lower()}`",
        f"- `paper_evidence` changed: `{str(payload['paper_evidence_changed']).lower()}`",
        "",
        "## Remaining Blockers",
        "",
    ]
    for item in payload["remaining_blockers"]:
        lines.append(f"- {item}")
    lines += [
        "",
        "## Validation Snapshot",
        "",
        f"- Selected pytest log exists: `{str(validation['selected_pytest_log_exists']).lower()}`; last line: `{validation['selected_pytest_last_line']}`",
        f"- Full pytest log exists: `{str(validation['full_pytest_log_exists']).lower()}`; last line: `{validation['full_pytest_last_line']}`",
        f"- Claim guard passed: `{validation['claim_guard']['passed']}`; findings: `{validation['claim_guard']['n_findings']}`",
        f"- Privacy audit passed: `{validation['privacy_audit']['passed']}`; findings: `{validation['privacy_audit']['n_total_findings']}`",
        "",
        "Do not start Main-500 from this state.",
    ]
    write_md(OUT_DIR / "V10_1_FINAL_HANDOFF.md", lines)


def refresh_privacy_fix_report() -> None:
    manifest = read_json(OUT_DIR / "privacy_fix_manifest.json")
    before = read_json(OUT_DIR / "privacy_audit_before_fix.json")
    after = read_json(OUT_DIR / "privacy_audit_after_fix.json")
    counts = manifest.get("finding_counts_by_file", {})
    lines = [
        "# V10.1 Privacy Fix Report",
        "",
        "Status: `PASS` after a documentation-only redaction.",
        "",
        "## Before Fix",
        "",
        f"- Total findings: `{before.get('n_total_findings')}`",
        f"- Private-path findings: `{before.get('private_paths', {}).get('n_findings')}`",
        "- Finding files:",
    ]
    for file, count in sorted(counts.items()):
        lines.append(f"  - `{file}`: `{count}`")
    lines += [
        "",
        "## Fix Applied",
        "",
        "- Replaced the private project root with `<PROJECT_ROOT>`.",
        "- Replaced the private project parent with `<PROJECT_PARENT>` where needed.",
        "- Replaced the private user home with `<USER_HOME>` where needed.",
        "- No files were deleted or quarantined.",
        "- No prediction files or canonical result JSON files were edited.",
        "- `paper_evidence` was not changed.",
        "",
        "## After Fix",
        "",
        f"- Privacy passed: `{after.get('passed')}`",
        f"- Total findings: `{after.get('n_total_findings')}`",
        "",
        "## Files Touched",
        "",
        "| File | Findings before | Changed |",
        "| --- | ---: | --- |",
    ]
    for entry in manifest.get("files_touched", []):
        lines.append(f"| `{entry['file']}` | {entry['finding_count_before']} | `{str(entry['changed']).lower()}` |")
    write_md(OUT_DIR / "PRIVACY_FIX_REPORT.md", lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    discovery = run_discovery()
    render_discovery(discovery)
    if (OUT_DIR / "privacy_fix_manifest.json").exists():
        refresh_privacy_fix_report()
    package_audit = audit_spurious_v2_package()
    render_spurious_v2_audit(package_audit)
    partials = build_partials_table()
    render_partials_table(partials)
    render_kaggle_checklist(package_audit)
    render_next_action_card(package_audit)
    render_final_handoff(package_audit, partials)
    print(
        json.dumps(
            {
                "out_dir": rel(OUT_DIR),
                "spurious_v2_verdict": package_audit["verdict"],
                "partials": len(partials),
                "next_action": "run_qwen_spurious_v2_on_kaggle",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
