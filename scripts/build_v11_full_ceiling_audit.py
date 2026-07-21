#!/usr/bin/env python3
"""Build the deterministic, evidence-bounded CertVIC V11 audit packet.

The builder reads only local artifacts.  It never runs a model, invents a human
judgment, or promotes a planned artifact to evidence.  Paths written to the
packet are repository-relative and the root is represented as ``<PROJECT_ROOT>``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import random
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "v11_full_ceiling_audit"
ROOT_TOKEN = "<PROJECT_ROOT>"

EVIDENCE_CLASSES = {
    "REAL_OBSERVED_EVIDENCE",
    "DERIVED_FROM_REAL_EVIDENCE",
    "DIAGNOSTIC_ONLY",
    "MACHINE_ASSISTED_PRELIMINARY",
    "HUMAN_REVIEW_PENDING",
    "PLANNED_NOT_EXECUTED",
    "SYNTHETIC_TEST_FIXTURE",
    "DEPRECATED_OR_STALE",
    "UNKNOWN_REQUIRES_AUDIT",
}

EVIDENCE_FIELDS = [
    "artifact_id",
    "artifact_path",
    "experiment_family",
    "model_provider",
    "dataset_domain",
    "run_tag",
    "item_count",
    "evidence_class",
    "raw_or_derived_status",
    "upstream_source",
    "sha256",
    "timestamp",
    "validation_status",
    "paper_claim_eligibility",
    "paper_evidence",
    "diagnostic_only",
    "human_reviewed",
    "known_limitations",
    "canonical_status",
]

REQUIRED_REPORTS = [
    "V11_AUDIT_SESSION_MANIFEST.md",
    "CERTVIC_REPOSITORY_FORENSIC_INVENTORY.md",
    "CERTVIC_CANONICAL_ARTIFACT_INDEX.md",
    "CERTVIC_EVIDENCE_LEDGER.csv",
    "CERTVIC_EVIDENCE_LEDGER.json",
    "CERTVIC_GATE_LEDGER.csv",
    "CERTVIC_BLOCKER_REGISTER.csv",
    "CERTVIC_CLAIM_LEDGER.md",
    "SOFTWARE_VALIDATION_AND_REPAIR_REPORT.md",
    "SCIENTIFIC_VALIDITY_AUDIT.md",
    "STATISTICAL_AUDIT_AND_POWER_PLAN.md",
    "QWEN_12_FAILURE_FORENSIC_AUDIT.md",
    "SPURIOUS_V2_AND_V2_LARGE_READINESS.md",
    "HUMAN_REVIEW_OPERATIONS_AND_BLINDING.md",
    "MAIN500_DESIGN_LOCK_AND_GO_NOGO.md",
    "SECOND_DOMAIN_DECISION.md",
    "MODEL_MATRIX_DECISION.md",
    "PAPER_AND_NOVELTY_AUDIT.md",
    "REVIEWER_RED_TEAM_V11.md",
    "REPRODUCIBILITY_AND_RELEASE_AUDIT.md",
    "VENUE_CEILING_AND_RESEARCH_ROADMAP.md",
    "V11_CHANGE_MANIFEST.csv",
    "V11_COMMAND_AND_EXIT_CODE_LOG.md",
    "V11_FINAL_VALIDATION.md",
    "CERTVIC_V11_MASTER_HANDOFF.md",
]

PROVIDERS = {
    "qwen2_5_vl_7b": {
        "display": "Qwen2.5-VL-7B",
        "model": "Qwen/Qwen2.5-VL-7B-Instruct",
        "presence": "data/results/main_real_200/raw_predictions/"
        "presence__pred_qwen2_5_vl_7b_merged.jsonl",
        "spurious": "data/results/main_real_200/kaggle_spurious/"
        "pred_qwen2_5_vl_7b_spurious_merged.jsonl",
        "pilot_report": "data/results/main_real_200/pilot_report/pilot_result.json",
    },
    "internvl_8b": {
        "display": "InternVL2-8B",
        "model": "OpenGVLab/InternVL2-8B",
        "presence": "data/results/main_real_200/raw_predictions__internvl_8b/"
        "presence__pred_internvl_8b_presence_merged.jsonl",
        "spurious": "data/results/main_real_200/kaggle_spurious/"
        "pred_internvl_8b_spurious_merged.jsonl",
        "pilot_report": "data/results/main_real_200/"
        "pilot_report__internvl_8b/pilot_result.json",
    },
    "llava_onevision_7b": {
        "display": "LLaVA-OneVision-7B",
        "model": "llava-hf/llava-onevision-qwen2-7b-ov-hf",
        "presence": "data/results/main_real_200/raw_predictions__llava_onevision_7b/"
        "presence__pred_llava_onevision_7b_presence_merged.jsonl",
        "spurious": "data/results/main_real_200/kaggle_spurious/"
        "pred_llava_onevision_7b_spurious_merged.jsonl",
        "pilot_report": "data/results/main_real_200/"
        "pilot_report__llava_onevision_7b/pilot_result.json",
    },
}


def rel(path: Path | str) -> str:
    """Return a stable repository-relative path."""
    path = Path(path)
    if path.is_absolute():
        path = path.relative_to(ROOT)
    return path.as_posix()


def sha256(path: Path | str) -> str:
    path = ROOT / path if not Path(path).is_absolute() else Path(path)
    if not path.is_file():
        return "MISSING"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def timestamp(path: Path | str) -> str:
    path = ROOT / path if not Path(path).is_absolute() else Path(path)
    if not path.exists():
        return "MISSING"
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


def read_json(path: Path | str) -> Any:
    path = ROOT / path if not Path(path).is_absolute() else Path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path | str) -> list[dict[str, Any]]:
    path = ROOT / path if not Path(path).is_absolute() else Path(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def markdown_table(headers: list[str], rows: Iterable[Iterable[Any]]) -> str:
    def cell(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    output = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    output.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)
    return "\n".join(output)


def paired_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    pairs: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        pairs.setdefault(str(row["item_id"]), {})[str(row["image_variant"])] = row
    return pairs


def flip_ids(rows: list[dict[str, Any]]) -> set[str]:
    result: set[str] = set()
    for item_id, pair in paired_rows(rows).items():
        original = pair.get("original")
        edited = pair.get("edited")
        if not original or not edited:
            continue
        if not original.get("parse_ok") or not edited.get("parse_ok"):
            continue
        if original.get("parsed_answer") != edited.get("parsed_answer"):
            result.add(item_id)
    return result


def exact_mcnemar_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(0, min(b, c) + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def bootstrap_risk_difference(
    ids: list[str], left: set[str], right: set[str], *, seed: int = 11011, reps: int = 20_000
) -> tuple[float, float]:
    rng = random.Random(seed)
    values = [int(item in left) - int(item in right) for item in ids]
    n = len(values)
    samples = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return samples[int(0.025 * reps)], samples[int(0.975 * reps) - 1]


def inventory(out: Path) -> dict[str, Any]:
    files: list[Path] = []
    dirs: set[Path] = set()
    for base, dirnames, filenames in os.walk(ROOT):
        base_path = Path(base)
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in {".git", ".pytest_cache", ".ruff_cache", "__pycache__"}
            and not (base_path / name).is_relative_to(out)
        )
        if base_path.is_relative_to(out):
            continue
        dirs.add(base_path)
        files.extend(base_path / name for name in sorted(filenames))
    regular = [path for path in files if path.is_file()]
    by_hash: dict[tuple[int, str], list[Path]] = {}
    for path in regular:
        size = path.stat().st_size
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        by_hash.setdefault((size, digest), []).append(path)
    duplicate_groups = [group for group in by_hash.values() if len(group) > 1]
    redundant_bytes = sum(group[0].stat().st_size * (len(group) - 1) for group in duplicate_groups)
    large_files = sorted(regular, key=lambda path: path.stat().st_size, reverse=True)[:15]
    empty_paths = sorted(rel(path) for path in regular if path.stat().st_size == 0)
    broken_symlinks = sorted(
        rel(path) for path in files if path.is_symlink() and not path.exists()
    )
    return {
        "files": len(regular),
        "directories": max(0, len(dirs) - 1),
        "bytes": sum(path.stat().st_size for path in regular),
        "empty_files": sum(path.stat().st_size == 0 for path in regular),
        "empty_paths": empty_paths,
        "symlinks": sum(path.is_symlink() for path in files),
        "broken_symlinks": broken_symlinks,
        "duplicate_groups": len(duplicate_groups),
        "redundant_copies": sum(len(group) - 1 for group in duplicate_groups),
        "redundant_bytes": redundant_bytes,
        "large_files": [
            {"path": rel(path), "bytes": path.stat().st_size} for path in large_files
        ],
        "python_modules": sum(
            path.suffix == ".py" and path.is_relative_to(ROOT / "certvic") for path in regular
        ),
        "test_files": sum(
            path.suffix == ".py"
            and path.name.startswith("test_")
            and path.is_relative_to(ROOT / "tests")
            for path in regular
        ),
        "scripts": sum(path.suffix == ".py" and path.is_relative_to(ROOT / "scripts") for path in regular),
        "notebooks": sum(path.suffix == ".ipynb" for path in regular),
        "configs": sum(path.is_relative_to(ROOT / "configs") and path.is_file() for path in regular),
        "paper_files": sum(path.is_relative_to(ROOT / "paper") and path.is_file() for path in regular),
        "docs": sum(path.is_relative_to(ROOT / "docs") and path.is_file() for path in regular),
        "prompt_pack_files": sum(
            "prompt" in path.as_posix().lower() and path.is_file() for path in regular
        ),
    }


def dependency_versions() -> dict[str, str]:
    packages = [
        "numpy",
        "pandas",
        "pillow",
        "pydantic",
        "pyyaml",
        "scikit-learn",
        "matplotlib",
        "pytest",
        "ruff",
        "nbformat",
        "scipy",
        "confseq",
    ]
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not installed"
    return versions


def physical_memory_gib() -> str:
    try:
        pages = int(os.sysconf("SC_PHYS_PAGES"))
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        return f"{pages * page_size / (1024**3):.1f} GiB"
    except (ValueError, OSError, AttributeError):
        return "unknown"


def load_state(out: Path) -> dict[str, Any]:
    main_tasks_path = "data/results/main_real_200/pilot_eval_tasks_reviewed_v2.jsonl"
    taskitems_path = "data/results/main_real_200/pilot_eval_taskitems_v2.jsonl"
    v1_tasks_path = "data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl"
    v2_tasks_path = "data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl"
    v2_candidate_audit_path = (
        "data/results/main_real_200/v8_1_qwen_spurious_forensics/"
        "qwen_spurious_all_items.jsonl"
    )
    main_tasks = read_jsonl(main_tasks_path)
    v1_tasks = read_jsonl(v1_tasks_path)
    v2_tasks = read_jsonl(v2_tasks_path)
    v2_candidate_audit = read_jsonl(v2_candidate_audit_path)
    failures: dict[str, set[str]] = {}
    raw_rows: dict[str, dict[str, list[dict[str, Any]]]] = {}
    pilot_metrics: dict[str, dict[str, Any]] = {}
    for provider, spec in PROVIDERS.items():
        presence_rows = read_jsonl(spec["presence"])
        spurious_rows = read_jsonl(spec["spurious"])
        raw_rows[provider] = {"presence": presence_rows, "spurious": spurious_rows}
        failures[provider] = flip_ids(spurious_rows)
        report = read_json(spec["pilot_report"])
        intervention = report["presence_intervention"]
        summary = intervention.get("summary", intervention)
        certification = intervention["certification"]
        pilot_metrics[provider] = {
            "n": int(summary["n"]),
            "a": float(summary["original_accuracy"]),
            "p": float(summary["consistency_rate"]),
            "gap": float(summary.get("gap", summary["intervention_consistency_gap"])),
            "cs_lb": float(certification["confidence_sequence"]["latest"]["lo"]),
            "certified": bool(certification.get("certified", False)),
        }
    ids = sorted(task["item_id"] for task in v1_tasks)
    comparisons: list[dict[str, Any]] = []
    pairs = [
        ("qwen2_5_vl_7b", "internvl_8b"),
        ("qwen2_5_vl_7b", "llava_onevision_7b"),
        ("internvl_8b", "llava_onevision_7b"),
    ]
    for index, (left, right) in enumerate(pairs):
        left_set, right_set = failures[left], failures[right]
        b = len(left_set - right_set)
        c = len(right_set - left_set)
        lo, hi = bootstrap_risk_difference(ids, left_set, right_set, seed=11011 + index)
        comparisons.append(
            {
                "left_provider": left,
                "right_provider": right,
                "n": len(ids),
                "left_flips": len(left_set),
                "right_flips": len(right_set),
                "risk_difference": (len(left_set) - len(right_set)) / len(ids),
                "left_only": b,
                "right_only": c,
                "exact_mcnemar_p": exact_mcnemar_p(b, c),
                "bootstrap_seed": 11011 + index,
                "bootstrap_repetitions": 20_000,
                "bootstrap_95_lo": lo,
                "bootstrap_95_hi": hi,
                "analysis_status": "retrospective_exploratory",
                "paper_evidence": False,
            }
        )
    v2_ids = {row["item_id"] for row in v2_tasks}
    v1_ids = {row["item_id"] for row in v1_tasks}
    qwen_failures = failures["qwen2_5_vl_7b"]
    v2_quality = read_json("data/results/main_real_200/v9_mega_upgrade/spurious_v2_quality_report.json")
    v2_bundle = read_json("data/edits/spurious_v2_control/bundle_manifest.json")
    main_detectability_path = out / "analysis" / "main91_detectability" / "detectability_summary.json"
    main_detectability = read_json(main_detectability_path) if main_detectability_path.is_file() else None
    v2_detectability_path = (
        out / "analysis" / "v2_retrospective_detectability" / "detectability_summary.json"
    )
    v2_detectability = read_json(v2_detectability_path) if v2_detectability_path.is_file() else None
    v1_detectability = read_json(
        "data/results/spurious_flip_control/edit_detectability/detectability_summary.json"
    )
    review_manifest_path = out / "human_review_packet" / "packet_manifest.json"
    review_manifest = read_json(review_manifest_path) if review_manifest_path.is_file() else None
    second_domain_registry = read_json("registry/datasets/second_domain_candidates.json")
    main_bundle_manifest = read_json("dist/certvic_kaggle_main200_bundle_manifest.json")
    session2_path = ROOT / "dist" / "certvic_main200_session2_data.zip"
    session2_private_occurrences = 0
    if session2_path.is_file():
        with zipfile.ZipFile(session2_path) as archive:
            for name in archive.namelist():
                if name.endswith("/"):
                    continue
                session2_private_occurrences += archive.read(name).count(b"/" + b"Users/")
    return {
        "out": out,
        "main_tasks": main_tasks,
        "v1_tasks": v1_tasks,
        "v2_tasks": v2_tasks,
        "v2_candidate_audit": v2_candidate_audit,
        "raw_rows": raw_rows,
        "failures": failures,
        "pilot_metrics": pilot_metrics,
        "comparisons": comparisons,
        "qwen_failures": sorted(qwen_failures),
        "v2_overlap_v1": len(v2_ids & v1_ids),
        "v2_qwen_retained": len(v2_ids & qwen_failures),
        "v2_qwen_filtered": len(qwen_failures - v2_ids),
        "v2_historical_numeric_detectability": sum(
            isinstance(row.get("detectability_score"), (int, float)) for row in v2_tasks
        ),
        "v2_v11_numeric_detectability": sum(
            isinstance((row.get("metadata") or {}).get("v11_detectability_score"), (int, float))
            for row in v2_tasks
        ),
        "v2_quality": v2_quality,
        "v2_bundle": v2_bundle,
        "main_detectability": main_detectability,
        "v2_detectability": v2_detectability,
        "v1_detectability": v1_detectability,
        "review_manifest": review_manifest,
        "second_domain_registry": second_domain_registry,
        "main_bundle_manifest": main_bundle_manifest,
        "session2_private_occurrences": session2_private_occurrences,
        "repo_license_present": any(
            path.is_file() for pattern in ("LICENSE", "LICENSE.*", "COPYING", "COPYING.*")
            for path in ROOT.glob(pattern)
        ),
        "paper_bibliography_present": any((ROOT / "paper").glob("*.bib")),
        "inventory": inventory(out),
        "dependencies": dependency_versions(),
        "paths": {
            "main_tasks": main_tasks_path,
            "taskitems": taskitems_path,
            "v1_tasks": v1_tasks_path,
            "v2_tasks": v2_tasks_path,
            "v2_candidate_audit": v2_candidate_audit_path,
        },
    }


def evidence_row(
    artifact_id: str,
    path: str,
    family: str,
    model: str,
    domain: str,
    run_tag: str,
    item_count: int | str,
    evidence_class: str,
    raw_derived: str,
    upstream: str,
    validation: str,
    limitations: str,
    canonical: str,
    *,
    diagnostic: bool = False,
) -> dict[str, Any]:
    assert evidence_class in EVIDENCE_CLASSES
    exists = (ROOT / path).is_file()
    return {
        "artifact_id": artifact_id,
        "artifact_path": path,
        "experiment_family": family,
        "model_provider": model,
        "dataset_domain": domain,
        "run_tag": run_tag,
        "item_count": item_count,
        "evidence_class": evidence_class,
        "raw_or_derived_status": raw_derived,
        "upstream_source": upstream,
        "sha256": sha256(path) if exists else "NOT_APPLICABLE",
        "timestamp": timestamp(path) if exists else "NOT_CREATED",
        "validation_status": validation,
        "paper_claim_eligibility": False,
        "paper_evidence": False,
        "diagnostic_only": diagnostic,
        "human_reviewed": False,
        "known_limitations": limitations,
        "canonical_status": canonical,
    }


def build_evidence_ledger(state: dict[str, Any]) -> list[dict[str, Any]]:
    paths = state["paths"]
    rows = [
        evidence_row(
            "main91_task_manifest",
            paths["main_tasks"],
            "intervention_pilot",
            "all",
            "ADE20K/household",
            "main_real_200_reviewed_v2",
            len(state["main_tasks"]),
            "MACHINE_ASSISTED_PRELIMINARY",
            "input_manifest",
            "data/results/main_real_200/visual_review_completed.csv",
            "hash and 91 unique item IDs verified; embedded historical review label superseded",
            "Completed by assistant_visual_review_v1; independent rater sheet is blank.",
            "canonical_with_v11_override",
        ),
        evidence_row(
            "main91_taskitems",
            paths["taskitems"],
            "intervention_pilot",
            "all",
            "ADE20K/household",
            "main_real_200_taskitems_v2",
            len(state["main_tasks"]),
            "MACHINE_ASSISTED_PRELIMINARY",
            "input_manifest",
            paths["main_tasks"],
            "hash and row count verified; embedded historical review label superseded",
            "Validity decisions have not completed independent human review.",
            "canonical_with_v11_override",
        ),
        evidence_row(
            "v1_specificity_tasks",
            paths["v1_tasks"],
            "spurious_v1",
            "all",
            "ADE20K/household",
            "spurious_flip_control_v1",
            len(state["v1_tasks"]),
            "MACHINE_ASSISTED_PRELIMINARY",
            "input_manifest",
            "data/edits/spurious_flip_control",
            "94 unique item IDs and 188 paired images verified; embedded review label superseded",
            "Objective checks do not replace blinded human validity review.",
            "canonical_with_v11_override",
        ),
    ]
    for provider, spec in PROVIDERS.items():
        rows.append(
            evidence_row(
                f"main91_presence_{provider}",
                spec["presence"],
                "intervention_pilot",
                provider,
                "ADE20K/household",
                str(state["raw_rows"][provider]["presence"][0]["run_id"]),
                91,
                "REAL_OBSERVED_EVIDENCE",
                "raw_model_output",
                paths["taskitems"],
                "182 rows; 91 complete original/edited pairs; strict parse complete",
                "Exact model repository revision was not recorded; item validity remains pending human review.",
                "canonical_raw",
            )
        )
        rows.append(
            evidence_row(
                f"v1_specificity_{provider}",
                spec["spurious"],
                "spurious_v1",
                provider,
                "ADE20K/household",
                str(state["raw_rows"][provider]["spurious"][0]["run_id"]),
                94,
                "REAL_OBSERVED_EVIDENCE",
                "raw_model_output",
                paths["v1_tasks"],
                "188 rows; 94 complete original/edited pairs; strict parse complete",
                "Historical model revision is unpinned and control validity review is incomplete.",
                "canonical_raw",
            )
        )
        rows.append(
            evidence_row(
                f"pilot_report_{provider}",
                spec["pilot_report"],
                "intervention_pilot",
                provider,
                "ADE20K/household",
                "v11_recomputed_report",
                91,
                "DERIVED_FROM_REAL_EVIDENCE",
                "derived_statistics",
                spec["presence"],
                "raw-pair metrics and confidence-sequence values cross-checked",
                "Numeric threshold crossing is not full scientific certification.",
                "canonical_derived",
            )
        )
    rows.extend(
        [
            evidence_row(
                "qwen_v1_failure_forensics",
                "data/results/main_real_200/v8_1_qwen_spurious_forensics/"
                "qwen_spurious_failed_12.jsonl",
                "spurious_v1_forensics",
                "qwen2_5_vl_7b",
                "ADE20K/household",
                "v8_1_recompute",
                len(state["qwen_failures"]),
                "DIAGNOSTIC_ONLY",
                "derived_diagnostic",
                PROVIDERS["qwen2_5_vl_7b"]["spurious"],
                "12 failures reproduce from raw pair differences",
                "Machine visual labels are not human labels; mechanism attribution is unsupported.",
                "canonical_diagnostic",
                diagnostic=True,
            ),
            evidence_row(
                "spurious_v2_retrospective_tasks",
                paths["v2_tasks"],
                "spurious_v2",
                "all",
                "ADE20K/household",
                "seed_9009_retrospective",
                len(state["v2_tasks"]),
                "DIAGNOSTIC_ONLY",
                "input_manifest",
                paths["v1_tasks"],
                "30 unique items; geometry constraints validated; no provider outputs present",
                "All items reuse V1; constructed after V1 outcomes; 26 detectability values are null.",
                "retrospective_diagnostic_only",
                diagnostic=True,
            ),
            evidence_row(
                "spurious_v2_kaggle_bundle",
                "dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip",
                "spurious_v2",
                "all",
                "ADE20K/household",
                "private_kaggle_input",
                30,
                "PLANNED_NOT_EXECUTED",
                "execution_package",
                paths["v2_tasks"],
                "package present; provider result artifacts absent",
                "Source metadata disallows redistribution; private execution only pending license verification.",
                "canonical_execution_package",
                diagnostic=True,
            ),
            evidence_row(
                "human_review_second_rater",
                "data/results/main_real_200/review_iaa/second_rater_review_sheet.csv",
                "human_validation",
                "none",
                "ADE20K/household",
                "second_rater_pending",
                91,
                "HUMAN_REVIEW_PENDING",
                "blank_review_template",
                paths["main_tasks"],
                "file exists but decision fields are blank",
                "No independent human judgments are present.",
                "canonical_pending",
            ),
            evidence_row(
                "v11_blinded_review_packet",
                "reports/v11_full_ceiling_audit/human_review_packet/packet_manifest.json",
                "human_validation",
                "none",
                "ADE20K/household",
                "seed_110713_private_blinded_packet",
                int((state["review_manifest"] or {}).get("n_unique_review_rows", 227)),
                "HUMAN_REVIEW_PENDING",
                "blank_review_packet",
                "pilot91; V1 control94; strict retrospective control30; anonymized diagnostic12",
                "four-track packet is deterministic and blinded; all human fields remain blank",
                "Private coordinated review only; agreement has not been computed.",
                "canonical_pending",
            ),
            evidence_row(
                "main91_detectability_v11",
                "reports/v11_full_ceiling_audit/analysis/main91_detectability/detectability_summary.json",
                "construct_validity_diagnostic",
                "none",
                "ADE20K/household",
                "grouped_item_cv_v11",
                91,
                "DIAGNOSTIC_ONLY",
                "derived_diagnostic",
                paths["main_tasks"],
                "grouped-by-item CV and symmetric AUC",
                "Classifier separability does not validate item semantics or prove artifact absence.",
                "canonical_diagnostic",
                diagnostic=True,
            ),
            evidence_row(
                "v2_retrospective_detectability_v11",
                "reports/v11_full_ceiling_audit/analysis/v2_retrospective_detectability/detectability_summary.json",
                "construct_validity_diagnostic",
                "none",
                "ADE20K/household",
                "grouped_item_cv_v11",
                30,
                "DIAGNOSTIC_ONLY",
                "derived_diagnostic",
                paths["v2_tasks"],
                "30/30 paired scores plus grouped-by-item symmetric AUC",
                "Post-selection diagnostic; cannot repair retrospective item selection or establish semantics.",
                "canonical_diagnostic",
                diagnostic=True,
            ),
            evidence_row(
                "main500_protocol",
                "configs/certvic_v11_protocol.yaml",
                "main500",
                "all",
                "ADE20K/household",
                "seed_11011_planned",
                500,
                "PLANNED_NOT_EXECUTED",
                "prospective_protocol",
                "none",
                "execution_allowed_now=false",
                "Specificity, human review, objective quality, importer, and revision prerequisites remain open.",
                "canonical_protocol",
            ),
            evidence_row(
                "synthetic_smoke_matrix",
                "data/results/v1_1_smoke_matrix/mock_spurious_flip/predictions.jsonl",
                "software_validation",
                "mock_spurious_flip",
                "synthetic",
                "v1_1_smoke",
                len(
                    read_jsonl(
                        "data/results/v1_1_smoke_matrix/mock_spurious_flip/predictions.jsonl"
                    )
                ),
                "SYNTHETIC_TEST_FIXTURE",
                "synthetic_fixture",
                "tests",
                "retained for regression testing only",
                "Never usable as empirical evidence.",
                "canonical_test_fixture",
                diagnostic=True,
            ),
            evidence_row(
                "historical_v9_paper",
                "paper/main_v9.tex",
                "paper",
                "all",
                "ADE20K/household",
                "v9",
                "not applicable",
                "DEPRECATED_OR_STALE",
                "historical_document",
                "historical V7-V9 outputs",
                "retained for provenance; superseded by V11",
                "Contains stale framing and cannot establish present project state.",
                "superseded",
            ),
            evidence_row(
                "v11_paper_draft",
                "paper/main_v11.pdf",
                "paper",
                "all",
                "ADE20K/household",
                "v11_evidence_safe_draft",
                "not applicable",
                "DERIVED_FROM_REAL_EVIDENCE",
                "paper_draft",
                "raw predictions and V11 audit",
                "compiled and visually inspected; claim eligibility remains false",
                "Draft is pilot-scale and not submission-ready.",
                "current_draft",
            ),
        ]
    )
    assert all(row["evidence_class"] in EVIDENCE_CLASSES for row in rows)
    assert all(not row["paper_evidence"] for row in rows)
    assert all(not row["human_reviewed"] for row in rows)
    return rows


def build_gate_ledger(state: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = state["pilot_metrics"]
    qwen = len(state["failures"]["qwen2_5_vl_7b"])
    intern = len(state["failures"]["internvl_8b"])
    llava = len(state["failures"]["llava_onevision_7b"])
    all_raw = [rows for provider in state["raw_rows"].values() for rows in provider.values()]
    raw_pairs_complete = all(
        len(rows) == 182 and all(row.get("parse_ok") is True for row in rows)
        for rows in all_raw
    )
    v2_rows = state["v2_tasks"]
    v2_geometry_pass = (
        len(v2_rows) == 30
        and all(float(row.get("patch_object_bbox_distance_px") or -1) >= 75.0 for row in v2_rows)
        and all(row.get("patch_bbox_intersects_object_bbox") is False for row in v2_rows)
        and all(int(row.get("patch_target_mask_overlap_pixels") or 0) == 0 for row in v2_rows)
    )
    v2_scores = [
        float((row.get("metadata") or {})["v11_detectability_score"])
        for row in v2_rows
        if isinstance((row.get("metadata") or {}).get("v11_detectability_score"), (int, float))
    ]
    v2_auc = (
        float(state["v2_detectability"]["classifier"]["auc"])
        if state["v2_detectability"]
        else None
    )
    expected_v2_outputs = [
        ROOT / "data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest"
        / f"pred_{provider}_spurious_v2_merged.jsonl"
        for provider in PROVIDERS
    ]
    n_v2_outputs = sum(path.is_file() for path in expected_v2_outputs)
    notebook_validation_path = state["out"] / "notebook_static_validation.json"
    notebook_validation = (
        read_json(notebook_validation_path) if notebook_validation_path.is_file() else {}
    )
    return [
        {
            "gate_name": "raw_pair_parse_completeness",
            "exact_formula": "for each of 3 providers and 2 arms: rows=182, unique item-variant keys=182, parse_ok=182",
            "frozen_threshold": "6/6 canonical files complete with zero parse failures",
            "source_specification": "docs/methodology/CERTVIC_PROSPECTIVE_ANALYSIS_SPEC_V11.md",
            "required_artifacts": "six canonical main91/V1 raw prediction files",
            "current_result": "6/6 files have 182 rows and strict parse_ok throughout",
            "status": "PASS" if raw_pairs_complete else "FAIL",
            "uncertainty_treatment": "none; structural integrity gate",
            "prospective_or_retrospective": "retrospective integrity audit of observed files",
            "downstream_actions_enabled": "paired descriptive and inferential recomputation",
            "reason_for_blockage": "none" if raw_pairs_complete else "row, key, or parse completeness failed",
        },
        {
            "gate_name": "evidence_class_eligibility",
            "exact_formula": "human_reviewed=true and evidence class eligible under V11 policy",
            "frozen_threshold": "real blinded human review plus all policy gates",
            "source_specification": "configs/certvic_v11_protocol.yaml#evidence_policy",
            "required_artifacts": "V11 evidence ledger; completed reviewer/adjudication outputs",
            "current_result": "human_reviewed=0; all paper_claim_eligibility=false",
            "status": "BLOCKED",
            "uncertainty_treatment": "blank judgments are never imputed",
            "prospective_or_retrospective": "current-state classification",
            "downstream_actions_enabled": "internal pilot and diagnostic reporting only",
            "reason_for_blockage": "historical machine-assisted labels are overridden; no real human review exists",
        },
        {
            "gate_name": "historical_provider_revision_provenance",
            "exact_formula": "provider identity exact and immutable model/processor revision recorded",
            "frozen_threshold": "exact repository ID plus 40-character commit per run",
            "source_specification": "configs/certvic_v11_protocol.yaml#models",
            "required_artifacts": "raw prediction rows and runtime manifests",
            "current_result": "provider IDs validate; historical model_version is unpinned/unloaded",
            "status": "BLOCKED",
            "uncertainty_treatment": "not recoverable statistically",
            "prospective_or_retrospective": "historical audit; prospective requirement for new runs",
            "downstream_actions_enabled": "qualified historical pilot reporting only",
            "reason_for_blockage": "exact historical revisions were not recorded",
        },
        {
            "gate_name": "pilot_n_overall",
            "exact_formula": "n_overall >= min_n_overall",
            "frozen_threshold": "150",
            "source_specification": "configs/certification_policy.yaml",
            "required_artifacts": state["paths"]["taskitems"],
            "current_result": "91",
            "status": "FAIL",
            "uncertainty_treatment": "not applicable",
            "prospective_or_retrospective": "prospective policy applied to pilot",
            "downstream_actions_enabled": "descriptive pilot analysis only",
            "reason_for_blockage": "91 < 150",
        },
        {
            "gate_name": "pilot_n_by_family",
            "exact_formula": "min_f n_f >= min_n_by_family",
            "frozen_threshold": "40 per family",
            "source_specification": "configs/certification_policy.yaml",
            "required_artifacts": state["paths"]["taskitems"],
            "current_result": "support_stability=54; affordance_reachability=31; occlusion_safety=6",
            "status": "FAIL",
            "uncertainty_treatment": "not applicable",
            "prospective_or_retrospective": "prospective policy applied to pilot",
            "downstream_actions_enabled": "family-stratified descriptive reporting",
            "reason_for_blockage": "two families are below 40",
        },
        {
            "gate_name": "numeric_cs_gap",
            "exact_formula": "latest anytime-valid CS lower bound > 0.05",
            "frozen_threshold": "0.05",
            "source_specification": "configs/certification_policy.yaml",
            "required_artifacts": "three canonical main91 presence prediction files",
            "current_result": "; ".join(
                f"{provider}={metrics[provider]['cs_lb']:.6f}" for provider in PROVIDERS
            ),
            "status": "PASS_NUMERIC_ONLY",
            "uncertainty_treatment": "Hoeffding normal-mixture time-uniform confidence sequence",
            "prospective_or_retrospective": "pre-existing estimator; V11 audit retrospective",
            "downstream_actions_enabled": "report numerical crossings with qualification",
            "reason_for_blockage": "does not clear sample-size, review, or specificity gates",
        },
        {
            "gate_name": "v1_qwen_specificity",
            "exact_formula": "observed flips / 94 <= 0.10",
            "frozen_threshold": "0.10",
            "source_specification": "configs/certvic_v11_protocol.yaml#historical_v1",
            "required_artifacts": PROVIDERS["qwen2_5_vl_7b"]["spurious"],
            "current_result": f"{qwen}/94={qwen / 94:.6f}",
            "status": "FAIL",
            "uncertainty_treatment": "frozen observed-rate rule; intervals reported separately",
            "prospective_or_retrospective": "historical frozen V1",
            "downstream_actions_enabled": "model-dependent specificity hypothesis",
            "reason_for_blockage": "observed flip rate exceeds 0.10",
        },
        {
            "gate_name": "v1_internvl_specificity",
            "exact_formula": "observed flips / 94 <= 0.10",
            "frozen_threshold": "0.10",
            "source_specification": "configs/certvic_v11_protocol.yaml#historical_v1",
            "required_artifacts": PROVIDERS["internvl_8b"]["spurious"],
            "current_result": f"{intern}/94={intern / 94:.6f}",
            "status": "PASS_OBSERVED_RULE_ONLY",
            "uncertainty_treatment": "frozen observed-rate rule; intervals reported separately",
            "prospective_or_retrospective": "historical frozen V1",
            "downstream_actions_enabled": "qualified model-specific pilot statement",
            "reason_for_blockage": "independent human validity review remains incomplete",
        },
        {
            "gate_name": "v1_llava_specificity",
            "exact_formula": "observed flips / 94 <= 0.10",
            "frozen_threshold": "0.10",
            "source_specification": "configs/certvic_v11_protocol.yaml#historical_v1",
            "required_artifacts": PROVIDERS["llava_onevision_7b"]["spurious"],
            "current_result": f"{llava}/94={llava / 94:.6f}",
            "status": "PASS_OBSERVED_RULE_ONLY",
            "uncertainty_treatment": "frozen observed-rate rule; intervals reported separately",
            "prospective_or_retrospective": "historical frozen V1",
            "downstream_actions_enabled": "qualified model-specific pilot statement",
            "reason_for_blockage": "independent human validity review remains incomplete",
        },
        {
            "gate_name": "current_v2_independence",
            "exact_formula": "count(V2 item IDs intersect V1 item IDs) = 0",
            "frozen_threshold": "0 reused items",
            "source_specification": "configs/certvic_v11_protocol.yaml#spurious_v2",
            "required_artifacts": state["paths"]["v1_tasks"] + "; " + state["paths"]["v2_tasks"],
            "current_result": f"{state['v2_overlap_v1']}/30 reused",
            "status": "FAIL_DIAGNOSTIC_ONLY",
            "uncertainty_treatment": "not repaired by a statistical interval",
            "prospective_or_retrospective": "retrospective post-V1 selection",
            "downstream_actions_enabled": "retrospective sensitivity analysis only",
            "reason_for_blockage": "all current V2 items were seen in V1",
        },
        {
            "gate_name": "current_v2_objective_geometry",
            "exact_formula": "n=30; distance>=75 px; bbox overlap=false; target-mask overlap=0 for every item",
            "frozen_threshold": "all four conditions on 30/30 items",
            "source_specification": "configs/certvic_v11_protocol.yaml#spurious_v2.current_set",
            "required_artifacts": state["paths"]["v2_tasks"],
            "current_result": "30/30 geometry-complete with frozen thresholds" if v2_geometry_pass else "geometry preflight failed",
            "status": "PASS_DIAGNOSTIC_ONLY" if v2_geometry_pass else "FAIL",
            "uncertainty_treatment": "deterministic geometry checks; semantics still require humans",
            "prospective_or_retrospective": "retrospective post-outcome selected set",
            "downstream_actions_enabled": "private retrospective diagnostic execution only",
            "reason_for_blockage": "geometry cannot cure V1 reuse or post-outcome selection",
        },
        {
            "gate_name": "current_v2_detectability_diagnostic",
            "exact_formula": "30/30 paired scores present; grouped-item symmetric AUC<=0.80",
            "frozen_threshold": "set AUC <= 0.80; historical per-item cap 0.12 was incompletely observed",
            "source_specification": "configs/certvic_v11_protocol.yaml#spurious_v2",
            "required_artifacts": "V2 task manifest; V11 grouped detectability summary",
            "current_result": (
                f"scores={len(v2_scores)}/30; max={max(v2_scores):.8f}; AUC={v2_auc:.4f}"
                if v2_scores and v2_auc is not None
                else "incomplete detectability diagnostics"
            ),
            "status": "PASS_SET_LEVEL_DIAGNOSTIC_ONLY" if len(v2_scores) == 30 and v2_auc is not None and v2_auc <= 0.80 else "BLOCKED",
            "uncertainty_treatment": "grouped folds by item; symmetric AUC; no retroactive exclusions",
            "prospective_or_retrospective": "post-selection, pre-provider retrospective diagnostic",
            "downstream_actions_enabled": "diagnostic reporting only",
            "reason_for_blockage": "26/30 original selector scores were missing and the current maximum slightly exceeds 0.12",
        },
        {
            "gate_name": "prospective_v2_primary",
            "exact_formula": "one-sided CP upper bound(alpha=0.05) <= 0.10",
            "frozen_threshold": "0.10",
            "source_specification": "configs/certvic_v11_protocol.yaml#spurious_v2.primary_decision",
            "required_artifacts": "independent unseen controls; Qwen outputs; completed pre-unblinding review",
            "current_result": "no independent set and no V2 provider outputs",
            "status": "BLOCKED",
            "uncertainty_treatment": "one-sided Clopper-Pearson, missing/unparseable pairs count as flips",
            "prospective_or_retrospective": "prospective",
            "downstream_actions_enabled": "none",
            "reason_for_blockage": "missing independent items, outputs, and human review",
        },
        {
            "gate_name": "prospective_v2_three_model_joint",
            "exact_formula": "for all 3 models: one-sided CP upper bound at alpha=0.05/3 <= 0.10",
            "frozen_threshold": "each of three upper bounds <=0.10",
            "source_specification": "configs/certvic_v11_protocol.yaml#spurious_v2.three_model_joint_claim",
            "required_artifacts": "independent set; three complete imported outputs; pre-unblinding review",
            "current_result": f"{n_v2_outputs}/3 provider outputs present",
            "status": "BLOCKED",
            "uncertainty_treatment": "Bonferroni one-sided Clopper-Pearson; missing pairs count as flips",
            "prospective_or_retrospective": "prospective",
            "downstream_actions_enabled": "none",
            "reason_for_blockage": "independent set, review, revisions, and all provider outputs are absent",
        },
        {
            "gate_name": "v2_output_and_import_completeness",
            "exact_formula": "3 archives pass schema-v3 hashes/revisions and each yields exactly 60 unique rows",
            "frozen_threshold": "3/3 valid archives; 180/180 rows; transactional conflict-free import",
            "source_specification": "scripts/import_v9_spurious_v2_outputs.py",
            "required_artifacts": "three provider prediction archives and runtime manifests",
            "current_result": f"{n_v2_outputs}/3 canonical provider outputs present; importer implemented but not run on real V2 outputs",
            "status": "BLOCKED",
            "uncertainty_treatment": "missing/unparseable rows fail closed",
            "prospective_or_retrospective": "prospective operational gate",
            "downstream_actions_enabled": "synthetic importer regression tests only",
            "reason_for_blockage": "real V2 outputs do not exist",
        },
        {
            "gate_name": "v2_model_revision_lock",
            "exact_formula": "every notebook MODEL_REVISION matches a 40-character immutable commit and runtime manifest",
            "frozen_threshold": "3/3 exact revisions",
            "source_specification": "configs/certvic_v11_protocol.yaml#models",
            "required_artifacts": "three V2 notebooks; runtime manifests",
            "current_result": "0/3 revisions filled; notebooks retain MODEL_REVISION=None",
            "status": "BLOCKED",
            "uncertainty_treatment": "none; exact identity requirement",
            "prospective_or_retrospective": "prospective before GPU execution",
            "downstream_actions_enabled": "static validation only",
            "reason_for_blockage": "immutable model and processor revisions are unresolved",
        },
        {
            "gate_name": "v2_notebook_static_contract",
            "exact_formula": "all six VLM notebooks pass provider, T4x2, fallback, resume, merge, hash, schema, and no-output checks",
            "frozen_threshold": "6/6 static pass",
            "source_specification": "scripts/validate_t4x2_notebooks.py",
            "required_artifacts": "six provider notebooks; static validation JSON",
            "current_result": "6/6 static pass" if notebook_validation.get("passed") else "final static validation not yet recorded",
            "status": "PASS_STATIC_ONLY" if notebook_validation.get("passed") else "PENDING_FINAL_VALIDATION",
            "uncertainty_treatment": "static inspection only; no notebook execution claim",
            "prospective_or_retrospective": "pre-execution operational gate",
            "downstream_actions_enabled": "private execution after revisions/review are supplied",
            "reason_for_blockage": "static pass does not supply revisions, outputs, or human approval",
        },
        {
            "gate_name": "v2_private_package_integrity",
            "exact_formula": "task_rows=30; image_entries=60; every member size/hash matches manifest; deterministic ZIP",
            "frozen_threshold": "all package locks pass",
            "source_specification": "data/edits/spurious_v2_control/bundle_manifest.json",
            "required_artifacts": "V2 task, manifest, 60 images, private ZIP",
            "current_result": f"task_rows={state['v2_bundle'].get('task_rows')}; image_entries={len(state['v2_bundle'].get('image_entries', []))}",
            "status": "PASS_PRIVATE_PACKAGE" if state["v2_bundle"].get("task_rows") == 30 and len(state["v2_bundle"].get("image_entries", [])) == 60 else "FAIL",
            "uncertainty_treatment": "byte-level hashes and fixed ZIP metadata",
            "prospective_or_retrospective": "current private execution package",
            "downstream_actions_enabled": "private diagnostic upload only",
            "reason_for_blockage": "image redistribution license is unresolved; package is not a public release",
        },
        {
            "gate_name": "human_validity",
            "exact_formula": "two independent blinded raters complete required fields before output unblinding",
            "frozen_threshold": "2 raters plus adjudication",
            "source_specification": "configs/certvic_v11_protocol.yaml",
            "required_artifacts": "reviewer sheets; codebook; agreement report; adjudication log",
            "current_result": "assistant_visual_review_v1 only; independent sheet blank",
            "status": "BLOCKED",
            "uncertainty_treatment": "report agreement and Cohen kappa; never impute blank judgments",
            "prospective_or_retrospective": "must precede new output unblinding",
            "downstream_actions_enabled": "none",
            "reason_for_blockage": "real independent human judgments are absent",
        },
        {
            "gate_name": "main500_go",
            "exact_formula": "all formal go_requirements in V11 protocol are true",
            "frozen_threshold": "all prerequisites",
            "source_specification": "configs/certvic_v11_protocol.yaml#main500",
            "required_artifacts": "specificity sign-off; review; importer; quality gates; pinned revisions",
            "current_result": "execution_allowed_now=false",
            "status": "BLOCKED",
            "uncertainty_treatment": "not applicable before execution",
            "prospective_or_retrospective": "prospective",
            "downstream_actions_enabled": "design and acquisition planning only",
            "reason_for_blockage": "multiple mandatory prerequisites remain false",
        },
        {
            "gate_name": "paper_bibliography_and_novelty_sources",
            "exact_formula": "bibliography present and every novelty/priority statement anchored to verified primary sources",
            "frozen_threshold": "complete source-backed related work and bibliography",
            "source_specification": "paper/main_v11.tex; PAPER_AND_NOVELTY_AUDIT.md",
            "required_artifacts": "paper bibliography and verified literature matrix",
            "current_result": "bibliography present" if state["paper_bibliography_present"] else "no paper bibliography present",
            "status": "PASS" if state["paper_bibliography_present"] else "BLOCKED",
            "uncertainty_treatment": "not applicable",
            "prospective_or_retrospective": "submission-readiness gate",
            "downstream_actions_enabled": "internal draft only" if not state["paper_bibliography_present"] else "source-backed paper revision",
            "reason_for_blockage": "bibliography and primary-source novelty audit are absent" if not state["paper_bibliography_present"] else "none",
        },
        {
            "gate_name": "public_release_license",
            "exact_formula": "project license present and every bundled data/image asset has redistribution permission",
            "frozen_threshold": "license plus asset-level redistribution clearance",
            "source_specification": "REPRODUCIBILITY_AND_RELEASE_AUDIT.md",
            "required_artifacts": "repository license; source-dataset license decisions; release manifest",
            "current_result": "repository license present" if state["repo_license_present"] else "no repository license; ADE-derived images private",
            "status": "BLOCKED",
            "uncertainty_treatment": "legal/data-governance decision; no inference",
            "prospective_or_retrospective": "release gate",
            "downstream_actions_enabled": "private coordination and pointer-only planning",
            "reason_for_blockage": "project license and authoritative image redistribution clearance are missing",
        },
    ]


def build_blockers(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "blocker_id": "B01",
            "category": "human validation",
            "severity": "critical",
            "probability_affecting_conclusions": "high",
            "exact_evidence": "assistant_visual_review_v1 completed selection; independent rater sheet blank",
            "repairable_locally": "no",
            "owner_type": "two independent human raters plus adjudicator",
            "prerequisite": "outcome-blind packet and codebook",
            "recommended_action": "complete pilot91 and V1-94 review before any new output unblinding",
            "blocks_spurious_v2": "yes",
            "blocks_main500": "yes",
            "blocks_submission": "yes",
        },
        {
            "blocker_id": "B02",
            "category": "scientific validity",
            "severity": "critical",
            "probability_affecting_conclusions": "high",
            "exact_evidence": f"current V2 reuses {state['v2_overlap_v1']}/30 V1 item IDs and retained "
            f"{state['v2_qwen_retained']}/12 known Qwen failures",
            "repairable_locally": "no; local unused pool is absent",
            "owner_type": "research/data acquisition",
            "prerequisite": "new control source pool unseen in V1",
            "recommended_action": "construct and preregister a powered independent specificity set",
            "blocks_spurious_v2": "yes for confirmatory use",
            "blocks_main500": "yes",
            "blocks_submission": "yes for broad specificity claims",
        },
        {
            "blocker_id": "B03",
            "category": "missing real evidence",
            "severity": "critical",
            "probability_affecting_conclusions": "high",
            "exact_evidence": "no current V2 provider prediction file exists",
            "repairable_locally": "no",
            "owner_type": "Kaggle/GPU executor",
            "prerequisite": "pinned revisions and approved blinded control set",
            "recommended_action": "run only after protocol and review prerequisites; treat current set as diagnostic",
            "blocks_spurious_v2": "yes",
            "blocks_main500": "yes",
            "blocks_submission": "yes for new V2 claims",
        },
        {
            "blocker_id": "B04",
            "category": "reproducibility",
            "severity": "high",
            "probability_affecting_conclusions": "medium",
            "exact_evidence": "historical prediction rows record model_version=unloaded",
            "repairable_locally": "no for historical runs",
            "owner_type": "future run operator",
            "prerequisite": "resolve immutable model and processor commits",
            "recommended_action": "pin repository revisions, processor version, precision, and environment before reruns",
            "blocks_spurious_v2": "yes for reproducible new evidence",
            "blocks_main500": "yes",
            "blocks_submission": "yes for strong reproducibility claim",
        },
        {
            "blocker_id": "B05",
            "category": "statistics",
            "severity": "high",
            "probability_affecting_conclusions": "high",
            "exact_evidence": "pilot n=91 < 150; family counts 54, 31, and 6 < required 40 for two families",
            "repairable_locally": "no without new eligible items",
            "owner_type": "research/data acquisition",
            "prerequisite": "validity-approved powered sample",
            "recommended_action": "use pilot descriptively; power the confirmatory study prospectively",
            "blocks_spurious_v2": "no",
            "blocks_main500": "yes",
            "blocks_submission": "yes for certification claim",
        },
        {
            "blocker_id": "B06",
            "category": "release defect",
            "severity": "high",
            "probability_affecting_conclusions": "low",
            "exact_evidence": "V2 source metadata has redistribution_allowed=false while bundle contains images",
            "repairable_locally": "no; requires license determination",
            "owner_type": "legal/data steward",
            "prerequisite": "authoritative ADE20K redistribution review",
            "recommended_action": "keep image bundle private; release manifests and pointers only until cleared",
            "blocks_spurious_v2": "no for private run",
            "blocks_main500": "no for private run",
            "blocks_submission": "yes for public image release",
        },
        {
            "blocker_id": "B07",
            "category": "paper defect",
            "severity": "high",
            "probability_affecting_conclusions": "medium",
            "exact_evidence": "related-work matrix lacks fully verified bibliographic anchors and no priority audit is complete",
            "repairable_locally": "partly",
            "owner_type": "researcher",
            "prerequisite": "source-backed literature review",
            "recommended_action": "verify primary sources and remove unsupported novelty or priority language",
            "blocks_spurious_v2": "no",
            "blocks_main500": "no",
            "blocks_submission": "yes",
        },
        {
            "blocker_id": "B08",
            "category": "data defect",
            "severity": "medium",
            "probability_affecting_conclusions": "medium",
            "exact_evidence": f"the retrospective selector saw only {state['v2_historical_numeric_detectability']}/30 stored scores; V11 now records {state['v2_v11_numeric_detectability']}/30 post-selection, pre-provider diagnostics",
            "repairable_locally": "measurement repaired; retrospective selection bias is not repairable",
            "owner_type": "software/research",
            "prerequisite": "locked objective metric and untouched outputs",
            "recommended_action": "preserve the new complete diagnostic but do not retroactively exclude; freeze the metric before independent-set selection",
            "blocks_spurious_v2": "yes for confirmatory use of the current selected set",
            "blocks_main500": "yes",
            "blocks_submission": "no for an explicitly retrospective appendix",
        },
        {
            "blocker_id": "B09",
            "category": "optional enhancement",
            "severity": "medium",
            "probability_affecting_conclusions": "medium",
            "exact_evidence": "all current real intervention and specificity data use ADE20K household/object questions",
            "repairable_locally": "no second-domain assets are present",
            "owner_type": "research/data acquisition",
            "prerequisite": "license-verified second-domain dataset and preregistered protocol mapping",
            "recommended_action": "add a small independent domain only after specificity is resolved",
            "blocks_spurious_v2": "no",
            "blocks_main500": "no",
            "blocks_submission": "limits generalization ceiling",
        },
        {
            "blocker_id": "B10",
            "category": "privacy",
            "severity": "high",
            "probability_affecting_conclusions": "low",
            "exact_evidence": "dist/certvic_main200_session2_data.zip contains "
            f"{state['session2_private_occurrences']} private-root occurrences",
            "repairable_locally": "yes by building a sanitized replacement; do not mutate the historical archive",
            "owner_type": "release engineer",
            "prerequisite": "explicit release file list and privacy audit on the exact candidate",
            "recommended_action": "mark session2 archive non-release and build a clean archive from approved relative paths",
            "blocks_spurious_v2": "no",
            "blocks_main500": "no",
            "blocks_submission": "yes for release readiness",
        },
        {
            "blocker_id": "B11",
            "category": "data defect",
            "severity": "medium",
            "probability_affecting_conclusions": "low for current results; high for new local mining",
            "exact_evidence": "initial census recorded ade20kdataset/ade20k.zip; the final repository path is absent",
            "repairable_locally": "only after owner confirms the intended sibling source copy",
            "owner_type": "data owner",
            "prerequisite": "confirm source archive identity and license before copying or linking",
            "recommended_action": "do not infer restoration authority; reattach the approved source before independent-set mining",
            "blocks_spurious_v2": "yes for mining a new local independent set",
            "blocks_main500": "yes for new source-based generation",
            "blocks_submission": "no for reporting existing raw outputs",
        },
    ]


def write_ledgers(out: Path, evidence: list[dict[str, Any]], gates: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> None:
    write_csv(out / "CERTVIC_EVIDENCE_LEDGER.csv", EVIDENCE_FIELDS, evidence)
    write_text(out / "CERTVIC_EVIDENCE_LEDGER.json", json.dumps(evidence, indent=2, sort_keys=True))
    gate_fields = [
        "gate_name",
        "exact_formula",
        "frozen_threshold",
        "source_specification",
        "required_artifacts",
        "current_result",
        "status",
        "uncertainty_treatment",
        "prospective_or_retrospective",
        "downstream_actions_enabled",
        "reason_for_blockage",
    ]
    blocker_fields = [
        "blocker_id",
        "category",
        "severity",
        "probability_affecting_conclusions",
        "exact_evidence",
        "repairable_locally",
        "owner_type",
        "prerequisite",
        "recommended_action",
        "blocks_spurious_v2",
        "blocks_main500",
        "blocks_submission",
    ]
    write_csv(out / "CERTVIC_GATE_LEDGER.csv", gate_fields, gates)
    write_csv(out / "CERTVIC_BLOCKER_REGISTER.csv", blocker_fields, blockers)


def report_header(title: str, purpose: str) -> str:
    return f"# {title}\n\n**Status:** evidence-bounded V11 audit; `paper_evidence=false`\n\n{purpose}\n"


def build_reports(
    state: dict[str, Any], evidence: list[dict[str, Any]], gates: list[dict[str, Any]], blockers: list[dict[str, Any]]
) -> dict[str, str]:
    inv = state["inventory"]
    metrics = state["pilot_metrics"]
    failures = state["failures"]
    dependencies = state["dependencies"]
    pilot_rows = [
        [
            PROVIDERS[p]["display"],
            metrics[p]["n"],
            f"{metrics[p]['a']:.4f}",
            f"{metrics[p]['p']:.4f}",
            f"{metrics[p]['gap']:.4f}",
            f"{metrics[p]['cs_lb']:.6f}",
            "false",
        ]
        for p in PROVIDERS
    ]
    v1_rows = [
        [
            PROVIDERS[p]["display"],
            f"{len(failures[p])}/94",
            f"{len(failures[p]) / 94:.6f}",
            "FAIL" if len(failures[p]) / 94 > 0.10 else "PASS observed rule only",
        ]
        for p in PROVIDERS
    ]
    domain_rows = [
        [
            row["rank"],
            row["name"],
            row["weighted_total"],
            f"{row['weighted_pct']}%",
            row["blocked"],
        ]
        for row in state["second_domain_registry"]["ranking"]
    ]
    artifact_rows = [
        [row["artifact_id"], row["artifact_path"], row["evidence_class"], row["canonical_status"]]
        for row in evidence
    ]
    deps = ", ".join(f"{name}={version}" for name, version in dependencies.items())
    inventory_table = markdown_table(
        ["Measure", "Count"],
        [
            ["Regular files (excluding V11 output/caches)", f"{inv['files']:,}"],
            ["Directories", f"{inv['directories']:,}"],
            ["Bytes", f"{inv['bytes']:,}"],
            ["Empty files", inv["empty_files"]],
            ["Symlinks", inv["symlinks"]],
            ["Package Python modules", inv["python_modules"]],
            ["Test files", inv["test_files"]],
            ["Python scripts", inv["scripts"]],
            ["Notebooks", inv["notebooks"]],
            ["Config files", inv["configs"]],
            ["Paper-tree files", inv["paper_files"]],
            ["Docs-tree files", inv["docs"]],
        ],
    )
    large_file_table = markdown_table(
        ["Path", "Bytes"],
        [[row["path"], f"{row['bytes']:,}"] for row in inv["large_files"]],
    )
    empty_file_list = "\n".join(f"- `{path}`" for path in inv["empty_paths"]) or "- none"
    broken_symlink_list = (
        "\n".join(f"- `{path}`" for path in inv["broken_symlinks"]) or "- none"
    )
    reports: dict[str, str] = {}
    reports["V11_AUDIT_SESSION_MANIFEST.md"] = (
        report_header(
            "V11 Audit Session Manifest",
            "This manifest anchors the local-only full-ceiling audit without exposing a private root path.",
        )
        + f"""
