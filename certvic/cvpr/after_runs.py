"""Fail-closed discovery, validation, and transactional import of returned CVPR runs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from certvic.cvpr.contracts import (
    load_yaml,
    validate_model_registry,
    validate_study_config,
)
from certvic.cvpr.statistics import specificity_decision
from certvic.cvpr.primary_endpoint import score_item, summarize_items, two_gate_certificate
from certvic.cvpr.transactional import read_jsonl
from certvic.cvpr.analysis import (
    human_aware_analysis,
    outcome_branch,
    write_human_aware_artifacts,
)
from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.paper_branch import activate_paper_branch
from certvic.cvpr.execution_gate import ExecutionAuthorizationError, verify_permission
from certvic.cvpr.schema_contract import require_schema_matrix
from certvic.cvpr.whole_study_import import atomic_import_matrix
from certvic.security.release_privacy_audit import audit as privacy_audit
from certvic.validation.claim_language_guard import scan_claim_language


class ImportBlocked(ValueError):
    pass


def _safe_extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as handle:
        if handle.testzip() is not None:
            raise ImportBlocked(f"corrupt ZIP: {archive.name}")
        for member in handle.infolist():
            pure = PurePosixPath(member.filename)
            if pure.is_absolute() or ".." in pure.parts or member.is_dir():
                if member.is_dir():
                    continue
                raise ImportBlocked(f"unsafe ZIP member: {member.filename}")
            if member.file_size > 2_000_000_000:
                raise ImportBlocked(f"oversized ZIP member: {member.filename}")
        handle.extractall(destination)


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ImportBlocked(f"expected exactly one {name}, found {len(matches)}")
    return matches[0]


def _load_task_ids(path: Path) -> tuple[str, ...]:
    rows = read_jsonl(path)
    ids = tuple(str(row["item_id"]) for row in rows)
    if len(ids) != len(set(ids)):
        raise ImportBlocked("task manifest contains duplicate item IDs")
    return ids


def _analyze_specificity(rows: list[dict[str, Any]], alpha: float) -> dict[str, Any]:
    by_item: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_item.setdefault(str(row["item_id"]), {})[str(row["variant"])] = row
    flips = 0
    parse_failures = 0
    for pair in by_item.values():
        original, edited = pair["original"], pair["edited"]
        if original["parse_status"] != "PARSE_OK" or edited["parse_status"] != "PARSE_OK":
            flips += 1
            parse_failures += 1
        elif original["parsed_response"] != edited["parsed_response"]:
            flips += 1
    return {**specificity_decision(flips, len(by_item), alpha=alpha),
            "missing_or_unparseable_policy": "COUNT_AS_FLIP_PRIMARY",
            "parse_failure_pairs": parse_failures}


def _normalize(value: Any) -> str | None:
    return str(value).strip().lower() if value is not None else None


def _analyze_study(
    rows: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    *,
    alpha: float,
) -> dict[str, Any]:
    by_item: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_item.setdefault(str(row["item_id"]), {})[str(row["variant"])] = row
    task_map = {str(task["item_id"]): task for task in tasks}
    scored: list[dict[str, Any]] = []
    for item_id, pair in by_item.items():
        task = task_map[item_id]
        original, edited = pair["original"], pair["edited"]
        scored.append(score_item(
            original_gold=task["original_expected_answer"],
            edited_gold=task["edited_expected_answer"],
            original_prediction=original.get("parsed_response"),
            edited_prediction=edited.get("parsed_response"),
            required_change=task.get("required_change") is True,
            original_parse_ok=original["parse_status"] == "PARSE_OK",
            edited_parse_ok=edited["parse_status"] == "PARSE_OK",
        ))
    result = summarize_items(scored)
    result["original_correct_rate"] = result["original_accuracy"]
    result["edited_correct_rate"] = result["edited_accuracy"]
    result["spurious_flip_rate"] = result["irrelevant_flip_rate"]
    result["parse_failure_pairs"] = sum(not row["parse_ok"] for row in scored)
    result["missing_or_unparseable_policy"] = (
        "RELEVANT_UPDATE_FAILURE_AND_IRRELEVANT_FLIP_PRIMARY"
    )
    if result["relevant_items"] and result["irrelevant_items"]:
        result["primary_two_gate_certificate"] = two_gate_certificate(
            scored,
            tau_update=0.50,
            tau_spurious=0.10,
            responsiveness_alpha=alpha,
            specificity_alpha=alpha,
        )
    return result


def _write_analysis_outputs(out: Path, providers: dict[str, Any]) -> None:
    analysis_dir = out / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    summary = {provider: payload["analysis"] for provider, payload in sorted(providers.items())}
    (analysis_dir / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fields = ["provider", "items", "original_correct_rate", "edited_correct_rate",
              "raw_answer_change_rate", "correct_semantic_update_rate",
              "conditional_semantic_update_rate_given_original_correct", "spurious_flip_rate",
              "parse_failure_pairs"]
    with (analysis_dir / "primary_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for provider, metrics in summary.items():
            writer.writerow({"provider": provider, **{field: metrics.get(field) for field in fields[1:]}})
    lines = ["\\begin{tabular}{lrrrr}", "\\toprule",
             "Model & Original correct & Edited correct & Raw change & Spurious flip \\\\",
             "\\midrule"]
    for provider, metrics in summary.items():
        values = [metrics.get(key) for key in ("original_correct_rate", "edited_correct_rate",
                                                "raw_answer_change_rate", "spurious_flip_rate")]
        rendered = ["--" if value is None else f"{float(value):.3f}" for value in values]
        lines.append(f"{provider} & " + " & ".join(rendered) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    (analysis_dir / "primary_metrics.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (analysis_dir / "figure_data.json").write_text(
        json.dumps({"status": "VALIDATED_IMPORT_DATA_FOR_FIGURE_RENDERING", "series": summary,
                    "paper_evidence": False}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _upsert_csv(path: Path, key: str, row: dict[str, Any]) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    rows = [value for value in rows if value.get(key) != row[key]]
    rows.append({field: row.get(field, "") for field in fields})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _close_post_run_state(
    root: Path,
    *,
    study: str,
    promotion: dict[str, Any],
    analysis: dict[str, Any],
    final_inclusion: dict[str, Any],
    claim: dict[str, Any],
    privacy: dict[str, Any],
) -> dict[str, Any]:
    requested_branch = str(analysis.get("outcome_branch", {}).get(
        "active_branch", "VALIDATED_STUDY_RESULTS"
    ))
    branch = activate_paper_branch(
        study_import=promotion,
        final_inclusion=final_inclusion,
        evidence_hashes_match=True,
        intervals=analysis["adjudicated_filtered_analysis"],
        claim_guard=claim,
        requested_branch=requested_branch,
    )
    paper_build = {"passed": False, "reason": "paper branch blocked"}
    release_build = {"passed": False, "reason": "paper branch blocked"}
    if branch["status"] == "PAPER_BRANCH_ACTIVATED" and privacy.get("passed") is True:
        paper_commands = [
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
        ]
        completed = [subprocess.run(command, cwd=root / "paper_cvpr", check=False,
                                    capture_output=True, text=True) for command in paper_commands]
        paper_build = {"passed": all(value.returncode == 0 for value in completed),
                       "exit_codes": [value.returncode for value in completed]}
        if paper_build["passed"]:
            release = subprocess.run(
                [sys.executable, "scripts/build_cvpr_final_integration.py", "--rebuild-release-only"],
                cwd=root, check=False, capture_output=True, text=True,
            )
            release_build = {"passed": release.returncode == 0, "exit_code": release.returncode,
                             "stdout": release.stdout[-2000:], "stderr": release.stderr[-2000:]}
    closed = branch["status"] == "PAPER_BRANCH_ACTIVATED" and paper_build["passed"] \
        and release_build["passed"] and privacy.get("passed") is True
    evidence_path = root / "reports/cvpr_pre_execution/CERTVIC_CVPR_EVIDENCE_LEDGER.csv"
    gate_path = root / "reports/cvpr_pre_execution/CERTVIC_CVPR_GATE_LEDGER.csv"
    _upsert_csv(evidence_path, "artifact_id", {
        "artifact_id": f"{study}_validated_import",
        "artifact_path": f"data/results/cvpr_imports/{study}/atomic_matrix",
        "evidence_class": "DERIVED_FROM_REAL_EVIDENCE",
        "paper_evidence": closed,
        "human_reviewed": True,
        "status": "VALIDATED_COMPLETE" if closed else "VALIDATED_GUARDS_PENDING",
    })
    _upsert_csv(gate_path, "gate", {
        "gate": f"{study}_post_run_closure",
        "status": "PASS" if closed else "BLOCKED",
        "reason": "review provenance, import, analysis, paper, and release closed"
        if closed else "one or more post-run closure checks failed",
        "paper_evidence": closed,
    })
    outcome_payload = {
        "schema": "certvic.cvpr.confirmatory_outcome.v1",
        "study": study,
        "status": "CONFIRMATORY_OUTCOME_VALIDATED" if closed and study ==
        "specificity_confirmatory_cvpr" else "CONFIRMATORY_OUTCOME_BLOCKED",
        "main_go_no_go": "GO" if closed and study == "specificity_confirmatory_cvpr" else "NO_GO",
        "active_outcome_branch": requested_branch,
        "atomic_import_sha256": sha256_bytes(canonical_json_bytes(promotion)),
        "review_artifact_sha256": final_inclusion.get("final_artifact_sha256"),
        "paper_branch_status": branch.get("status"),
        "paper_build_passed": paper_build["passed"],
        "release_build_passed": release_build["passed"],
        "paper_evidence": closed,
    }
    outcome_payload["content_signature_sha256"] = sha256_bytes(
        canonical_json_bytes(outcome_payload)
    )
    outcome_path = root / "reports/cvpr_absolute_final/CONFIRMATORY_OUTCOME_AND_MAIN_GO_NO_GO.json"
    outcome_path.parent.mkdir(parents=True, exist_ok=True)
    outcome_path.write_text(json.dumps(outcome_payload, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    return {
        "status": "POST_RUN_CLOSURE_COMPLETE" if closed else "BLOCKED_POST_RUN_CLOSURE",
        "paper_branch": branch, "paper_build": paper_build, "release_build": release_build,
        "confirmatory_outcome": str(outcome_path),
        "main_go_no_go": outcome_payload["main_go_no_go"], "paper_evidence": closed,
    }


def process(
    input_dir: str | Path,
    study: str,
    *,
    project_root: str | Path = ".",
) -> dict[str, Any]:
    root = Path(project_root)
    config_path = root / "configs" / "studies" / f"{study}.yaml"
    if not config_path.is_file():
        raise ImportBlocked(f"unknown study config: {config_path}")
    config = load_yaml(config_path)
    freeze = validate_study_config(config, require_frozen=True)
    registry = load_yaml(root / "configs/models/certvic_cvpr_model_registry.yaml")
    model_check = validate_model_registry(registry, for_execution=True)
    blockers = [*freeze["errors"], *model_check["errors"]]
    if blockers:
        return {"status": "BLOCKED_PRECONDITIONS", "blockers": blockers, "paper_evidence": False}
    task_path = root / str(config["execution"]["task_manifest"])
    if not task_path.is_file():
        return {"status": "BLOCKED_MISSING_TASK_MANIFEST", "blockers": [str(task_path)],
                "paper_evidence": False}
    execution = config["execution"]
    bundle_root = root / str(execution.get("task_bundle_root", ""))
    bundle_manifest = root / str(execution.get("task_bundle_manifest", ""))
    try:
        from certvic.cvpr.task_bundle import verify_bundle
        verified_bundle = verify_bundle(bundle_root, bundle_manifest)
        if Path(verified_bundle["tasks_path"]).resolve() != task_path.resolve():
            raise ValueError("study task manifest differs from verified portable bundle")
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return {"status": "BLOCKED_TASK_BUNDLE", "blockers": [str(exc)],
                "paper_evidence": False}
    permission_path = root / str(execution.get("permission_artifact", ""))
    review_contract = execution.get("human_review_outputs", {})
    permission_inputs = {
        "smoke_gate": root / str(execution.get("smoke_gate", "")),
        "final_tasks": task_path,
        "final_review": root / str(review_contract.get("final_inclusion_manifest", "")),
        "freeze_manifest": root / str(execution.get("freeze_manifest", "")),
        "environment_lock": root / str(execution.get("environment_lock", "")),
        "model_registry": root / "configs/models/certvic_cvpr_model_registry.yaml",
        "study_config": config_path,
        "task_bundle_manifest": bundle_manifest,
        "permission_ledger": root / str(execution.get("permission_ledger", "")),
    }
    if execution.get("detectability_gate"):
        permission_inputs["detectability_gate"] = root / str(execution["detectability_gate"])
    for provider in registry["primary_models"]:
        permission_inputs[f"model_snapshot_manifest:{provider}"] = Path(str(
            registry["models"][provider].get("snapshot_manifest_path", "")
        ))
    code_hash = str(execution.get("code_bundle_sha256", ""))
    try:
        permission = verify_permission(
            permission_path, study=study, input_paths=permission_inputs,
            expected_code_hash=code_hash, expected_provider=str(registry["primary_models"][0]),
            expected_run_tag=str(execution["run_tag"]),
            expected_output_schema="certvic.cvpr.output.v2",
        )
        permission_payload = json.loads(permission_path.read_text(encoding="utf-8"))
    except (ExecutionAuthorizationError, OSError, json.JSONDecodeError) as exc:
        return {"status": "BLOCKED_EXECUTION_PERMISSION", "blockers": [str(exc)],
                "paper_evidence": False}
    archives = sorted(Path(input_dir).glob("*.zip"))
    if not archives:
        return {"status": "BLOCKED_MISSING_RETURNED_ARCHIVES", "blockers": [],
                "paper_evidence": False}
    tasks = read_jsonl(task_path)
    expected = set(registry["primary_models"])
    archive_map: dict[str, Path] = {}
    for archive in archives:
        with tempfile.TemporaryDirectory(prefix="certvic_cvpr_discovery_") as temp:
            unpacked = Path(temp)
            _safe_extract(archive, unpacked)
            manifest = json.loads(_single(unpacked, "runtime_manifest.json").read_text())
        provider = str(manifest.get("provider"))
        if provider not in expected or provider in archive_map:
            raise ImportBlocked(f"unexpected or duplicate provider archive: {provider}")
        archive_map[provider] = archive
    if set(archive_map) != expected:
        return {"status": "BLOCKED_MISSING_PROVIDERS",
                "missing_providers": sorted(expected - set(archive_map)), "paper_evidence": False}
    if len(code_hash) != 64:
        return {"status": "BLOCKED_CODE_BUNDLE_NOT_FROZEN", "paper_evidence": False}
    snapshot_hashes = {provider: str(registry["models"][provider].get(
        "snapshot_manifest_sha256", ""
    )) for provider in expected}
    if any(len(value) != 64 for value in snapshot_hashes.values()):
        return {"status": "BLOCKED_SNAPSHOT_MANIFEST_NOT_FROZEN", "paper_evidence": False}
    destination = root / "data/results/cvpr_imports" / study / "atomic_matrix"
    promotion = atomic_import_matrix(
        archive_map,
        study=study,
        run_tag=str(config["execution"]["run_tag"]),
        model_contracts={provider: registry["models"][provider] for provider in expected},
        tasks=tasks,
        expected_code_bundle_hash=code_hash,
        expected_snapshot_hashes=snapshot_hashes,
        expected_permission_id=permission["permission_id"],
        expected_permission_signature=permission_payload["content_signature_sha256"],
        permission_ledger_path=permission_inputs["permission_ledger"],
        bundle_root=bundle_root,
        destination_root=destination,
    )
    provider_rows = {
        provider: read_jsonl(destination / "canonical" / f"{provider}.jsonl")
        for provider in sorted(expected)
    }
    for rows in provider_rows.values():
        require_schema_matrix(rows)
    review_paths = {name: root / str(value) for name, value in review_contract.items()}
    inclusion_path = review_paths.get("final_inclusion_manifest", root)
    agreement_path = review_paths.get("agreement_report", root)
    missing_review = [path for path in review_paths.values() if not path.is_file()]
    if missing_review:
        return {
            "status": "IMPORTED_PENDING_HUMAN_REVIEW",
            "promotion": promotion, "providers": sorted(expected),
            "blockers": [str(path) for path in missing_review],
            "analysis_written": False, "paper_evidence": False,
        }
    final_inclusion = json.loads(inclusion_path.read_text(encoding="utf-8"))
    agreement = json.loads(agreement_path.read_text(encoding="utf-8"))
    provenance = final_inclusion.get("provenance", {})
    if final_inclusion.get("schema") != "certvic.cvpr.final_review_state.v2":
        raise ImportBlocked("final inclusion is not the strict provenance-bound review state")
    expected_review_hashes = {
        "rater_1_qualification": provenance.get("qualification_artifact_hashes", {}).get("rater_1"),
        "rater_2_qualification": provenance.get("qualification_artifact_hashes", {}).get("rater_2"),
        "rater_1_validation": provenance.get("validation_artifact_hashes", {}).get("rater_1"),
        "rater_2_validation": provenance.get("validation_artifact_hashes", {}).get("rater_2"),
        "adjudication_artifact": provenance.get("adjudication_artifact_hash"),
        "agreement_report": provenance.get("agreement_artifact_hash"),
    }
    for name, expected_hash in expected_review_hashes.items():
        path = review_paths.get(name)
        if path is None or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ImportBlocked(f"review provenance hash mismatch: {name}")
    analysis = human_aware_analysis(
        provider_rows, tasks, final_inclusion=final_inclusion, agreement=agreement,
        study_kind=study,
    )
    if study == "specificity_confirmatory_cvpr":
        invalidation_rate = len(analysis["excluded_item_ids"]) / len(tasks)
        branch = outcome_branch(
            analysis["adjudicated_filtered_analysis"], human_invalidation_rate=invalidation_rate
        )
        analysis["outcome_branch"] = branch
    write_human_aware_artifacts(destination / "analysis", analysis)
    claim = scan_claim_language(["README.md", "docs", "paper", "paper_cvpr",
                                 "reports/cvpr_pre_execution"])
    privacy = privacy_audit(str(root))
    closure = _close_post_run_state(
        root, study=study, promotion=promotion, analysis=analysis,
        final_inclusion=final_inclusion, claim=claim, privacy=privacy,
    )
    return {"status": closure["status"], "missing_providers": [], "promotion": promotion,
            "providers": sorted(expected), "analysis": analysis,
            "claim_guard_passed": claim["passed"], "privacy_guard_passed": privacy["passed"],
            "post_run_closure": closure, "paper_evidence": closure["paper_evidence"],
            "human_review_required": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and import returned CertVIC CVPR runs")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--study", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--status-out", default="reports/cvpr_pre_execution/after_runs_status.json")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = process(args.input_dir, args.study, project_root=args.project_root)
    except (ImportBlocked, ValueError, KeyError, json.JSONDecodeError) as exc:
        result = {"status": "BLOCKED_INVALID_RETURN", "blockers": [str(exc)],
                  "paper_evidence": False}
    out = Path(args.project_root) / args.status_out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "status_out": str(out)}, sort_keys=True))
    return 0 if result["status"] == "POST_RUN_CLOSURE_COMPLETE" else (2 if args.strict else 0)


if __name__ == "__main__":
    raise SystemExit(main())
