"""Detectability-first go/no-go gate for the tiny pilot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from certvic.io import read_json

GO_MAX_AUC = 0.60
CONDITIONAL_MAX_AUC = 0.70
ARTIFACT_CONFOUNDED_AUC = 0.80


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if path.exists() and path.is_file():
        try:
            data = read_json(path)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None
    return None


def load_detectability_summary(path: str | Path) -> dict[str, Any] | None:
    raw = Path(path)
    if raw.is_dir():
        for name in (
            "detectability_summary.json",
            "summary.json",
            "edit_detectability_summary.json",
            "detectability.json",
            "result.json",
        ):
            data = _load_json_if_exists(raw / name)
            if data is not None:
                return data
        return None
    return _load_json_if_exists(raw)


def _extract_auc(summary: dict[str, Any] | None) -> float | None:
    if not summary:
        return None
    for key in ("auc", "detectability_auc", "edit_detectability_auc"):
        if summary.get(key) is not None:
            return float(summary[key])
    classifier = summary.get("classifier")
    if isinstance(classifier, dict) and classifier.get("auc") is not None:
        return float(classifier["auc"])
    return None


def _extract_n(summary: dict[str, Any] | None) -> int | None:
    if not summary:
        return None
    for key in ("n", "n_items", "n_pairs", "review_count"):
        if summary.get(key) is not None:
            return int(summary[key])
    return None


def load_quality_summary(path: str | Path) -> dict[str, Any] | None:
    raw = Path(path)
    if raw.is_dir():
        for name in ("quality_report.json", "summary.json", "quality_summary.json"):
            data = _load_json_if_exists(raw / name)
            if data is not None:
                return data
        return None
    return _load_json_if_exists(raw)


def quality_passes(summary: dict[str, Any] | None) -> bool:
    if not summary:
        return False
    for key in ("passed", "quality_passed", "all_passed"):
        if key in summary:
            return bool(summary[key])
    for key in ("quality_gate_status", "overall_status", "status"):
        if str(summary.get(key, "")).strip().lower() in {"pass", "passed", "ok", "go"}:
            return True
        if str(summary.get(key, "")).strip().lower() in {"fail", "failed", "no_go", "no-go"}:
            return False
    if summary.get("n_failed") is not None:
        return int(summary.get("n_failed") or 0) == 0
    if summary.get("quality_failed") is not None:
        return int(summary.get("quality_failed") or 0) == 0 and int(summary.get("quality_passed") or 0) > 0
    return False


def evaluate_gate(
    detectability_summary: dict[str, Any] | None,
    quality_summary: dict[str, Any] | None = None,
    *,
    min_n: int = 20,
) -> dict[str, Any]:
    auc = _extract_auc(detectability_summary)
    n_items = _extract_n(detectability_summary)
    quality_ok = quality_passes(quality_summary)
    blockers: list[str] = []
    warnings: list[str] = []

    if auc is None:
        blockers.append("missing_detectability_auc")
        status = "NO_GO"
    elif auc > CONDITIONAL_MAX_AUC:
        blockers.append("edit_detectability_too_high")
        status = "NO_GO"
    elif auc > GO_MAX_AUC:
        warnings.append("edit_detectability_borderline")
        status = "CONDITIONAL"
    else:
        status = "GO"

    if auc is not None and auc >= ARTIFACT_CONFOUNDED_AUC:
        blockers.append("artifact_confounded_auc_ge_0_80")
    if n_items is None:
        warnings.append("missing_detectability_n")
        if status == "GO":
            status = "CONDITIONAL"
    elif n_items < min_n:
        warnings.append("insufficient_detectability_n")
        if status == "GO":
            status = "CONDITIONAL"
    if not quality_ok:
        blockers.append("quality_gate_not_passed")
        status = "NO_GO"

    return {
        "gate": "tiny_pilot_detectability_first",
        "status": status,
        "may_begin_vlm_inference": status == "GO",
        "detectability_auc": auc,
        "n_detectability_items": n_items,
        "quality_passed": quality_ok,
        "artifact_confounded": bool(auc is not None and auc >= ARTIFACT_CONFOUNDED_AUC),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "evidence_status": "GATE_ONLY_NON_EVIDENCE",
        "guidance": "VLM inference should not begin until detectability and visual quality pass.",
    }


def render_gate_report(result: dict[str, Any]) -> str:
    lines = [
        "# Tiny Pilot Go/No-Go Gate",
        "",
        f"Status: {result['status']}",
        f"May begin VLM inference: {result['may_begin_vlm_inference']}",
        f"Detectability AUC: {result['detectability_auc'] if result['detectability_auc'] is not None else 'missing'}",
        f"Quality passed: {result['quality_passed']}",
        "",
        result["guidance"],
        "",
    ]
    if result["blockers"]:
        lines += ["## Blockers", ""]
        lines.extend(f"- {blocker}" for blocker in result["blockers"])
        lines.append("")
    if result["warnings"]:
        lines += ["## Warnings", ""]
        lines.extend(f"- {warning}" for warning in result["warnings"])
        lines.append("")
    return "\n".join(lines)