## Environment

- Audit date: {datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()} Asia/Kolkata
- Repository root: `{ROOT_TOKEN}`
- Git state: not applicable; this directory is not a Git worktree
- Python: {platform.python_version()}
- OS/architecture: {platform.system()} / {platform.machine()}
- Logical CPUs: {os.cpu_count() or 'unknown'}
- Physical memory: {physical_memory_gib()}
- Accelerator execution: none; this audit used local CPU-safe operations only
- Key dependencies: {deps}

## Initial evidence counts

- Intervention pilot: 91 paired items and 182 rows per provider for 3 providers.
- V1 specificity: 94 paired items and 188 rows per provider for 3 providers.
- Current V2 package: 30 items, 60 images, zero provider-output files.
- Human validity: assistant-generated preliminary screening only; independent second-rater fields blank.
- Main-500: planned, not executed, and formally blocked.

## Initial failures and audit corrections

1. Historical task metadata called machine screening human reviewed; V11 supersedes that label without rewriting hash-bound raw files.
2. The 91-item pilot does not meet the 150 overall or 40-per-family policy.
3. Qwen fails the frozen V1 specificity gate at 12/94.
4. The current 30-item V2 set reuses every V1 item and has no model outputs.
5. Exact historical model revisions are not recorded.
6. Private-path and release-package scope differ from the older scoped privacy claim.

