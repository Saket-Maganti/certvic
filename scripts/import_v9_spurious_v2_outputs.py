from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from certvic.eval.parse import parse_answer  # noqa: E402
from certvic.schema import PredictionRecord  # noqa: E402


V9 = ROOT / "data/results/main_real_200/v9_mega_upgrade"
CANONICAL = ROOT / "data/results/main_real_200/kaggle_spurious_v2"
TASKS = ROOT / "data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl"
CODE_BUNDLE = ROOT / "dist/certvic_kaggle_main200_bundle.zip"
CONTROL_BUNDLE = ROOT / "dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip"
PROVIDERS = ["qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"]
PROVIDER_MODEL_REPOS = {
    "qwen2_5_vl_7b": "Qwen/Qwen2.5-VL-7B-Instruct",
    "internvl_8b": "OpenGVLab/InternVL2-8B",
    "llava_onevision_7b": "llava-hf/llava-onevision-qwen2-7b-ov-hf",
}
RUN_TAG = "spurious_v2"
THRESHOLD = 0.10
VARIANTS = {"original", "edited"}
OUTPUT_MANIFEST_SCHEMA = "certvic.v11.spurious_v2.kaggle_output_manifest.v3"


class ImportValidationError(ValueError):
    """A fail-closed validation error for returned provider artifacts."""


@dataclass(frozen=True)
class Candidate:
    provider: str
    source: Path
    source_kind: str
    prediction_bytes: bytes
    manifest: dict

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.prediction_bytes).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return f"<EXTERNAL_INPUT>/{path.name}"


