"""Guarded paper injection from hash-verified canonical registry artifacts only."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from certvic.cvpr.artifact_registry import load_registry, verify_registry
from certvic.cvpr.ceiling_common import atomic_json, repository_root, sha256_file


ELIGIBLE_CLASSES = {"REAL_OBSERVED_EVIDENCE", "DERIVED_FROM_REAL_EVIDENCE"}
FORBIDDEN_CLASSES = {
    "PLANNED_NOT_EXECUTED",
    "SYNTHETIC_TEST_FIXTURE",
    "DIAGNOSTIC_ONLY",
    "RETROSPECTIVE_SENSITIVITY_ONLY",
    "MACHINE_ASSISTED_PRELIMINARY",
    "HUMAN_REVIEW_PENDING",
}


class PaperEvidenceError(ValueError):
    """Evidence cannot be promoted into the paper branch."""


def _latex(value: object) -> str:
    text = str(value)
    for source, target in (
        ("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
        ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
    ):
        text = text.replace(source, target)
    return text


def compile_evidence(
    registry_path: str | Path,
    out_dir: str | Path,
    *,
    root: str | Path,
) -> dict[str, Any]:
    base = Path(root).resolve()
    verification = verify_registry(registry_path, root=base)
    registry = load_registry(registry_path)
    blockers: list[str] = []
    if not verification["passed"]:
        blockers.append("artifact registry verification failed")
    analyses = [row for row in registry["artifacts"] if row.get("role") == "analysis"]
    reviews = [row for row in registry["artifacts"] if row.get("role") == "human_review"]
    if not analyses:
        blockers.append("canonical analysis artifact is absent")
    if any(row.get("study") == "specificity_confirmatory_cvpr" for row in analyses):
        from certvic.cvpr.protocol_authority import validate_authority

        authority = validate_authority(base)
        if not authority["passed"]:
            blockers.append("prospective protocol authority or primary-analysis lock is invalid")
    if not reviews or any(row.get("evidence_class") not in ELIGIBLE_CLASSES for row in reviews):
        blockers.append("genuine final human-review artifact is absent")
    ineligible = [
        row["artifact_id"] for row in analyses if row.get("evidence_class") in FORBIDDEN_CLASSES
    ]
    if ineligible:
        blockers.append(f"analysis has forbidden evidence classes: {ineligible}")
    eligible = [row for row in analyses if row.get("evidence_class") in ELIGIBLE_CLASSES]
    if analyses and len(eligible) != len(analyses):
        blockers.append("not every analysis artifact is eligible for paper promotion")
    loaded: list[tuple[dict[str, Any], dict[str, Any]]] = []
    if not blockers:
        for row in eligible:
            path = base / row["immutable_location"]
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or value.get("paper_evidence") is not True:
                blockers.append(f"{row['artifact_id']}: artifact does not explicitly permit paper evidence")
                continue
            if value.get("synthetic") is True or value.get("status") in {
                "PLANNED", "SYNTHETIC", "DIAGNOSTIC_ONLY"
            }:
                blockers.append(f"{row['artifact_id']}: planned/synthetic/diagnostic artifact refused")
                continue
            if row.get("study") == "specificity_confirmatory_cvpr" and not (
                value.get("primary_two_gate_certificate")
                or value.get("providers")
            ):
                blockers.append(
                    f"{row['artifact_id']}: corrected two-gate confirmatory analysis is absent"
                )
                continue
            loaded.append((row, value))
    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)
    table_path = destination / "canonical_evidence_table.tex"
    if loaded and not blockers:
        lines = [r"\begin{tabular}{lll}", r"Artifact & Study & SHA-256 \\", r"\hline"]
        for row, _ in loaded:
            lines.append(
                f"{_latex(row['artifact_id'])} & {_latex(row['study'])} & "
                f"{_latex(row['sha256'][:12])} \\\\"
            )
        lines.append(r"\end{tabular}")
        table_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        table_path.unlink(missing_ok=True)
    manifest = {
        "schema": "certvic.cvpr.paper_injection_manifest.v1",
        "status": "PAPER_EVIDENCE_READY" if not blockers else "PAPER_EVIDENCE_BLOCKED",
        "registry_verification": verification,
        "input_artifacts": [
            {
                "artifact_id": row["artifact_id"],
                "sha256": row["sha256"],
                "evidence_class": row["evidence_class"],
            }
            for row, _ in loaded
        ],
        "generated_table": str(table_path.relative_to(base)) if table_path.is_file() else None,
        "generated_table_sha256": sha256_file(table_path) if table_path.is_file() else None,
        "blockers": blockers,
        "paper_evidence": not blockers,
    }
    atomic_json(destination / "paper_injection_manifest.json", manifest)
    return manifest


def compile_paper(root: str | Path, manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("status") != "PAPER_EVIDENCE_READY":
        raise PaperEvidenceError("paper compile refused because the injection manifest is blocked")
    base = Path(root).resolve()
    paper = base / "paper_cvpr"
    commands = [
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
    ]
    results = [subprocess.run(command, cwd=paper, check=False, capture_output=True, text=True) for command in commands]
    passed = all(result.returncode == 0 for result in results) and (paper / "main.pdf").is_file()
    return {
        "passed": passed,
        "exit_codes": [result.returncode for result in results],
        "pdf_sha256": sha256_file(paper / "main.pdf") if passed else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile guarded CertVIC paper evidence")
    parser.add_argument("--root")
    parser.add_argument(
        "--registry", default="reports/max_ceiling_upgrade/artifact_registry.json"
    )
    parser.add_argument("--out-dir", default="reports/max_ceiling_upgrade/paper_evidence")
    parser.add_argument("--compile-paper", action="store_true")
    args = parser.parse_args(argv)
    base = repository_root(args.root)
    registry = Path(args.registry)
    if not registry.is_absolute():
        registry = base / registry
    out = Path(args.out_dir)
    if not out.is_absolute():
        out = base / out
    result = compile_evidence(registry, out, root=base)
    if args.compile_paper and result["status"] == "PAPER_EVIDENCE_READY":
        result["paper_compile"] = compile_paper(base, result)
        result["paper_pdf_sha256"] = result["paper_compile"]["pdf_sha256"]
        atomic_json(out / "paper_injection_manifest.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PAPER_EVIDENCE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