## Commands represented in this build

The generator reads local JSON/JSONL/CSV/config/package artifacts, recomputes pair flips,
exact McNemar tests, deterministic paired bootstrap intervals, hashes, and inventory counts.
External validation commands and their exit codes are tracked in
`V11_COMMAND_AND_EXIT_CODE_LOG.md`; a not-run entry is never interpreted as a pass.

## Files modified during the V11 pass

See `V11_CHANGE_MANIFEST.csv`. Raw model-output files were read and hash-bound, not overwritten.
Derived reports, task-package metadata, notebooks, tests, and release manifests were regenerated
only where the V11 audit identified a concrete defect.
"""
    )
    reports["CERTVIC_REPOSITORY_FORENSIC_INVENTORY.md"] = (
        report_header(
            "CertVIC Repository Forensic Inventory",
            "The inventory separates live code and evidence from generated, stale, synthetic, and release material.",
        )
        + f"""
## Current filesystem census

{inventory_table}

The walk excludes this V11 output directory plus `.git`, test/lint caches, and `__pycache__`.
The final tree contains {inv['duplicate_groups']} byte-identical content groups,
{inv['redundant_copies']} redundant copies, and {inv['redundant_bytes']:,} redundant bytes.
Those duplicates are retained because many are historical provenance or packaged copies; the
builder does not delete or silently choose among them.