def _atomic_write(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = data.encode("utf-8") if isinstance(data, str) else data
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _read_jsonl_bytes(data: bytes, *, source: str) -> list[dict]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ImportValidationError(f"{source}: predictions are not UTF-8") from exc
    rows: list[dict] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ImportValidationError(f"{source}:{line_no}: malformed JSON: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise ImportValidationError(f"{source}:{line_no}: every JSONL row must be an object")
        rows.append(row)
    if not rows:
        raise ImportValidationError(f"{source}: prediction file is empty")
    return rows


def _read_json(path: Path, *, source: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ImportValidationError(f"{source}: invalid JSON manifest: {exc}") from exc
    if not isinstance(payload, dict):
        raise ImportValidationError(f"{source}: manifest must be a JSON object")
    return payload


def _candidate_dirs(input_dir: Path | None) -> list[Path]:
    # An explicit input is authoritative. Falling through to Downloads or old
    # canonical files after an explicit artifact is absent/invalid can silently
    # import stale evidence.
    if input_dir is not None:
        return [input_dir] if input_dir.exists() else []
    return [
        path
        for path in (
            ROOT / "kaggleoutputs/v9_spurious_v2",
            ROOT / "kaggleoutputs/spurious_v2",
            ROOT / "kaggleoutputs/newruns",
            Path.home() / "Downloads",
            CANONICAL,
        )
        if path.exists()
    ]


def _manifest_name(provider: str) -> str:
    return f"runtime_manifest_{provider}_{RUN_TAG}.json"


def _prediction_name(provider: str) -> str:
    return f"pred_{provider}_{RUN_TAG}_merged.jsonl"


def _candidate_from_zip(provider: str, path: Path) -> Candidate:
    wanted = _prediction_name(provider)
    manifest_name = _manifest_name(provider)
    try:
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            if bad is not None:
                raise ImportValidationError(f"{path.name}: corrupt ZIP member {bad}")
            pred_members = [info for info in zf.infolist() if Path(info.filename).name == wanted]
            manifest_members = [info for info in zf.infolist() if Path(info.filename).name == manifest_name]
            if len(pred_members) != 1:
                raise ImportValidationError(
                    f"{path.name}: expected exactly one {wanted}, found {len(pred_members)}"
                )
            if len(manifest_members) != 1:
                raise ImportValidationError(
                    f"{path.name}: expected exactly one {manifest_name}, found {len(manifest_members)}"
                )
            prediction_bytes = zf.read(pred_members[0])
            try:
                manifest = json.loads(zf.read(manifest_members[0]).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ImportValidationError(f"{path.name}: invalid runtime manifest: {exc}") from exc
    except zipfile.BadZipFile as exc:
        raise ImportValidationError(f"{path.name}: invalid ZIP archive") from exc
    if not isinstance(manifest, dict):
        raise ImportValidationError(f"{path.name}: runtime manifest must be a JSON object")
    return Candidate(provider, path, "zip", prediction_bytes, manifest)


def _candidate_from_direct(provider: str, path: Path) -> Candidate:
    manifest_path = path.parent / _manifest_name(provider)
    if not manifest_path.exists():
        raise ImportValidationError(
            f"{path.name}: missing required source-hash manifest {manifest_path.name}"
        )
    return Candidate(
        provider,
        path,
        "direct_jsonl",
        path.read_bytes(),
        _read_json(manifest_path, source=manifest_path.name),
    )


def _find_prediction(provider: str, dirs: list[Path]) -> Candidate | None:
    wanted = _prediction_name(provider)
    zip_name = f"{provider}_{RUN_TAG}_preds.zip"
    for directory in dirs:
        direct = directory / wanted
        zipped = directory / zip_name
        if direct.exists() and zipped.exists():
            raise ImportValidationError(
                f"{provider}: ambiguous sources in {_display_path(directory)}; keep either {wanted} "
                f"or {zip_name}, not both"
            )
        if zipped.exists():
            return _candidate_from_zip(provider, zipped)
        if direct.exists():
            return _candidate_from_direct(provider, direct)
    return None


def _validate_manifest(candidate: Candidate, *, expected_items: int, task_sha256: str) -> None:
    manifest = candidate.manifest
    expected_rows = expected_items * len(VARIANTS)
    expected_name = _prediction_name(candidate.provider)
    if not CODE_BUNDLE.is_file() or not CONTROL_BUNDLE.is_file():
        raise ImportValidationError(
            "local V11 code/control bundle locks are missing; rebuild both deterministic bundles before import"
        )
    checks = {
        "schema": OUTPUT_MANIFEST_SCHEMA,
        "provider": candidate.provider,
        "run_tag": RUN_TAG,
        "expected_items": expected_items,
        "expected_prediction_rows": expected_rows,
        "task_file_sha256": task_sha256,
        "merged_predictions_sha256": candidate.sha256,
        "model_repo_id": PROVIDER_MODEL_REPOS[candidate.provider],
        "model_revision_marker_verified": True,
        "code_bundle_sha256": _sha256(CODE_BUNDLE),
        "control_bundle_sha256": _sha256(CONTROL_BUNDLE),
    }
    errors = [
        f"manifest {key}={manifest.get(key)!r}, expected {value!r}"
        for key, value in checks.items()
        if manifest.get(key) != value
    ]
    if Path(str(manifest.get("merged_predictions", ""))).name != expected_name:
        errors.append(
            f"manifest merged_predictions={manifest.get('merged_predictions')!r}, expected basename {expected_name!r}"
        )
    if manifest.get("paper_evidence") is not False:
        errors.append("manifest paper_evidence must be false")
    if manifest.get("canonical_results_changed") is not False:
        errors.append("manifest canonical_results_changed must be false before local import")
    model_revision = manifest.get("model_revision")
    if not isinstance(model_revision, str) or not re.fullmatch(r"[0-9a-f]{40}", model_revision):
        errors.append("manifest model_revision must be an exact 40-character lowercase commit SHA")
    if errors:
        raise ImportValidationError(f"{candidate.provider}: " + "; ".join(errors))


def _expected_run_ids(provider: str) -> set[str]:
    return {f"v9_{provider}_{RUN_TAG}_shard0", f"v9_{provider}_{RUN_TAG}_shard1"}


def _validate_and_score(
    candidate: Candidate,
    *,
    expected_items: set[str],
    task_sha256: str,
) -> dict:
    provider = candidate.provider
    _validate_manifest(candidate, expected_items=len(expected_items), task_sha256=task_sha256)
    rows = _read_jsonl_bytes(candidate.prediction_bytes, source=candidate.source.name)
    expected_keys = {(item_id, variant) for item_id in expected_items for variant in VARIANTS}
    expected_rows = len(expected_keys)
    if len(rows) != expected_rows:
        raise ImportValidationError(
            f"{provider}: unexpected denominator: expected {expected_rows} prediction rows, found {len(rows)}"
        )

    by_key: dict[tuple[str, str], dict] = {}
    errors: list[str] = []
    allowed_run_ids = _expected_run_ids(provider)
    expected_model_revision = candidate.manifest.get("model_revision")
    run_id_re = re.compile(rf"^v9_{re.escape(provider)}_{RUN_TAG}_shard[01]$")
    for index, raw_row in enumerate(rows, 1):
        try:
            row = PredictionRecord.model_validate(raw_row).model_dump(mode="json")
        except Exception as exc:
            errors.append(f"row {index}: prediction schema invalid: {exc}")
            continue
        item_id = str(row["item_id"])
        variant = str(row["image_variant"])
        key = (item_id, variant)
        if item_id not in expected_items:
            errors.append(f"row {index}: unexpected item_id {item_id!r}")
        if variant not in VARIANTS:
            errors.append(f"row {index}: invalid image_variant {variant!r}")
        if key in by_key:
            errors.append(f"row {index}: duplicate item/variant key {key!r}")
        else:
            by_key[key] = row
        if row["provider_name"] != provider:
            errors.append(
                f"row {index}: provider_name {row['provider_name']!r} does not match {provider!r}"
            )
        if row["provider_type"] != "open_local":
            errors.append(f"row {index}: provider_type must be 'open_local'")
        if row["model_version"] != expected_model_revision:
            errors.append(
                f"row {index}: model_version {row['model_version']!r} does not match "
                f"runtime manifest revision {expected_model_revision!r}"
            )
        run_id = str(row["run_id"])
        if run_id not in allowed_run_ids or not run_id_re.fullmatch(run_id):
            errors.append(f"row {index}: wrong run_id/run_tag {run_id!r}")
        if row["parse_ok"] is not True:
            errors.append(f"row {index}: parse_ok is not true; certification-critical import is blocked")
        if row["parsed_answer"] not in {"yes", "no"}:
            errors.append(f"row {index}: parsed_answer must be exactly 'yes' or 'no'")
        reparsed = parse_answer(str(row["raw_output"]), "yes_no", strict=True)
        if not reparsed.parse_ok or reparsed.parsed_answer != row["parsed_answer"]:
            errors.append(
                f"row {index}: raw_output does not reproduce stored strict parsed_answer"
            )

    missing = sorted(expected_keys - set(by_key))
    extra = sorted(set(by_key) - expected_keys)
    if missing:
        errors.append(f"missing item/variant keys: {missing[:5]!r} (n={len(missing)})")
    if extra:
        errors.append(f"unexpected item/variant keys: {extra[:5]!r} (n={len(extra)})")
    if errors:
        raise ImportValidationError(f"{provider}: " + "; ".join(errors[:20]))

    scored_rows = []
    for item_id in sorted(expected_items):
        original = by_key[(item_id, "original")]
        edited = by_key[(item_id, "edited")]
        flipped = original["parsed_answer"] != edited["parsed_answer"]
        scored_rows.append(
            {
                "provider": provider,
                "item_id": item_id,
                "original_answer": original["parsed_answer"],
                "edited_answer": edited["parsed_answer"],
                "parse_ok": True,
                "flipped": flipped,
            }
        )
    flips = sum(int(row["flipped"]) for row in scored_rows)
    n = len(scored_rows)
    rate = flips / n
    return {
        "provider": provider,
        "source": _display_path(candidate.source),
        "source_kind": candidate.source_kind,
        "source_sha256": candidate.sha256,
        "task_file_sha256": task_sha256,
        "model_repo_id": candidate.manifest.get("model_repo_id"),
        "model_revision": candidate.manifest.get("model_revision"),
        "code_bundle_sha256": candidate.manifest.get("code_bundle_sha256"),
        "control_bundle_sha256": candidate.manifest.get("control_bundle_sha256"),
        "n_items": n,
        "n_prediction_rows": len(rows),
        "missing_items": [],
        "duplicate_item_variant_keys": 0,
        "parse_failures": 0,
        "flipped": flips,
        "spurious_flip_rate": rate,
        "gate_threshold": THRESHOLD,
        "gate_pass": rate <= THRESHOLD,
        "scored_rows": scored_rows,
    }


def _write_blocked(
    *,
    report_dir: Path,
    status: str,
    missing: list[str] | None = None,
    errors: list[str] | None = None,
    searched_dirs: list[Path] | None = None,
) -> None:
    report = {
        "schema": "certvic.v11.spurious_v2_import_status.v1",
        "status": status,
        "missing_providers": missing or [],
        "validation_errors": errors or [],
        "searched_dirs": [_display_path(path) for path in (searched_dirs or [])],
        "paper_evidence": False,
        "canonical_results_changed": False,
        "next_action": (
            "Supply all three hash-manifested Spurious V2 provider archives."
            if status == "BLOCKED_MISSING_PREDICTIONS"
            else "Correct or re-export the rejected provider artifact; do not use canonical outputs."
        ),
    }
    _atomic_write(
        report_dir / "spurious_v2_ingest_status.json",
        json.dumps(report, indent=2, sort_keys=True) + "\n",
    )
    heading = (
        "Spurious V2 Blocked: Missing Predictions"
        if status == "BLOCKED_MISSING_PREDICTIONS"
        else "Spurious V2 Blocked: Invalid Predictions"
    )
    body = [
        f"# {heading}",
        "",
        f"Status: `{status}`. No canonical prediction files or paper evidence were created.",
        "",
    ]
    if missing:
        body += ["## Missing Providers", "", *[f"- `{provider}`" for provider in missing], ""]
    if errors:
        body += ["## Validation Errors", "", *[f"- {error}" for error in errors], ""]
    _atomic_write(
        report_dir
        / (
            "SPURIOUS_V2_BLOCKED_MISSING_PREDICTIONS.md"
            if status == "BLOCKED_MISSING_PREDICTIONS"
            else "SPURIOUS_V2_BLOCKED_INVALID_PREDICTIONS.md"
        ),
        "\n".join(body) + "\n",
    )


def _commit_canonical(
    candidates: dict[str, Candidate], canonical_dir: Path
) -> tuple[dict[str, str], bool]:
    # Check every destination before creating or replacing anything. Existing
    # identical bytes are idempotent; any differing canonical file is a hard
    # conflict that requires explicit human resolution outside this importer.
    actions: dict[str, str] = {}
    for provider, candidate in candidates.items():
        dst = canonical_dir / _prediction_name(provider)
        if dst.exists():
            if hashlib.sha256(dst.read_bytes()).hexdigest() == candidate.sha256:
                actions[provider] = "idempotent_existing_identical"
            else:
                raise ImportValidationError(
                    f"{provider}: canonical conflict at {_display_path(dst)}; existing hash "
                    f"{_sha256(dst)} differs from incoming {candidate.sha256}"
                )
        else:
            actions[provider] = "created"

    changed = any(action == "created" for action in actions.values())
    if changed:
        canonical_dir.mkdir(parents=True, exist_ok=True)
        for provider, candidate in candidates.items():
            if actions[provider] == "created":
                _atomic_write(canonical_dir / _prediction_name(provider), candidate.prediction_bytes)
    return actions, changed


def _write_success_reports(
    *,
    results: list[dict],
    actions: dict[str, str],
    canonical_changed: bool,
    report_dir: Path,
    out_dir: Path,
) -> dict:
    report_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = report_dir / "spurious_v2_specificity_results.csv"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", delete=False, dir=csv_path.parent, prefix=f".{csv_path.name}."
    ) as handle:
        temp_csv = Path(handle.name)
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "provider",
                "n_items",
                "n_prediction_rows",
                "missing_items",
                "duplicate_item_variant_keys",
                "parse_failures",
                "flipped",
                "spurious_flip_rate",
                "gate_threshold",
                "gate_pass",
                "source_sha256",
                "canonical_action",
            ],
        )
        writer.writeheader()
        for row in results:
            payload = {key: row.get(key) for key in writer.fieldnames}
            payload["canonical_action"] = actions[row["provider"]]
            writer.writerow(payload)
    os.replace(temp_csv, csv_path)

    providers = {}
    for row in results:
        providers[row["provider"]] = {
            **{key: value for key, value in row.items() if key != "scored_rows"},
            "canonical_action": actions[row["provider"]],
        }
        scored = "".join(json.dumps(item, sort_keys=True) + "\n" for item in row["scored_rows"])
        _atomic_write(out_dir / f"scored_{row['provider']}_{RUN_TAG}.jsonl", scored)

    qwen = providers["qwen2_5_vl_7b"]
    all_pass = all(row["gate_pass"] for row in providers.values())
    if qwen["gate_pass"] and all_pass:
        decision_label = "V2_SPECIFICITY_PASSES_PENDING_QUALITY_AND_CLAIM_REVIEW"
    elif not qwen["gate_pass"]:
        decision_label = "QWEN_SPECIFICITY_FAILURE_REMAINS_MODEL_DEPENDENT"
    else:
        decision_label = "MIXED_PROVIDER_SPECIFICITY_REQUIRES_REFRAME"
    decision = {
        "schema": "certvic.v11.spurious_v2_specificity_results.v1",
        "status": "DONE_REAL_IMPORTED_OUTPUTS",
        "evidence_class": "REAL_OBSERVED_EVIDENCE",
        "threshold": THRESHOLD,
        "paper_evidence": False,
        "canonical_results_changed": canonical_changed,
        "decision": decision_label,
        "providers": providers,
    }
    _atomic_write(
        report_dir / "spurious_v2_specificity_results.json",
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
    )
    _atomic_write(
        report_dir / "spurious_v2_ingest_status.json",
        json.dumps(
            {
                "schema": "certvic.v11.spurious_v2_import_status.v1",
                "status": "DONE_REAL_IMPORTED_OUTPUTS",
                "paper_evidence": False,
                "canonical_results_changed": canonical_changed,
                "canonical_actions": actions,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    _atomic_write(
        report_dir / "SPURIOUS_V2_DECISION_REPORT.md",
        "# Spurious V2 Decision Report\n\n"
        f"- Status: `{decision['status']}`\n"
        f"- Decision: `{decision['decision']}`\n"
        f"- Threshold: `{THRESHOLD}`\n"
        "- Paper evidence: `false`\n"
        f"- Canonical results changed: `{str(canonical_changed).lower()}`\n\n"
        "## Provider Results\n\n"
        + "".join(
            f"- `{provider}`: flipped `{info['flipped']}/{info['n_items']}`, rate "
            f"`{info['spurious_flip_rate']}`, pass `{info['gate_pass']}`, canonical "
            f"`{info['canonical_action']}`\n"
            for provider, info in providers.items()
        ),
    )
    return decision


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import and gate V9 Spurious V2 Kaggle outputs.")
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--out-dir", type=Path, default=V9 / "spurious_v2_ingest")
    parser.add_argument("--canonical-dir", type=Path, default=CANONICAL)
    parser.add_argument("--report-dir", type=Path, default=V9)
    args = parser.parse_args(argv)

    dirs = _candidate_dirs(args.input_dir)
    if args.input_dir is not None and not dirs:
        args.report_dir.mkdir(parents=True, exist_ok=True)
        _write_blocked(
            report_dir=args.report_dir,
            status="BLOCKED_MISSING_PREDICTIONS",
            missing=list(PROVIDERS),
            searched_dirs=[args.input_dir],
        )
        print(json.dumps({"status": "BLOCKED_MISSING_PREDICTIONS", "missing": PROVIDERS}, sort_keys=True))
        return 2

    try:
        found = {provider: _find_prediction(provider, dirs) for provider in PROVIDERS}
    except ImportValidationError as exc:
        _write_blocked(
            report_dir=args.report_dir,
            status="BLOCKED_INVALID_PREDICTIONS",
            errors=[str(exc)],
            searched_dirs=dirs,
        )
        print(json.dumps({"status": "BLOCKED_INVALID_PREDICTIONS", "error": str(exc)}, sort_keys=True))
        return 3
    missing = [provider for provider, candidate in found.items() if candidate is None]
    if missing:
        _write_blocked(
            report_dir=args.report_dir,
            status="BLOCKED_MISSING_PREDICTIONS",
            missing=missing,
            searched_dirs=dirs,
        )
        print(json.dumps({"status": "BLOCKED_MISSING_PREDICTIONS", "missing": missing}, sort_keys=True))
        return 2

    candidates = {provider: candidate for provider, candidate in found.items() if candidate is not None}
    try:
        task_rows = _read_jsonl_bytes(TASKS.read_bytes(), source=_display_path(TASKS))
        task_ids = [str(row.get("item_id")) for row in task_rows]
        if len(task_ids) != len(set(task_ids)):
            raise ImportValidationError("canonical Spurious V2 task manifest has duplicate item IDs")
        if not task_ids or any(item_id in {"", "None"} for item_id in task_ids):
            raise ImportValidationError("canonical Spurious V2 task manifest has missing item IDs")
        expected_items = set(task_ids)
        task_sha256 = _sha256(TASKS)
        results = [
            _validate_and_score(
                candidates[provider], expected_items=expected_items, task_sha256=task_sha256
            )
            for provider in PROVIDERS
        ]
        actions, canonical_changed = _commit_canonical(candidates, args.canonical_dir)
    except (ImportValidationError, OSError) as exc:
        _write_blocked(
            report_dir=args.report_dir,
            status="BLOCKED_INVALID_PREDICTIONS",
            errors=[str(exc)],
            searched_dirs=dirs,
        )
        print(json.dumps({"status": "BLOCKED_INVALID_PREDICTIONS", "error": str(exc)}, sort_keys=True))
        return 3

    decision = _write_success_reports(
        results=results,
        actions=actions,
        canonical_changed=canonical_changed,
        report_dir=args.report_dir,
        out_dir=args.out_dir,
    )
    print(json.dumps({"status": decision["status"], "decision": decision["decision"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