## Largest current files

{large_file_table}

## Empty files

{empty_file_list}

## Broken symlinks

{broken_symlink_list}

## Baseline-to-final discrepancy

The initial audit snapshot recorded `ade20kdataset/ade20k.zip` and a substantially larger tree.
That path is absent from the final repository census. No V11 result depends on that archive, and
this pass did not restore it from a sibling project because cross-project copying was not authorized.
Treat the missing local source archive as a data-availability blocker for mining a new independent
control set; use `<PROJECT_PARENT>/certGen/ade20kdataset/ade20k.zip` only after the owner explicitly
confirms that it is the intended source copy.

## Evidence-bearing zones

- `data/results/main_real_200`: real raw outputs, derived reports, diagnostics, review templates, and historical audits coexist.
- `data/edits/spurious_flip_control`: canonical 94-item V1 control tasks and image pairs.
- `data/edits/spurious_v2_control`: 30-item retrospective stricter-control package.
- `data/results/v1_1_smoke_matrix` and `data/results/v2_1_sim_matrix`: software fixtures, never empirical evidence.
- `dist`: execution and release packages whose embedded manifests must be checked independently.
- `paper`: current V11 draft plus historical sections and generated intermediates.

## High-risk ambiguity

Historical V7--V10 reports use many ad hoc evidence-status strings. V11 does not normalize
the raw files in place. Instead, `configs/certvic_v11_protocol.yaml` and the evidence ledger
provide a hash-preserving canonical override. In particular, embedded
`HUMAN_REVIEWED_NON_EVIDENCE` labels do not establish human review.
"""
    )
    reports["CERTVIC_CANONICAL_ARTIFACT_INDEX.md"] = (
        report_header(
            "CertVIC Canonical Artifact Index",
            "Use this index before interpreting a similarly named historical report or package.",
        )
        + "\n## Canonical and superseded artifacts\n\n"
        + markdown_table(["Artifact ID", "Repository-relative path", "V11 class", "Status"], artifact_rows)
        + """

## Precedence rules

1. Raw prediction JSONL files outrank summaries when numerical values conflict.
2. `configs/certvic_v11_protocol.yaml` governs evidence classes and prospective decisions.
3. Embedded historical review labels in the task and prediction files are superseded by
   the hash-preserving mappings in that protocol.
4. `paper/main_v11.*` supersedes V9 prose but remains a non-eligible pilot draft.
5. The current V2 task package is canonical only as a retrospective diagnostic package;
   it is not the independent confirmatory set required by the protocol.
6. Historical and synthetic artifacts remain available for provenance and software testing,
   not as substitutes for missing real evidence.
"""
    )
    reports["CERTVIC_CLAIM_LEDGER.md"] = (
        report_header(
            "CertVIC Claim Ledger",
            "Every substantive claim is scoped to the exact artifact that can support it.",
        )
        + """
| Claim | Classification | Exact evidence | Required qualification |
|---|---|---|---|
| Three open-model prediction files exist for the 91-pair intervention pilot. | currently supported | canonical presence JSONL files in the evidence ledger | Real outputs; item validity remains pending human review. |
| Numerical intervention-gap CS lower bounds exceed 0.05 for all three models. | supported with qualification | three `pilot_result.json` artifacts and raw pairs | Numeric crossing is not full certification. |
| Qwen flips on 12/94 V1 irrelevant-edit pairs. | currently supported | canonical Qwen V1 JSONL | Frozen observed-rate gate fails; mechanism is unknown. |
| InternVL and LLaVA flip on 1/94 and 3/94 V1 pairs. | supported with qualification | canonical V1 JSONL files | Validity review is incomplete and revisions are unpinned. |
| Specificity differs by model in this pilot. | supported with qualification | paired same-item comparison | Retrospective, exploratory, one domain. |
| The 12 Qwen flips are parser or row-integrity failures. | contradicted by current evidence | pair-integrity forensic audit | All pairs parse and match; this does not establish a causal mechanism. |
| The current V2 package independently confirms specificity. | prohibited | V1/V2 item-ID intersection | All 30 items reuse V1 and no V2 outputs exist. |
| The current V2 package is a stricter retrospective sensitivity set. | diagnostic only | V2 task and quality manifests | Four known Qwen failures retained, eight filtered out. |
| The pilot tasks completed independent human review. | contradicted by current evidence | reviewer identity and blank second-rater sheet | Machine assistance is preliminary, not human-reviewed evidence. |
| Main-500 results exist or execution is currently allowed. | prohibited | V11 protocol | `execution_allowed_now=false`. |
| CertVIC is submission-ready. | prohibited | blocker and gate ledgers | Human, independent-control, reproducibility, and literature blockers remain. |

No ledger entry is paper-claim eligible in the current V11 state. This conservative setting
does not erase real observations; it prevents incomplete validity evidence from being promoted.
"""
    )
    reports["SOFTWARE_VALIDATION_AND_REPAIR_REPORT.md"] = (
        report_header(
            "Software Validation and Repair Report",
            "This report records the root-cause repairs already made in the V11 working tree and the remaining validation boundary.",
        )
        + """
## Repairs

| Area | Root cause | Repair | Regression surface |
|---|---|---|---|
| V2 importer | Earlier import accepted under-specified or stale inputs. | Transactional schema, row/key/provider/run/hash checks; atomic writes; idempotency and conflict refusal. | `tests/test_v9_spurious_v2_ingest_decision.py` |
| V2 notebooks | Provider scaffold did not guarantee two-device execution, exact model identity, or exact merged rows. | Generated notebooks now use the working runner spine, `Popen`, device-local processes, revision/cache locks, bundle and image hashes, resume checks, and the V11 v3 output manifest. | V2 builder/runbook and static notebook tests |
| Certification policy | A numerical gap helper could be confused with the complete policy. | Full sample, family, parse, specificity, evidence, and CS gates are applied together. | certification-policy tests |
| Historical review labels | Machine-assisted approval was represented as human-reviewed metadata. | V11 adds hash-preserving canonical overrides and fail-closed review integration. | claim and integration tests |
| Prompt ablations | Alternating source answers corrupted gold polarity. | Builders normalize source presence before applying ablation format. | prompt/mechanism tests |
| Detectability | Item variants could leak between folds and directional AUC could invert. | Grouped-by-item validation and symmetric AUC. | detectability tests |

## Validation boundary

The focused repaired surfaces passed 124 tests during the V11 working session. The authoritative
final count, lint status, notebook result, package integrity, claim guard, privacy scan, and paper
checks must be taken from the command ledger after they are rerun. A historical statement such as
"657 passed" is not treated as current merely because it appears in an older handoff.

No repair changes a raw model response, V1 item membership, frozen threshold, or failure count.
"""
    )
    reports["SCIENTIFIC_VALIDITY_AUDIT.md"] = (
        report_header(
            "Scientific Validity Audit",
            "The scientific question is whether intended responsiveness is separable from specificity under irrelevant edits.",
        )
        + f"""
## Intervention pilot

{markdown_table(['Model', 'n', 'a', 'raw answer-change p', 'gap', 'CS LB', 'full certified'], pilot_rows)}

The historical quantity `p` is raw response change, not necessarily correct semantic updating.
Qwen and InternVL changes end on edited gold for 16/91 and 9/91 items. LLaVA changes on 16/91,
but only 13 reach edited gold. The full policy fails because n=91 < 150, family counts are
54/31/6, validity review is incomplete, and specificity is not uniformly cleared.

## Specificity pilot

{markdown_table(['Model', 'V1 flips', 'rate', 'frozen V1 status'], v1_rows)}

The current evidence supports a model-dependent pilot observation. It does not support a broad
robustness, causal-understanding, architecture, or population-generalization claim. All outputs
come from one ADE20K-derived household/object setting, and exact historical revisions are missing.

## Validity threats

- Inclusion decisions are machine-assisted preliminary, despite stale embedded labels.
- Conservative image-difference boxes intersect target boxes on 20/94 V1 controls; target-mask overlap is zero.
- Corrected grouped detectability is moderate, not proof that artifacts are absent.
- Current V2 is post-outcome and reuses V1; selection can change failure composition.
- The natural perception control shows unedited object recognition but cannot validate edited images.
"""
    )
    reports["STATISTICAL_AUDIT_AND_POWER_PLAN.md"] = (
        report_header(
            "Statistical Audit and Power Plan",
            "This audit distinguishes descriptive point estimates, time-uniform pilot bounds, and prospective specificity decisions.",
        )
        + f"""
## Verified estimands

For intervention item i, `a = mean(original correctness)`, `p = mean(raw answer change)`, and
`gap = a - p`. The bounded gap variable is mapped to `(A_i - C_i + 1)/2` for the confidence
sequence. Parser failures must be reported and may not be dropped to improve a gate.

{markdown_table(['Model', 'n', 'a', 'p', 'gap', 'CS LB', 'full certified'], pilot_rows)}

## Specificity decisions

- Frozen V1 continuity rule: observed flip rate <= 0.10. Do not retrofit an interval rule to V1.
- Prospective independent V2 primary: one-sided 95% Clopper-Pearson upper bound <= 0.10 for Qwen.
- Joint three-model statement: Bonferroni one-sided alpha=0.05/3 and every upper bound <= 0.10.
- Missing or unparseable pairs count as flips in the primary endpoint and are reported separately.
- Raw and pre-result validity-filtered results must both be shown.

With zero observed flips, the one-model bound first falls to at most 0.10 at n=29; under the
three-model Bonferroni level it requires n=39. Those best-case thresholds do not constitute a
power analysis for nonzero true rates. Design should report operating characteristics across
plausible rates (for example 0.01, 0.03, 0.05, 0.08, and 0.12) and choose n before outputs.

The deterministic planning tables under `analysis/supported_results/` provide: exact-binomial
specificity pass probability for n=30, 60, 94, 150, 200, 300, and 500 over six true-rate
assumptions; paired-model normal-approximation sensitivity over discordance 0.10--0.30 and risk
differences 0.05--0.15; conservative two-domain interaction sensitivity over effects 0.05--0.20;
and two-rater raw-agreement precision for agreement 0.80/0.90 and half-width 0.05--0.10. Every row
is `PLANNED_NOT_EXECUTED`; exact simulation and prevalence-sensitive kappa planning must be frozen
before a confirmatory design.

Main-500 is not justified merely because 500 is larger. Its value is balanced family/category
coverage and interaction estimation after the simple specificity gate is resolved. If the locked
analysis only needs an overall one-model specificity decision, the prospective table may justify a
smaller independent set; if it targets strata or domain interactions, sparse-cell requirements may
justify 500 or more. The design owner must state which question determines n before outcomes.

## Paired exploratory comparisons

See `V11_PAIRED_COMPARISONS.csv`. Exact McNemar tests use discordant same-item pairs; deterministic
paired bootstrap intervals use 20,000 resamples and fixed seeds. These tests are retrospective.
Holm correction across three comparisons leaves Qwen--InternVL below 0.05 but not Qwen--LLaVA.

## Confidence-sequence audit

The active fallback is `certvic.anytime_cs.hoeffding_mixture` because optional `confseq` is absent.
It applies a two-sided Gaussian-mixture Hoeffding boundary to the bounded transform
`(A_i-C_i+1)/2`, then maps back to the gap scale. Closed-form numerical reference, range, empty-input,
width, backend, and continuous-peeking simulation tests are present. The guarantee assumes the
mixture horizon/tuning, item order, and endpoint are fixed independently of outcomes and that the
bounded conditional-mean supermartingale condition is defensible. Historical n=91 was a fixed task
set; an adaptively chosen stopping-time horizon must not be reused as `t_opt` after looking at data.
No finite-population correction is used, and the bound does not turn the ADE20K items into a random
sample from a broader VLM population. Report the CS numerical crossing separately from sample,
family, validity, specificity, revision, and claim-eligibility gates.
"""
    )
    failures_md = "\n".join(f"- `{item_id}`" for item_id in state["qwen_failures"])
    reports["QWEN_12_FAILURE_FORENSIC_AUDIT.md"] = (
        report_header(
            "Qwen 12-Failure Forensic Audit",
            "The frozen V1 Qwen failures were reconstructed from raw paired rows without changing membership.",
        )
        + f"""
## Reproduced failures

{failures_md}

Every listed pair changes from parsed `yes` on the original to parsed `no` on the edited image.
All 188 Qwen rows parse; item/variant keys are complete and unique; provider and run metadata are
internally consistent. InternVL and LLaVA do not flip on these twelve items. No parser, missing-row,
duplicate-row, or image-key defect explains the Qwen count.

The compact row-level table at
`analysis/supported_results/qwen_12_forensic_table.csv` records each source ID, both image paths and
SHA-256 values, prompt, expected answers, raw and parsed answers for all three providers, parse
status, objective overlap/distance metadata, and exclusion status. The outcome-blind image packet is
`human_review_packet/reviewer_bundle/tracks/diagnostic_subset12`; its reviewer materials do not
contain provider identity, failure status, source IDs, or the coordinator selection key.

Two failures have conservative difference bounding boxes that intersect the target box; all twelve
have zero target-mask overlap. This supports targeted follow-up, not an exclusion after viewing
outcomes. Machine-generated visual categories in historical forensics are diagnostics only and do
not establish validity or mechanism.

The defensible conclusion is narrow: Qwen shows model-specific sensitivity on these irrelevant-edit
pairs. Architecture, quantization, processor behavior, or visual salience cannot be separated with
the present unpinned runs and incomplete human review.
"""
    )
    quality = state["v2_quality"]
    v2_bundle = state["v2_bundle"]
    v2_zip_path = "dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip"
    v2_zip_hash = sha256(v2_zip_path)
    review_manifest = state["review_manifest"] or {}
    review_zip_hash = str(review_manifest.get("reviewer_zip_sha256", "NOT_BUILT"))
    main_auc = (
        state["main_detectability"]["classifier"]["auc"]
        if state["main_detectability"]
        else "NOT_COMPUTED"
    )
    v1_auc = state["v1_detectability"]["classifier"]["auc"]
    v2_auc = (
        state["v2_detectability"]["classifier"]["auc"]
        if state["v2_detectability"]
        else "NOT_COMPUTED"
    )
    reports["SPURIOUS_V2_AND_V2_LARGE_READINESS.md"] = (
        report_header(
            "Spurious V2 and V2-Large Readiness",
            "The existing 30-item package is ready for a private retrospective diagnostic run, not a confirmatory claim.",
        )
        + f"""
## Current 30-item package

- Unique items: {len(state['v2_tasks'])}; V1 ID overlap: {state['v2_overlap_v1']}/30.
- Object distribution: {json.dumps(quality['class_distribution'], sort_keys=True)}.
- Patch-to-target-box distance: min {quality['bbox_distance_summary']['min_distance_px']} px,
  median {quality['bbox_distance_summary']['median_distance_px']} px, max
  {quality['bbox_distance_summary']['max_distance_px']} px.
- Target-box intersections: {quality['bbox_overlap_count']}; target-mask overlap: 0.
- Historical scores available to the retrospective selector: {state['v2_historical_numeric_detectability']}/30.
- V11 post-selection, pre-provider diagnostic scores now hash-locked: {state['v2_v11_numeric_detectability']}/30;
  they cannot justify retroactive exclusion or confirmatory status.
- Grouped-item symmetric set-level AUC: {v2_auc}, below the 0.80 repository flag but not proof
  of imperceptibility, semantic invariance, or outcome-unseen selection.
- V2 image entries hash-locked in the bundle manifest: {len(v2_bundle.get('image_entries', []))}/60.
- Current private control ZIP SHA-256: `{v2_zip_hash}` (recompute after every rebuild).
- Known Qwen V1 failures retained: {state['v2_qwen_retained']}/12; filtered out:
  {state['v2_qwen_filtered']}/12.
- Provider output files found: 0/3.
- Full local candidate audit: `SPURIOUS_V2_LOCAL_CANDIDATE_INVENTORY.csv` records all
  94 V1-derived candidates, 30 retained and 64 rejected, with geometry, available salience,
  duplicate-risk, and decision reasons. Every row is retrospective and confirmatory-ineligible.

Because all 30 items were selected from V1 after its outcomes, no result on this package can
confirm or clear specificity. It may quantify sensitivity to stricter geometry/salience filtering.
The raw V1 result must remain beside any V2 diagnostic result.

## V2-Large requirement

Create an independent pool with zero V1 overlap, lock exclusions and ordering before outputs,
complete two-rater blinded validity review, choose n from the prospective operating-characteristic
table, and hash-lock tasks. The one-model upper-bound rule needs at least 29 zero-failure items;
the simultaneous three-model best case needs at least 39, with larger n required for useful power
at nonzero rates.

`configs/certvic_v11_protocol.yaml` machine-locks zero target overlap, at least 75 px bbox distance,
set-level low-level AUC <= 0.80, category/spatial balance, exact/perceptual duplicate checks, image
quality, answer invariance, and two-rater acceptance. Perturbation-area, per-item salience,
category targets, image-quality, and perceptual-duplicate thresholds remain
`TBD_BEFORE_BUILD`; `unresolved_tbd_blocks_selection=true`, so no independent item selection is
authorized until those values are frozen.

Source rows state `redistribution_allowed=false`; the existing image zip is a private Kaggle input,
not a public release artifact until licensing is independently verified.

## Runtime contract

The importer requires exact schema `certvic.v11.spurious_v2.kaggle_output_manifest.v3`.
Each notebook must receive a 40-character immutable model revision and exact code/control-bundle
SHA-256 values. Static-valid notebooks are not runnable while `MODEL_REVISION` is null.
"""
    )
    reports["SPURIOUS_V2_EXECUTION_CARD.md"] = (
        report_header(
            "Spurious V2 Execution Card",
            "This card prevents a diagnostic run from being mistaken for confirmatory evidence.",
        )
        + """
## Before execution

This is an optional retrospective diagnostic run, not the mandatory independent confirmatory set.
Before uploading, complete or explicitly waive diagnostic-only review without exposing V1 outcomes,
fill each notebook's `MODEL_REVISION` with an exact 40-character commit, and rerun the local locks.

```bash
python3 scripts/build_kaggle_main200_bundle.py
python3 scripts/build_spurious_v2_control.py
python3 scripts/validate_t4x2_notebooks.py \\
  --out reports/v11_full_ceiling_audit/notebook_static_validation.json
python3 -m pytest -q tests/test_v9_spurious_v2_ingest_decision.py \\
  tests/test_v9_spurious_v2_builder.py tests/test_v9_spurious_v2_runbooks.py
```

## Exact Kaggle inputs and settings

Upload both inputs to each private notebook session:

1. `dist/certvic_kaggle_main200_bundle.zip`
2. `dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip`

Use Accelerator `GPU T4 x2`, Internet `ON` for a fresh public-model download, no paid API,
and no credential except an optional Hugging Face read token when the repository requires it.
The notebooks verify task, 60 image-member, code-bundle, control-bundle, and model-revision locks.

Run in this exact operational order:

1. `notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb`
2. `notebooks/kaggle/vlm_internvl_8b_spurious_v2_T4x2.ipynb`
3. `notebooks/kaggle/vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb`

Each notebook must produce exactly 60 merged rows and one schema-v3 runtime manifest. Expected
archives are `qwen2_5_vl_7b_spurious_v2_preds.zip`,
`internvl_8b_spurious_v2_preds.zip`, and `llava_onevision_7b_spurious_v2_preds.zip`.
Runbook-only T4x2 estimates, not measured V11 runtimes, are 12--25, 10--20, and 15--30 minutes;
single-GPU fallback estimates are 25--45, 20--40, and 30--60 minutes respectively.

## During and after execution

Download all three archives into `kaggleoutputs/v9_spurious_v2/`, then run:

```bash
python3 scripts/import_v9_spurious_v2_outputs.py \\
  --input-dir kaggleoutputs/v9_spurious_v2 \\
  --out-dir data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest
python3 -m pytest -q tests/test_v9_spurious_v2_ingest_decision.py
```

The importer requires all three providers at once, exact source/prediction hashes, 60 rows each,
strict parses, exact item/variant keys, provider/run IDs, pinned revisions, and conflict-free atomic
writes. Missing or unparseable pairs fail closed. The result remains `DIAGNOSTIC_ONLY` and
`paper_evidence=false` regardless of its numerical rate; it cannot unlock Main-500.
The final diagnostic gate artifact is
`data/results/main_real_200/v9_mega_upgrade/spurious_v2_specificity_results.json`
(or the explicit `--report-dir`);
do not route this retrospective set through the Main-500 readiness gate.

For recovery, rerun the same notebook with unchanged inputs/revision. Complete shard files are
reused only when their exact denominators validate; incomplete shards resume, merge is deterministic,
and any canonical hash conflict stops without overwrite.

## Stop condition

If hashes, provider/run IDs, item/variant keys, strict parsing, or row counts disagree, stop and
preserve inputs. Do not partially write canonical outputs.
"""
    )
    reports["HUMAN_REVIEW_OPERATIONS_AND_BLINDING.md"] = (
        report_header(
            "Human Review Operations and Blinding",
            "No independent human label exists yet; this document is an operating protocol, not a completed review report.",
        )
        + f"""
## Required review lanes

1. Review all 91 intervention pairs for target change, answer update validity, single-factor validity,
   answerability, ambiguity, artifact severity, and retain/exclude recommendation.
2. Review all 94 V1 specificity pairs for target preservation, answer invariance, perturbation
   acceptability, ambiguity, and retention.
3. Review the 30 current V2 pairs only as a retrospective diagnostic set.
4. Review the 12 Qwen forensic pairs in an anonymized lane that does not disclose provider or failure status.

## Blinding and provenance

- Deterministically randomize pair order and A/B orientation; keep the key outside reviewer bundles.
- Two independent human raters must use distinct IDs and ISO timestamps.
- Do not show provider outputs, V1 failure IDs, existing assistant labels, or selection reasons.
- Preserve both raw rater sheets; adjudicate disagreements without overwriting them.
- Report per-field agreement, Cohen kappa where meaningful, exclusions, and sensitivity with and without exclusions.
- Record item ID, objective reason, rater/rule source, timestamp, evidence pointer, and pre-result flag.

The existing `assistant_visual_review_v1` decisions are `MACHINE_ASSISTED_PRELIMINARY`.
They may seed a queue but cannot be relabeled as independent human evidence.

The deterministic private reviewer packet contains {review_manifest.get('n_tracks', 4)} tracks and
{review_manifest.get('n_unique_review_rows', 227)} unique pairs (91 + 94 + 30 + 12). Its current
reviewer ZIP hash is `{review_zip_hash}`. The hash identifies a blank packet, not completed review.
"""
    )
    reports["MAIN500_DESIGN_LOCK_AND_GO_NOGO.md"] = (
        report_header(
            "Main-500 Design Lock and Go/No-Go",
            "Decision: **NO-GO**. `execution_allowed_now=false` and `paper_evidence=false`.",
        )
        + """
## Locked design elements

- Seed 11011; source pool restricted to local ADE20K until formally amended.
- Outcome-blind selection and replacement from the same locked stratum, first unused item only.
- Strata: target object, image complexity, target size/position, edit type/magnitude,
  answer polarity, question template, and source split.
- Every raw response, parse status, exclusion, and quality field remains traceable.

## Mandatory GO prerequisites

1. Valid specificity outputs for every declared model under the applicable protocol.
2. Human review completed before output unblinding.
3. Transactional importer passes positive, negative, idempotency, and conflict tests.
4. Specificity branch receives signed scientific sign-off.
5. Objective quality and complete detectability gates pass without post-result tuning.
6. Exact model and processor revisions are pinned.

Current status: prerequisites 1, 2, 4, 5, and 6 are false; the current reused V2 cannot satisfy
the independent-specificity requirement. Main-500 may be designed and queued, but not executed or
described as observed evidence.
"""
    )
    reports["SECOND_DOMAIN_DECISION.md"] = (
        report_header(
            "Second-Domain Decision",
            "Decision: prepare a small COCO-2017 confirmatory plan after specificity repair; execute no second domain now.",
        )
        + f"""
## Existing repository ranking

{markdown_table(['Rank', 'Candidate', 'Weighted score / 90', 'Percent', 'Blocked in registry'], domain_rows)}

The scoring registry evaluates class overlap, edit suitability, masks, licensing, free-compute
feasibility, annotation simplicity, review burden, and likely reviewer objections. These are
planning scores, not observed evidence, and the stored licensing notes require current primary-source
verification before acquisition or release.

## Decision and scope

Current real evidence is ADE20K-derived and concentrated on household/object-presence questions.
No ready, license-verified second-domain asset pool is present locally. COCO 2017 ranks first at
80/90 because it overlaps chair/couch/car/table while offering instance masks and a practical small
validation split; LVIS is second but shares COCO pixels, Open Images adds pipeline burden,
Cityscapes has domain/license friction, and SA-1B lacks semantic labels at impractical scale.

After an independent specificity set passes its validity/import gates, prepare only a small,
preregistered COCO confirmation using pointer-only image handling. Its purpose is to test whether
the responsiveness--specificity separation survives a different image/annotation distribution.
Do not let this main-paper confirmation expand into a multi-domain journal program. TPAMI/IJCV scope
may later add multiple domains, longitudinal model versions, and broader interaction analysis.
"""
    )
    reports["MODEL_MATRIX_DECISION.md"] = (
        report_header(
            "Model Matrix Decision",
            "Keep the three-model open-weight matrix for continuity; do not add models before pinning the existing runs.",
        )
        + """
| Provider | Repository ID | Historical revision | Current role |
|---|---|---|---|
| qwen2_5_vl_7b | Qwen/Qwen2.5-VL-7B-Instruct | unpinned / `unloaded` | primary specificity model |
| internvl_8b | OpenGVLab/InternVL2-8B | unpinned / `unloaded` | paired comparator |
| llava_onevision_7b | llava-hf/llava-onevision-qwen2-7b-ov-hf | unpinned / `unloaded` | paired comparator |

Before a new run, record immutable model and processor commits, tokenizer/processor configuration,
precision/quantization, image preprocessing, framework versions, hardware class, decoding settings,
and input/package hashes. Preserve Qwen as the predeclared primary V2 model; a three-model statement
requires the Bonferroni rule. The V11 runbooks freeze `max_new_tokens=16`, `do_sample=false`,
`temperature=0`, strict yes/no parsing, exact model commits, and hash-locked code/control inputs.

## Optional expansion ranking

| Rank | Expansion | Scientific value | Feasibility / license condition | Decision |
|---|---|---|---|---|
| 1 | Size-controlled checkpoint in an existing family | separates family from scale effects | only an open, immutable revision that fits free Kaggle | planned after core evidence |
| 2 | A fourth open model with a distinct vision encoder/training family | increases architectural diversity | reproducible processor, redistributable metadata, T4x2 fit required | high-value optional |
| 3 | Larger open checkpoint | tests scale trend | likely higher memory/runtime and must not delay independent controls | enhancement only |
| 4 | Closed/API model | external relevance | cost, version opacity, and reproducibility conflict with the core protocol | exclude from core; reference-only if separately authorized |

No expansion can repair invalid item selection or missing human review. Do not add a fourth model
until the three current revisions and processors are pinned and the independent specificity set is locked.
"""
    )
    reports["PAPER_AND_NOVELTY_AUDIT.md"] = (
        report_header(
            "Paper and Novelty Audit",
            "The V11 paper is an evidence-safe pilot draft, not a submission-ready manuscript.",
        )
        + f"""
## Defensible contribution

The strongest current framing is a protocol contribution: separate responsiveness under intended
interventions from specificity under matched irrelevant edits, retain raw paired traces, and attach
explicit uncertainty and claim gates. The pilot observation is that these quantities separate and
that specificity is model-dependent on the available V1 control.

## Prohibited overreach

- Do not claim causal visual understanding, universal robustness, architecture-level explanation,
  independent V2 confirmation, completed human validation, broad domain generalization, or certification.
- Do not call a numerical CS crossing the full scientific gate.
- Do not describe current V2 or Main-500 outputs; none exist.
- Do not make priority claims until primary literature and bibliographic anchors are verified.

## Section-level gap audit

| Section | Current quality / evidence conflict | Required repair | Completed locally? |
|---|---|---|---|
| Title/abstract | evidence-safe short draft; contribution hierarchy still provisional | lead with responsiveness--specificity protocol and pilot scope | partial |
| Introduction | problem distinction present; novelty comparison unsupported | add source-backed gap and one primary contribution | no, citations blocked |
| Related work | no verified bibliography | compare counterfactual editing, VLM consistency, robustness, and confidence sequences using primary sources | no |
| Method | estimands and CS present; “certified” can be misread | map every symbol to code and state conditional guarantee/non-guarantees | yes in V11 spec; paper partial |
| Experimental design | real pilot described; review/revision provenance incomplete | add frozen independent-set, blinding, missing-data, and model-setting contracts | protocol complete, evidence pending |
| Results | exact pilot/V1 table present; no V2/Main-500 result | keep pilot result hierarchy and explicit missing-result placeholders | yes |
| Failure analysis | Qwen observation framed scientifically; mechanism unknown | insert blinded human outcomes and salience sensitivity when real | pending evidence |
| Limitations/ethics | main blockers stated; dataset/license ethics incomplete | add redistribution, annotation, environmental/compute, and scope discussion | partial |
| Figures | no overloaded engineering figure; conceptual visual absent | add one responsiveness-vs-specificity protocol figure from verified design | no |
| Tables | main pilot table answers a scientific question | add paired uncertainty and validity table after real review | partial |
| Appendix/reproducibility | audit artifacts exist outside manuscript | link schemas, hashes, parser tests, model revisions, and review codebook | partial |
| Bibliography/anonymity | anonymity passes; bibliography absent | create and verify `.bib`, citations, and source priority before submission | anonymity yes; bibliography no |

## Paper readiness

`paper/main_v11.pdf` compiles to a short evidence-bound draft and was rendered page-by-page for
layout review. Remaining paper blockers are empirical scope, human validity, independent specificity,
reproducibility metadata, citations, and a complete anonymous release. All current ledger entries
remain `paper_evidence=false`.

Repository-root LICENSE/COPYING present: {str(state['repo_license_present']).lower()}; paper
bibliography file present: {str(state['paper_bibliography_present']).lower()}. The existing
`docs/CITATION_TODO.md` is a reminder, not a bibliography or source verification.
"""
    )
    reports["REVIEWER_RED_TEAM_V11.md"] = (
        report_header(
            "Reviewer Red Team V11",
            "Likely reviewer attacks are listed with the evidence needed to answer them, not rhetorical workarounds.",
        )
        + """
| Reviewer persona | Criticism | Severity / valid? | Current evidence and repair | Experiment or action required | Acceptance threat |
|---|---|---|---|---|---|
| Benchmark skeptic | The 30-item V2 is too small and post-selected. | critical / yes | 30/30 overlap V1; V11 reclassifies it diagnostic and preserves V1. | Powered unseen set with frozen construction and review. | fatal to confirmatory specificity |
| VLM evaluation | Qwen's 12/94 failure may be edit salience, not specificity. | critical / yes | 12 raw flips reproduce; 2 failure boxes intersect conservative target boxes; mechanism unassigned. | Outcome-blind validity plus salience-matched independent controls and pinned rerun. | high |
| Statistics | The 0.10 threshold is arbitrary and observed-rate gating ignores uncertainty. | high / yes | Historical V1 rule remains frozen; prospective CP/Bonferroni rules are separated. | Justify threshold scientifically and lock operating characteristics before results. | high |
| Reproducibility | No independent human validation exists. | critical / yes | Assistant screening overridden; blank two-rater packet and fail-closed validator delivered. | Two raters, adjudication, agreement, raw/filtered sensitivity. | fatal to submission |
| VLM evaluation | Edits may be trivially detectable or contaminate targets. | high / yes | Grouped AUC .7123; 20/94 conservative bbox intersections, zero mask overlap; no causal attribution. | Review, complete pre-result metrics, salience-stratified sensitivity, no post-hoc drops. | high |
| Causal inference | V2 selection saw Qwen outcomes. | critical / yes | Four failures retained and eight filtered; V11 explicitly marks post-selection. | Zero-overlap source pool and immutable pre-output inclusion/exclusion ledger. | fatal to confirmation |
| VLM evaluation | Parser choices could manufacture flips. | medium / addressed for current yes/no | All V1 rows strict-parse; raw text reparses; malformed/contradictory cases fail closed. | Preserve raw outputs and apply the same parser/version to pinned reruns. | low now, high if drift recurs |
| Reproducibility | Model differences may be version, precision, or processor artifacts. | critical / yes | Historical `model_version=unloaded`; V11 notebooks now refuse null revisions and record bundle hashes. | Exact commits, processors, precision, packages, preprocessing, and retry rules. | high |
| VLM evaluation | Three open 7--8B models are not broad coverage. | medium / yes | Three distinct open families, but limited scale/training diversity. | Optional fourth distinct open family only after core blockers; closed model reference-only. | ceiling-limiting |
| Benchmark skeptic | One ADE20K-derived domain cannot support generalization. | high / yes | All real evidence is one household/object setting. | Small preregistered COCO confirmation after specificity repair. | high for main track |
| Statistics | Multiple models and exploratory diagnostics inflate false positives. | high / yes | Paired tests labeled retrospective; Holm applied; Qwen is prospective primary; joint rule Bonferroni. | Freeze confirmatory family and keep diagnostics secondary. | medium after repair |
| Statistics | “Certified” sounds like formal robustness certification. | high / yes | V11 says numerical time-uniform CS crossing, not deployment or perturbation-set robustness; full gate false. | Define guarantee in abstract/method and avoid unqualified certification. | high |
| Hostile novelty | This is a confidence-interval wrapper around another edit benchmark. | critical / unresolved | Best distinction is joint responsiveness vs irrelevant-edit specificity with traceable intervention pairs. | Source-backed related work and baselines that show what ordinary consistency misses. | fatal if not sharpened |
| Benchmark skeptic | The repository is overengineered relative to the science. | high / yes | V11 consolidates into canonical ledgers, one analysis rebuild, one review path, and one execution card. | Stop new wrappers; spend effort on independent items, humans, domain evidence, and paper. | medium |
| Reproducibility | Data/package release may violate licenses or leak paths. | high / yes | V2/reviewer images private; session2 ZIP quarantined; no repository license. | License determination, pointer-only release, exact-archive recursive audit, project license. | high for artifact track |
"""
    )
    reports["REPRODUCIBILITY_AND_RELEASE_AUDIT.md"] = (
        report_header(
            "Reproducibility and Release Audit",
            "The code path is substantially stronger than the evidence-release path; they must be evaluated separately.",
        )
        + f"""
## Current package locks

- Main code/config bundle: `{sha256('dist/certvic_kaggle_main200_bundle.zip')}`;
  {state['main_bundle_manifest'].get('n_entries')} manifest entries and content digest
  `{state['main_bundle_manifest'].get('content_digest')}`.
- Retrospective private V2 bundle: `{v2_zip_hash}`; 30 tasks and
  {len(v2_bundle.get('image_entries', []))} hash-locked image members.
- Private blinded reviewer bundle: `{review_zip_hash}`; blank human fields and no coordinator keys.
- `dist/certvic_main200_session2_data.zip`: quarantined historical/non-release archive.

## Reproducible surfaces

- Canonical raw prediction files are hash-bound in the evidence ledger.
- V1 item membership and frozen decision rule are preserved.
- V2 package construction and importer now have deterministic/transactional contracts.
- Pairwise statistics use explicit fixed bootstrap seeds.
- Synthetic results remain labeled test fixtures.

## Minimal reproducible path

1. Run `python3 -m pytest -q` and `python3 -m ruff check --no-cache certvic scripts tests`.
2. Inspect `CERTVIC_EVIDENCE_LEDGER.json`, then run
   `python3 scripts/rebuild_v11_supported_analysis.py` to reproduce supported numbers.
3. Inspect private pending packages with `scripts/build_spurious_v2_control.py`,
   `scripts/validate_t4x2_notebooks.py`, and the human-review packet validator.
4. Before any provider run, fill exact model commits and preserve the printed code/control hashes.
5. Import returned archives only through `scripts/import_v9_spurious_v2_outputs.py`.
6. Read `CERTVIC_GATE_LEDGER.csv`; do not infer a gate from a point estimate.
7. Build the paper twice with `pdflatex -interaction=nonstopmode -halt-on-error main_v11.tex`
   and visually inspect the rendered pages.
8. Read `CERTVIC_BLOCKER_REGISTER.csv` and the master handoff before selecting any next experiment.

## Release blockers

- Historical model/processor revisions are missing.
- Independent human review and exclusion provenance are incomplete.
- V2 imagery has `redistribution_allowed=false` in source metadata.
- `dist/certvic_main200_session2_data.zip` contains {state['session2_private_occurrences']}
  private-root occurrences and is explicitly non-release material.
- Repository-root LICENSE/COPYING present: {str(state['repo_license_present']).lower()}; paper
  bibliography present: {str(state['paper_bibliography_present']).lower()}.
- Older archives and generated results contain scoped or stale manifests; release integrity must use
  current hashes rather than V10.2 hash claims.
- The initial broad path scan found 195 files containing a private-root prefix, while older privacy
  checks excluded several generated/data trees. This V11 packet itself uses `{ROOT_TOKEN}` only.

## Safe release boundary

Until licensing is resolved, release code, schemas, task IDs, hashes, derived aggregate tables, and
pointer manifests; keep source-derived image bundles private. Run claim, privacy, package, anonymity,
and manifest checks on the exact candidate archive, not only on selected source trees.
"""
    )
    reports["VENUE_CEILING_AND_RESEARCH_ROADMAP.md"] = (
        report_header(
            "Venue Ceiling and Research Roadmap",
            "Venue fit is conditional and does not predict acceptance.",
        )
        + """
| State | Evidence and maturity | Best-fit level | Ceiling limits |
|---|---|---|---|
| Current | Real pilot outputs; incomplete human validity; one domain; retrospective V2 only | benchmark/evaluation workshop or internal technical report | not main-conference ready |
| Minimum credible completed | Blinded review, pinned three-model rerun, powered unseen specificity control, complete release | WACV or strong evaluation workshop; possible specialized conference paper | breadth and novelty comparison remain limited |
| Highest realistic | Powered Main-500, independent specificity, second-domain confirmation, source-backed novelty, full anonymous release | CVPR/ICCV/ECCV or ML evaluation venues if empirical story is strong | acceptance depends on novelty and evidence, not tooling volume |
| Journal extension | Multi-domain, broader models, longitudinal/version robustness, mature theory and release | TPAMI or IJCV candidate | requires substantially more evidence than the current pass |

## Venue fit by completed state

| Venue | Current fit | Minimum credible completed fit | Highest realistic requirement |
|---|---|---|---|
| WACV | weak pilot/workshop today | best-fit first full venue after human review, unseen specificity, pinned runs, and release | stronger domain confirmation improves odds |
| CVPR / ICCV / ECCV | not ready | still risky without breadth/novelty comparison | powered Main-500, one independent domain, clear scientific story, full artifact |
| NeurIPS / ICML / ICLR | not ready | poor fit as a vision-only benchmark | methodology must generalize beyond one visual benchmark with strong statistical/evaluation baselines |
| benchmark/evaluation workshops | suitable for transparent pilot discussion | strong fit after mandatory blockers | useful launch venue, not evidence of main-track ceiling |
| TPAMI / IJCV | not journal-ready | insufficient breadth | multi-domain, broader models/scales, longitudinal replication, deeper theory, mature public benchmark |

## Prioritized research plan

| Level / action | Scientific question | Required input / current status | Expected evidence | Compute / human burden | Dependency / acceptance value / stop condition |
|---|---|---|---|---|---|
| L1: pilot91 + V1-94 blinded review | are the intended and irrelevant edits visually valid? | private packet ready; labels pending | two raw sheets, adjudication, agreement, raw/filtered sensitivity | CPU only / high human | before unblinding new outputs; critical; stop on unresolved validity or pool overlap |
| L1: independent specificity set | does specificity hold on outcome-unseen controls? | source archive and TBD rules unresolved | immutable tasks/images/hashes and pre-output exclusions | local prep + image generation / high human | after rule/source lock; critical; stop if power/quality/source independence fails |
| L1: pinned three-model execution/import | do Qwen and comparators pass prospective specificity? | static notebooks/importer ready, revisions and real outputs absent | schema-v3 raw rows, manifests, one-sided decisions | free Kaggle GPU / low human after review | after independent set; critical; stop on any hash/key/parse/revision mismatch |
| L1: specificity sign-off | which model-dependent narrative is supported? | analysis specification ready | raw and validity-filtered gate ledger | CPU / scientific sign-off | after import; critical; stop if conclusion changes under predeclared sensitivity |
| L2: balanced Main-500 | does responsiveness remain strong across powered strata? | design locked, execution NO-GO | powered primary/stratified estimates and CS | high GPU/edit generation / high review | only after GO; main-track value; stop if quality cells cannot be filled prospectively |
| L2: small COCO confirmation | does the separation generalize across image/annotation distribution? | ranked plan only; no assets/license verification | preregistered cross-domain interaction and replication | medium GPU / medium review | after specificity; high reviewer value; stop if license or semantic mapping fails |
| L2: paper/literature/release completion | is the protocol novel, interpretable, and reproducible? | V11 draft/audit ready; bibliography/license absent | source-backed comparisons, anonymous pointer-safe artifact | low compute / high researcher | parallel after L1; critical; stop unsupported priority claims |
| L3: fourth complementary open family | is behavior architecture/training-family dependent? | optional, no model selected | pinned paired replication | medium/high GPU / no new review if same locked items | after core evidence; moderate value; stop if it delays L1/L2 |
| L3: prompt/edit-family replication | are findings stable to prompt and control construction? | diagnostics exist but are exploratory | preregistered sensitivity and replication | medium GPU / targeted review | after primary result; moderate value; stop when qualitative conclusion is stable |
| L4: multi-domain/longitudinal benchmark | how stable is specificity across domains, scales, and model versions? | not started | several domains, repeated commits, public benchmark governance | very high / very high | journal only; stop if first extension adds no new scientific interaction |
| L4: deeper theory/challenge | can the empirical certificate support a reusable evaluation theory? | current theorem scope limited | formal assumptions, external replication, challenge protocol | high research / community | TPAMI/IJCV ceiling; stop before inventing guarantees unsupported by executable estimands |

NeurIPS, ICML, and ICLR become plausible only if the statistical/evaluation methodology generalizes
beyond a vision benchmark and is compared rigorously with strong baselines. The shortest path is:
two-rater blinded review of pilot91 and V1-94; build a powered independent unseen control; pin and run
the existing model matrix; decide the specificity branch; then unlock Main-500 and a small second domain.
"""
    )
    reports["V11_COMMAND_AND_EXIT_CODE_LOG.md"] = (
        report_header(
            "V11 Command and Exit-Code Log",
            "Entries distinguish completed checks from commands that must still be run by the final validation owner.",
        )
        + """
| Check | Exact command | Exit code | Current interpretation |
|---|---|---:|---|
| Focused repaired surfaces | `python3 -m pytest -q tests/test_v9_spurious_v2_ingest_decision.py tests/test_v9_spurious_v2_builder.py tests/test_v9_spurious_v2_runbooks.py tests/test_remaining_kaggle_runbooks.py tests/test_claim_validation.py tests/test_v2_certification_power.py tests/test_v7_spurious_control_integration.py tests/test_v7_prompt_ablations.py tests/test_v7_mechanism_probes.py tests/test_v3_edit_detectability.py tests/test_parse.py tests/test_v1_1_reporting_outputs.py tests/test_v8_upgrade.py` | 0 | 124 passed in 18.67 s during V11 session. |
| V11 report contract | `python3 -m pytest -q tests/test_v11_full_ceiling_audit.py` | pending | Run after generation. |
| Full suite | `python3 -m pytest -q` | pending | No current pass claim until run. |
| Ruff | `python3 -m ruff check certvic scripts tests` | pending | No current pass claim until run. |
| T4x2 notebooks | `python3 scripts/validate_t4x2_notebooks.py` | pending | No current pass claim until run. |
| Import safety | `python3 -m pytest -q tests/test_v9_spurious_v2_ingest_decision.py` | pending | No current pass claim until rerun. |
| Claim guard | `python3 -m certvic.validation.claim_language_guard --root README.md docs paper reports/v11_full_ceiling_audit --out reports/v11_full_ceiling_audit/claim_guard_v11.md` | pending | No current pass claim until run. |
| Privacy audit | `python3 -m certvic.security.release_privacy_audit --root . --out reports/v11_full_ceiling_audit/privacy_audit_v11.md --json-out reports/v11_full_ceiling_audit/privacy_audit_v11.json` | pending | Scoped result must be paired with a literal-path scan. |
| Evidence ledger | `python3 -m pytest -q tests/test_v11_full_ceiling_audit.py -k evidence` | pending | No current pass claim until run. |
| Package integrity | `python3 -m pytest -q tests/test_v9_spurious_v2_builder.py tests/test_v9_spurious_v2_runbooks.py` | pending | No current pass claim until run. |
| Paper compile | `cd paper && pdflatex -interaction=nonstopmode -halt-on-error main_v11.tex` | 0 | Compiled twice during V11 session. |
| Bibliography | `test ! -f paper/main_v11.bbl` | pending | Paper has no verified bibliography; submission blocker. |
| Anonymization | `test -z "$PRIVATE_IDENTITY_TOKEN" || rg -nF "$PRIVATE_IDENTITY_TOKEN" paper reports/v11_full_ceiling_audit` | pending | Must return no private identity findings when the release owner supplies the token. |
| Release readiness | `python3 -m certvic.v7.spurious_control_integration` | pending | Expected scientific status remains blocked. |

`pending` is a status, not an exit code and not a pass. The final audit owner must replace these
entries with exact results after running the checks in the current tree.
"""
    )
    reports["V11_FINAL_VALIDATION.md"] = (
        report_header(
            "V11 Final Validation",
            "This generated checkpoint states invariants now; command-level finality requires completing the command ledger.",
        )
        + f"""
## Evidence invariants

- Evidence ledger entries: {len(evidence)}; allowed evidence classes only.
- Entries with `paper_evidence=true`: 0.
- Entries with `human_reviewed=true`: 0.
- Real main pilot pairs: 91/provider; real V1 specificity pairs: 94/provider.
- Current V2 provider outputs: 0; current V2 V1-overlap: {state['v2_overlap_v1']}/30.
- Main-500 allowed: false.
- Planned output represented as observed evidence: no.
- Machine-assisted judgment represented as human-reviewed: no in V11 canonical state.

## File-contract invariants

The required report set, JSON/CSV schema, evidence vocabulary, private-path absence, and non-empty
content are enforced by `tests/test_v11_full_ceiling_audit.py`. The command ledger intentionally
keeps unexecuted final checks pending. This document must be refreshed after those commands run;
it must not be cited as proof that a pending check passed.
"""
    )
    reports["CERTVIC_V11_MASTER_HANDOFF.md"] = (
        report_header(
            "CertVIC V11 Master Handoff",
            "This is the authoritative operational entry point for the current repository state.",
        )
        + f"""
## Executive verdict

CertVIC contains real, internally coherent pilot outputs for three open models, but it is not
scientifically certified or submission-ready. Numerical intervention-gap bounds cross the configured
threshold, yet the sample-size/family policy fails, validity screening is machine-assisted, Qwen
fails the frozen V1 specificity gate, current V2 is retrospective and has no outputs, revisions are
unpinned, and Main-500 is blocked. `paper_evidence=false` remains the only defensible setting.

## Verified observations

{markdown_table(['Model', 'n', 'a', 'raw answer-change p', 'gap', 'CS LB', 'full certified'], pilot_rows)}

{markdown_table(['Model', 'V1 flips', 'rate', 'frozen V1 status'], v1_rows)}

The Qwen count is not explained by parse, duplicate, missing-row, provider, or pair-key failures.
All twelve flips are Qwen-only in the three-model V1 matrix. The observation motivates a
model-dependent specificity question; it does not establish why the model differs.

## Current decision state

- Current V2: `DIAGNOSTIC_ONLY_RETROSPECTIVE_STRICTER_CONTROL`; {state['v2_overlap_v1']}/30
  items overlap V1, {state['v2_qwen_retained']}/12 Qwen failures retained, 0/3 outputs present.
- Human review: pending; stale embedded labels are superseded by V11 canonical overrides.
- Main-500: **NO-GO**.
- Second domain: defer until the specificity branch is valid.
- Model matrix: keep three models, but pin immutable revisions before new execution.
- Public image release: blocked pending licensing.
- Grouped detectability diagnostics: main91 symmetric AUC {main_auc}; V1 control94 symmetric
  AUC {v1_auc}; retrospective V2-30 symmetric AUC {v2_auc}. These measure classifier
  separability, not semantic validity.

## Exact next sequence

1. Complete two-rater blinded review of the 91 intervention items and 94 V1 specificity items;
   adjudicate while preserving raw sheets.
2. Build and hash-lock an independent, unseen, prospectively powered specificity set.
3. Pin immutable model/processor revisions and run the three-model matrix under the frozen rule.
4. Import transactionally; report raw and validity-filtered outcomes with missing pairs fail-closed.
5. Sign off the specificity branch. Only then reconsider Main-500 and a small second domain.

Running the existing 30-item V2 package is optional and diagnostic. It must not replace step 2 or
unlock Main-500. Read the evidence, gate, blocker, and claim ledgers before any paper update.
"""
    )
    return reports


def write_comparisons(out: Path, state: dict[str, Any]) -> None:
    fields = [
        "left_provider",
        "right_provider",
        "n",
        "left_flips",
        "right_flips",
        "risk_difference",
        "left_only",
        "right_only",
        "exact_mcnemar_p",
        "bootstrap_seed",
        "bootstrap_repetitions",
        "bootstrap_95_lo",
        "bootstrap_95_hi",
        "analysis_status",
        "paper_evidence",
    ]
    write_csv(out / "V11_PAIRED_COMPARISONS.csv", fields, state["comparisons"])


def write_candidate_inventory(out: Path, state: dict[str, Any]) -> None:
    """Record every locally audited V1 candidate and the retrospective V2 rule result."""
    selected_ids = {str(row["item_id"]) for row in state["v2_tasks"]}
    selected_rows = {str(row["item_id"]): row for row in state["v2_tasks"]}
    fields = [
        "candidate_source",
        "item_id",
        "category",
        "target_class",
        "edit_type",
        "feasibility",
        "duplicate_risk",
        "expected_answer_stability",
        "available_masks_or_boxes",
        "distance_px",
        "target_bbox_overlap",
        "target_mask_overlap_pixels",
        "detectability_score",
        "v11_post_selection_detectability_score",
        "decision",
        "reason",
        "prospective_confirmatory_eligible",
        "evidence_class",
        "paper_evidence",
    ]
    rows: list[dict[str, Any]] = []
    for candidate in state["v2_candidate_audit"]:
        reasons: list[str] = []
        if candidate.get("patch_bbox_intersects_object_bbox") is True:
            reasons.append("patch_bbox_intersects_target_bbox")
        if float(candidate.get("patch_target_mask_overlap_pixels") or 0) > 0:
            reasons.append("target_mask_overlap_positive")
        if float(candidate.get("patch_object_bbox_distance_px") or 0) < 75.0:
            reasons.append("distance_below_75_px")
        score = candidate.get("detectability_score")
        if isinstance(score, (int, float)) and float(score) > 0.12:
            reasons.append("stored_detectability_above_0_12")
        item_id = str(candidate["item_id"])
        selected = item_id in selected_ids
        if selected and reasons:
            raise RuntimeError(f"selected V2 item violates reconstructed rule: {item_id}: {reasons}")
        rows.append(
            {
                "candidate_source": state["paths"]["v2_candidate_audit"],
                "item_id": item_id,
                "category": candidate.get("task_family", "unknown"),
                "target_class": candidate.get("target_object", "unknown"),
                "edit_type": "control_irrelevant",
                "feasibility": "local_original_and_control_images_available",
                "duplicate_risk": "high_reuses_v1_item",
                "expected_answer_stability": "task_declares_no_change_human_review_pending",
                "available_masks_or_boxes": "patch_bbox,target_bbox,target_mask_overlap_count",
                "distance_px": candidate.get("patch_object_bbox_distance_px"),
                "target_bbox_overlap": bool(candidate.get("patch_bbox_intersects_object_bbox")),
                "target_mask_overlap_pixels": candidate.get("patch_target_mask_overlap_pixels"),
                "detectability_score": score if score is not None else "MISSING",
                "v11_post_selection_detectability_score": (
                    (selected_rows.get(item_id, {}).get("metadata") or {}).get(
                        "v11_detectability_score", "NOT_SELECTED"
                    )
                ),
                "decision": "retained_retrospective_diagnostic" if selected else "rejected_by_retrospective_rule",
                "reason": "passes_retrospective_geometry_and_available_salience_fields"
                if selected
                else ";".join(reasons),
                "prospective_confirmatory_eligible": False,
                "evidence_class": "DIAGNOSTIC_ONLY",
                "paper_evidence": False,
            }
        )
    if len(rows) != 94 or sum(row["decision"].startswith("retained") for row in rows) != 30:
        raise RuntimeError("candidate inventory must reconstruct the 94-source/30-retained boundary")
    write_csv(out / "SPURIOUS_V2_LOCAL_CANDIDATE_INVENTORY.csv", fields, rows)


def write_change_manifest(out: Path, report_names: list[str]) -> None:
    fields = ["artifact_path", "change_type", "problem", "change", "validation", "paper_evidence"]
    rows = [
        {
            "artifact_path": "scripts/build_v11_full_ceiling_audit.py",
            "change_type": "created",
            "problem": "No single deterministic authoritative audit builder.",
            "change": "Added local evidence discovery, ledgers, statistics, hashes, and required reports.",
            "validation": "tests/test_v11_full_ceiling_audit.py",
            "paper_evidence": False,
        },
        {
            "artifact_path": "tests/test_v11_full_ceiling_audit.py",
            "change_type": "created",
            "problem": "V11 report and evidence contracts were unenforced.",
            "change": "Added schema, vocabulary, claim-boundary, Main-500, and privacy tests.",
            "validation": "focused pytest",
            "paper_evidence": False,
        },
        {
            "artifact_path": "configs/certvic_v11_protocol.yaml",
            "change_type": "created/updated",
            "problem": "Prospective rules and stale embedded labels were ambiguous.",
            "change": "Locked V1/V2/Main500 decisions and hash-preserving evidence overrides.",
            "validation": "ledger and claim-boundary tests",
            "paper_evidence": False,
        },
        {
            "artifact_path": "paper/main_v11.tex",
            "change_type": "created",
            "problem": "Prior paper scaffold did not reflect current evidence boundaries.",
            "change": "Added evidence-safe pilot draft with explicit blockers and retrospective V2 status.",
            "validation": "pdflatex plus rendered-page visual inspection",
            "paper_evidence": False,
        },
    ]
    repair_changes = [
        (
            "scripts/import_v9_spurious_v2_outputs.py",
            "V2 import could accept under-specified or stale inputs.",
            "Added v3 manifest, exact revision/hash/key checks, transactionality, and conflict refusal.",
            "tests/test_v9_spurious_v2_ingest_decision.py",
        ),
        (
            "scripts/build_spurious_v2_control.py",
            "V2 packages lacked a complete deterministic contract and could truncate canonical outputs after an empty selection.",
            "Added deterministic ZIP metadata, per-image hashes, fail-closed notebook generation, and a frozen-count preflight before writes.",
            "V2 builder and runbook tests",
        ),
        (
            "scripts/build_remaining_kaggle_runbooks.py",
            "Runtime metadata did not pin every input and whole-directory cleanup deleted the independently owned V2 package.",
            "Added exact revision/hash requirements plus owned-file cleanup and explicit aggregate-ZIP membership.",
            "remaining runbook tests",
        ),
        (
            "scripts/build_v8_1_qwen_spurious_forensics.py",
            "Missing external ADE annotations silently degraded frozen geometry and caused downstream canonical corruption.",
            "Validated exact frozen geometry coverage and current image-difference boxes before explicitly labeled derived-cache reuse.",
            "V8.1 forensic and full-suite order-dependency regressions",
        ),
        (
            "scripts/pilot_report_from_raw.py",
            "Wall-clock report timestamps caused deterministic test rebuilds to churn canonical hashes.",
            "Derived the report timestamp from immutable source prediction timestamps and corrected certification prose.",
            "V8 upgrade and full-suite determinism checks",
        ),
        (
            "scripts/build_main200_paper_tables.py",
            "Legacy tables conflated numeric CS threshold crossing with full policy certification.",
            "Separated CS-threshold and full-certification fields and regenerated claim-safe prose.",
            "V7 paper-table tests and claim guard",
        ),
        (
            "certvic/v7/v7_post3model_final_audit.py",
            "Legacy final-audit notes called three pilot runs fully certified and routed the next action toward rerunning outputs.",
            "Recorded partial multi-model evidence and prioritized blinded review plus an independent outcome-unseen control.",
            "V7 final-audit tests",
        ),
        (
            "scripts/validate_t4x2_notebooks.py",
            "Static checks did not cover the complete V11 notebook contract.",
            "Added provider, dual-device, schema, hash, revision, and row-contract checks.",
            "notebook static validation",
        ),
        (
            "certvic/validation/claims.py",
            "Claim status could blur non-evidence blockers.",
            "Made blocked and non-evidence claim states explicit.",
            "claim validation tests",
        ),
        (
            "certvic/metrics/report_metrics.py",
            "Report generation could expose a numerical crossing without all policy gates.",
            "Routed certification through the complete policy.",
            "certification tests",
        ),
        (
            "certvic/v7/spurious_control_integration.py",
            "Missing review state was not uniformly fail-closed.",
            "Blocked integration when independent review is absent.",
            "V7 integration tests",
        ),
        (
            "certvic/eval/presence_semantics.py",
            "Raw answer changes were not separated from correct semantic updates.",
            "Added explicit presence-update semantics.",
            "parser and reporting tests",
        ),
        (
            "scripts/build_prompt_ablation_tasks.py",
            "Alternating source answers corrupted ablation gold polarity.",
            "Normalized source presence before changing answer format.",
            "prompt-ablation tests",
        ),
        (
            "scripts/build_mechanism_probe_tasks.py",
            "Alternating source answers corrupted mechanism-probe gold polarity.",
            "Normalized source presence before constructing probes.",
            "mechanism-probe tests",
        ),
        (
            "certvic/validation/edit_detectability.py",
            "Variant leakage and AUC orientation distorted detectability diagnostics.",
            "Grouped folds by item and reported symmetric separability AUC.",
            "detectability tests",
        ),
        (
            "scripts/build_v11_human_review_packet.py",
            "No outcome-blind portable two-rater review packet existed.",
            "Built four deterministic blinded tracks with separate coordinator keys.",
            "human-review packet tests",
        ),
        (
            "scripts/validate_v11_human_review.py",
            "Blank or malformed reviewer sheets needed a fail-closed validator.",
            "Added completion, provenance, agreement, and adjudication validation.",
            "human-review packet tests",
        ),
        (
            "scripts/rebuild_v11_supported_analysis.py",
            "Supported numerical claims lacked one fail-closed deterministic rebuild command.",
            "Added strict pair validation, semantic updates, V1 gates, paired tests, forensics, and prospective planning tables.",
            "V11 supported-analysis tests",
        ),
        (
            "README.md",
            "Top-level status still described real pilot evidence as future work.",
            "Replaced stale planning language with the verified V11 evidence boundary and exact next gates.",
            "claim-language guard",
        ),
        (
            "certvic/validation/claim_language_guard.py",
            "The CLI reported findings but returned success.",
            "Made forbidden claim findings produce a nonzero exit code.",
            "claim-language CLI regression tests",
        ),
        (
            "docs/methodology/CERTVIC_PROSPECTIVE_ANALYSIS_SPEC_V11.md",
            "Estimands and prospective decisions were spread across historical documents.",
            "Consolidated the V11 analysis and missing-data contract.",
            "claim audit",
        ),
    ]
    rows.extend(
        {
            "artifact_path": path,
            "change_type": "created/updated",
            "problem": problem,
            "change": change,
            "validation": validation,
            "paper_evidence": False,
        }
        for path, problem, change, validation in repair_changes
        if (ROOT / path).exists()
    )
    rows.append(
        {
            "artifact_path": "certvic/, scripts/, tests/ (safe Ruff mechanical sweep)",
            "change_type": "mechanical cleanup",
            "problem": "Repo-wide lint contained unused imports, ambiguous names, and unused assignments.",
            "change": "Applied safe Ruff fixes and narrow manual cleanups without changing raw evidence.",
            "validation": "python3 -m ruff check --no-cache certvic scripts tests plus full pytest",
            "paper_evidence": False,
        }
    )
    rows.extend(
        {
            "artifact_path": path,
            "change_type": "regenerated",
            "problem": "Execution artifact needed to reflect the V11 fail-closed contract.",
            "change": "Regenerated deterministically from current builders.",
            "validation": "notebook/package static checks",
            "paper_evidence": False,
        }
        for path in [
            "notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb",
            "notebooks/kaggle/vlm_internvl_8b_spurious_v2_T4x2.ipynb",
            "notebooks/kaggle/vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb",
            "data/edits/spurious_v2_control/bundle_manifest.json",
            "dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip",
            "reports/v11_full_ceiling_audit/human_review_packet",
            "reports/v11_full_ceiling_audit/certvic_v11_human_review_reviewer_only.zip",
            "output/pdf/certvic_v11_evidence_safe_draft.pdf",
        ]
        if (ROOT / path).exists()
    )
    rows.extend(
        {
            "artifact_path": f"reports/v11_full_ceiling_audit/{name}",
            "change_type": "generated",
            "problem": "Required V11 audit surface absent or stale.",
            "change": "Generated from canonical local artifacts.",
            "validation": "V11 report contract test",
            "paper_evidence": False,
        }
        for name in sorted(
            set(
                REQUIRED_REPORTS
                + report_names
                + [
                    "SPURIOUS_V2_EXECUTION_CARD.md",
                    "SPURIOUS_V2_LOCAL_CANDIDATE_INVENTORY.csv",
                    "V11_PAIRED_COMPARISONS.csv",
                    "notebook_static_validation.json",
                ]
            )
        )
    )
    write_csv(out / "V11_CHANGE_MANIFEST.csv", fields, rows)


def assert_safe_outputs(out: Path) -> None:
    private_prefix = str(ROOT.parent.parent)
    for path in sorted(out.glob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".csv", ".json"}:
            continue
        text = path.read_text(encoding="utf-8")
        if private_prefix in text or "/" + "Users/" in text:
            raise RuntimeError(f"private path leaked into {rel(path)}")
        if not text.strip():
            raise RuntimeError(f"empty output: {rel(path)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    state = load_state(out)
    evidence = build_evidence_ledger(state)
    gates = build_gate_ledger(state)
    blockers = build_blockers(state)
    write_ledgers(out, evidence, gates, blockers)
    write_comparisons(out, state)
    write_candidate_inventory(out, state)
    reports = build_reports(state, evidence, gates, blockers)
    for name, content in sorted(reports.items()):
        write_text(out / name, content)
    write_change_manifest(
        out,
        list(reports) + ["SPURIOUS_V2_LOCAL_CANDIDATE_INVENTORY.csv"],
    )
    missing = [name for name in REQUIRED_REPORTS if not (out / name).is_file()]
    if missing:
        raise RuntimeError(f"missing required reports: {missing}")
    assert_safe_outputs(out)
    print(
        json.dumps(
            {
                "status": "generated",
                "output": rel(out),
                "required_reports": len(REQUIRED_REPORTS),
                "evidence_entries": len(evidence),
                "paper_evidence": False,
                "main500_allowed": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
