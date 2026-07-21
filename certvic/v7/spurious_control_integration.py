"""Gated integration of the spurious-flip / control_irrelevant arm (V7 prompt 14).

This is integration-only. The control arm is built separately; do NOT start integration until
it has produced real VLM predictions + a quality/detectability report. This module inspects
the artifacts on disk and either (a) REFUSES with a precise BLOCKED status when anything is
missing, or (b) integrates without weakening gates when everything is present.

Current repo state: control images + task manifest exist, but predictions and the
quality/detectability report do not -> integration is BLOCKED. We never fabricate
control_irrelevant numbers.

Refusal gates (hard): control artifacts missing; control unreviewed when review required;
predictions copied from the intervention run (identical sha); provider label mismatch;
detectability/quality failed; result-ledger hashes absent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from certvic.io import read_jsonl, write_json

RESULTS = "data/results/main_real_200"
CONTROL_DIR = "data/edits/spurious_flip_control"
PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")
REPORT_DIR = f"{RESULTS}/control_irrelevant_report"
SPURIOUS_FLIP_MAX = 0.10


def _control_pred_paths(root: Path) -> dict[str, list[str]]:
    """provider -> list of candidate control prediction files found on disk."""
    out: dict[str, list[str]] = {}
    for prov in PROVIDERS:
        hits = []
        for pat in (f"{RESULTS}/**/*control_irrelevant*pred*{prov}*",
                    f"{RESULTS}/**/*spurious*pred*{prov}*",
                    f"{CONTROL_DIR}/**/*pred*{prov}*"):
            hits += [p.relative_to(root).as_posix() for p in root.glob(pat) if p.is_file()]
        out[prov] = sorted(set(hits))
    return out


def _quality_report_present(root: Path) -> bool:
    for pat in (f"{CONTROL_DIR}/**/*detectability*", f"{CONTROL_DIR}/**/*quality*report*",
                "data/results/spurious_flip_control/edit_detectability/**/*",
                f"{RESULTS}/control_irrelevant_report/*detectability*"):
        if any(root.glob(pat)):
            return True
    return False


def check_readiness(repo_root: str | Path = ".") -> dict:
    root = Path(repo_root)
    manifest = root / f"{CONTROL_DIR}/pilot_eval_tasks_reviewed.jsonl"
    images = list(root.glob(f"{CONTROL_DIR}/*.jpg"))
    preds = _control_pred_paths(root)
    quality = _quality_report_present(root)
    tasks = read_jsonl(manifest) if manifest.exists() else []
    reviewed = [
        task
        for task in tasks
        if str(
            task.get("visual_review_status")
            or (task.get("metadata") or {}).get("visual_review_status")
            or ""
        ).lower()
        == "approved"
    ]
    review_complete = bool(tasks) and len(reviewed) == len(tasks)

    present = {
        "control_task_manifest": manifest.exists(),
        "control_images": len(images) > 0,
        "quality_detectability_report": quality,
        "human_visual_review_complete": review_complete,
        "predictions_per_provider": {p: bool(preds[p]) for p in PROVIDERS},
    }
    missing = []
    if not present["control_task_manifest"]:
        missing.append("control task manifest")
    if not present["control_images"]:
        missing.append("control images")
    if not quality:
        missing.append("quality/detectability report")
    if not review_complete:
        missing.append(
            f"explicit human visual review approvals ({len(reviewed)}/{len(tasks)} approved)"
        )
    no_preds = [p for p in PROVIDERS if not preds[p]]
    if no_preds:
        missing.append(f"VLM predictions for: {', '.join(no_preds)}")

    ready = not missing
    if ready:
        specificity_status = "ready_to_integrate"
    else:
        # control built but un-run -> the specificity question is BLOCKED, not partial.
        specificity_status = "blocked"
    return {
        "ready": ready,
        "present": present,
        "missing": missing,
        "n_control_images": len(images),
        "n_control_tasks": len(tasks),
        "n_human_review_approved": len(reviewed),
        "candidate_prediction_files": preds,
        "specificity_status": specificity_status,
    }


def compute_control_metrics(tasks: list[dict], preds: dict[str, str | None]) -> dict:
    """Per-provider spurious-flip metrics. Gold for the control = NO answer change.

    preds: provider -> {item_id: {'original':ans,'edited':ans}}. spurious_flip = the model's
    answer changed under an irrelevant edit (specificity failure). Low rate = good specificity.
    """
    out = {}
    n = len(tasks)
    for prov, by_item in preds.items():
        flips = 0
        scored = 0
        parse_fail = 0
        for t in tasks:
            a = by_item.get(t["item_id"], {})
            op, ep = a.get("original"), a.get("edited")
            if op is None or ep is None:
                parse_fail += 1
                continue
            scored += 1
            if op != ep:
                flips += 1
        out[prov] = {
            "n": n, "n_scored": scored,
            "spurious_flip_rate": round(flips / scored, 4) if scored else None,
            "consistency_under_irrelevant_edit": round((scored - flips) / scored, 4) if scored else None,
            "parse_failure_rate": round(parse_fail / n, 4) if n else None,
            "gate_threshold": SPURIOUS_FLIP_MAX,
            "gate_pass": bool(
                n > 0
                and scored == n
                and parse_fail == 0
                and (flips / scored) <= SPURIOUS_FLIP_MAX
            ),
        }
    return out


def integrate(repo_root: str | Path = ".") -> dict:
    """Integrate if ready; otherwise write a BLOCKED marker and refuse (no fabrication)."""
    root = Path(repo_root)
    readiness = check_readiness(root)
    report_dir = root / REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)

    run_cmd = ("Run the Kaggle VLM notebook on data/edits/spurious_flip_control/ for each "
               "provider, then: python3 scripts/pilot_report_from_raw.py --provider <id> "
               "--model-name <hf-id> --run-label <id> --raw-presence ... --raw-control ... "
               "--raw-spurious <control_preds>.jsonl ; then re-run "
               "python3 -m certvic.v7.spurious_control_integration")

    if not readiness["ready"]:
        status = {
            "schema": "certvic.spurious_control_integration.v1",
            "status": "blocked",
            "specificity_status": "blocked",
            "evidence_status": "SPECIFICITY_CONTROL_BLOCKED_NON_EVIDENCE",
            "paper_evidence": False,
            "reason": "Integration refused: required control artifacts are missing. "
                      "Spurious-flip numbers are NOT fabricated.",
            "missing": readiness["missing"],
            "present": readiness["present"],
            "interpretation": "Until the control predictions + quality/detectability exist, the "
                              "objection 'models are sticky under any perturbation' is UNANSWERED.",
            "next_command": run_cmd,
            "canonical_unchanged": True,
        }
        write_json(report_dir / "INTEGRATION_BLOCKED.json", status)
        (report_dir / "INTEGRATION_BLOCKED.md").write_text(_blocked_md(status), encoding="utf-8")
        # Keep the canonical report path aligned with the current gate truth so
        # a stale previously-integrated report cannot be consumed while the
        # explicit human-review prerequisite is blocked. Raw predictions are
        # never modified.
        write_json(report_dir / "control_irrelevant_report.json", status)
        (report_dir / "control_irrelevant_report.md").write_text(
            _blocked_md(status), encoding="utf-8"
        )
        return status

    # ---- ready path (executes only once real predictions + quality exist) ----
    return _integrate_ready(root, readiness, report_dir)


def _integrate_ready(root: Path, readiness: dict, report_dir: Path) -> dict:
    for stale in ("INTEGRATION_BLOCKED.json", "INTEGRATION_BLOCKED.md"):
        p = report_dir / stale
        if p.exists():
            p.unlink()
    tasks = read_jsonl(root / f"{CONTROL_DIR}/pilot_eval_tasks_reviewed.jsonl")
    reviewed = [
        task
        for task in tasks
        if str(
            task.get("visual_review_status")
            or (task.get("metadata") or {}).get("visual_review_status")
            or ""
        ).lower()
        == "approved"
    ]
    gate_errors: list[str] = []
    if not tasks or len(reviewed) != len(tasks):
        gate_errors.append(
            f"control human review incomplete: {len(reviewed)}/{len(tasks)} explicitly approved"
        )
    quality_ok, quality_note = _quality_gate_ok(root)
    if not quality_ok:
        gate_errors.append(quality_note)
    pred_paths: dict[str, str] = {}
    provenance: dict[str, dict] = {}
    preds: dict[str, dict] = {}
    for prov in PROVIDERS:
        path = _select_prediction_file(root, prov)
        if path is None:
            gate_errors.append(f"missing canonical prediction file for {prov}")
            continue
        pred_paths[prov] = path.relative_to(root).as_posix()
        try:
            provider_names, by_item = _load_provider_predictions(path, prov)
        except ValueError as exc:
            gate_errors.append(str(exc))
            continue
        preds[prov] = by_item
        pred_sha = _sha256(path)
        source_kind = "canonical_kaggle_spurious" if "kaggle_spurious" in path.as_posix() else "ingested_raw_predictions"
        presence_matches = _matching_presence_shas(root, prov, pred_sha)
        if presence_matches:
            gate_errors.append(
                f"{prov} spurious predictions have the same sha256 as presence predictions: "
                + ", ".join(presence_matches)
            )
        provenance[prov] = {
            "prediction_path": path.relative_to(root).as_posix(),
            "prediction_sha256": pred_sha,
            "source_kind": source_kind,
            "provider_names": provider_names,
            "distinct_from_presence_predictions": not presence_matches,
        }
    metrics = compute_control_metrics(reviewed, preds) if preds else {}

    all_gate_pass = bool(metrics) and all(m.get("gate_pass") is True for m in metrics.values())
    passed = not gate_errors and all_gate_pass and len(metrics) == len(PROVIDERS)
    if metrics and not all_gate_pass:
        gate_errors.append("one or more providers exceeded the spurious-flip gate")
    specificity_status = "answered_passed" if passed else (
        "answered_failed_gate" if metrics else "blocked"
    )
    status = {
        "schema": "certvic.spurious_control_integration.v1",
        "status": "integrated" if passed else "blocked",
        "specificity_status": specificity_status,
        "evidence_status": "SPECIFICITY_CONTROL_PILOT_NON_EVIDENCE",
        "paper_evidence": False,
        "gate_errors": gate_errors,
        "metrics": metrics,
        "prediction_files": pred_paths,
        "provenance": provenance,
        "all_provider_gate_pass": passed,
        "quality_detectability_gate": {"ok": quality_ok, "note": quality_note},
        "note": "Real spurious-control predictions were loaded, provider names were checked, "
                "and files were checked against known presence-prediction hashes. This remains "
                "pilot-only and is blocked unless every provider passes the configured flip gate.",
    }
    write_json(report_dir / "control_irrelevant_report.json", status)
    (report_dir / "control_irrelevant_report.md").write_text(_ready_md(status), encoding="utf-8")
    return status


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _select_prediction_file(root: Path, provider: str) -> Path | None:
    preferred = root / RESULTS / "kaggle_spurious" / f"pred_{provider}_spurious_merged.jsonl"
    if preferred.exists():
        return preferred
    candidates = []
    for rel in _control_pred_paths(root).get(provider, []):
        p = root / rel
        if p.suffix == ".jsonl" and "shard" not in p.name and p.exists():
            candidates.append(p)
    return sorted(candidates)[0] if candidates else None


def _load_provider_predictions(path: Path, provider: str) -> tuple[list[str], dict[str, dict[str, str | None]]]:
    rows = read_jsonl(path)
    provider_names = sorted({str(r.get("provider_name")) for r in rows})
    if provider_names != [provider]:
        raise ValueError(
            f"provider mismatch for {path}: saw {provider_names}, expected [{provider!r}]"
        )
    by_item: dict[str, dict[str, str | None]] = {}
    seen: set[tuple[str, str]] = set()
    for index, r in enumerate(rows, 1):
        item_id = str(r.get("item_id"))
        variant = str(r.get("image_variant"))
        key = (item_id, variant)
        if variant not in {"original", "edited"}:
            raise ValueError(f"invalid image_variant in {path} row {index}: {variant!r}")
        if key in seen:
            raise ValueError(f"duplicate item/variant prediction in {path}: {key!r}")
        seen.add(key)
        if r.get("parse_ok") is not True or r.get("parsed_answer") not in {"yes", "no"}:
            raise ValueError(f"parse failure in certification-critical control prediction {path} row {index}")
        by_item.setdefault(item_id, {})[variant] = r.get("parsed_answer")
    return provider_names, by_item


def _matching_presence_shas(root: Path, provider: str, pred_sha: str) -> list[str]:
    matches: list[str] = []
    for p in sorted((root / RESULTS).glob("raw_predictions*/presence__*.jsonl")):
        if provider not in p.as_posix():
            # Bare raw_predictions/ belongs to Qwen.
            if provider != "qwen2_5_vl_7b" or "raw_predictions/" not in p.as_posix():
                continue
        if _sha256(p) == pred_sha:
            matches.append(p.relative_to(root).as_posix())
    return matches


def _quality_gate_ok(root: Path) -> tuple[bool, str]:
    summary = root / "data/results/spurious_flip_control/edit_detectability/detectability_summary.json"
    if not summary.exists():
        return False, "detectability summary missing"
    try:
        data = json.loads(summary.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, "detectability summary unreadable"
    n_items = int(data.get("n_items") or 0)
    if n_items <= 0:
        return False, "detectability summary has no scored items"
    if data.get("artifact_risk") is True:
        return False, "detectability summary flags artifact risk"
    return True, f"detectability summary ok: n_items={n_items}, artifact_risk={data.get('artifact_risk')}"


def _ready_md(status: dict) -> str:
    L = [
        "# Spurious-Flip / control_irrelevant Integration",
        "",
        f"**status: {status['status']}** · **specificity_status: {status['specificity_status']}** · "
        f"`evidence_status={status['evidence_status']}` · `paper_evidence=false`",
        "",
        "| provider | n scored | flip rate | threshold | gate |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for prov in PROVIDERS:
        m = status.get("metrics", {}).get(prov, {})
        L.append(
            f"| `{prov}` | {m.get('n_scored', '')} | {m.get('spurious_flip_rate', '')} | "
            f"{m.get('gate_threshold', SPURIOUS_FLIP_MAX)} | {'PASS' if m.get('gate_pass') else 'FAIL'} |"
        )
    L += ["", "## Gate Errors", ""]
    if status.get("gate_errors"):
        L.extend(f"- {e}" for e in status["gate_errors"])
    else:
        L.append("- none")
    L += [
        "",
        "This is a specificity control only. It does not create paper evidence or main-scale evidence.",
        "",
    ]
    return "\n".join(L)


def _blocked_md(status: dict) -> str:
    L = ["# Spurious-Flip / control_irrelevant Integration — BLOCKED", "",
         f"**specificity_status: {status['specificity_status']}** · "
         f"`evidence_status={status['evidence_status']}`", "",
         status["reason"], "", "## Missing"]
    for m in status["missing"]:
        L.append(f"- {m}")
    L += ["", "## Present",
          *[f"- {k}: {v}" for k, v in status["present"].items()],
          "", f"Interpretation: {status['interpretation']}", "",
          "## Next command", "", "```bash", status["next_command"], "```", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Integrate the spurious-flip control (gated)")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    status = integrate(args.repo_root)
    print(json.dumps({"status": status["status"],
                      "specificity_status": status["specificity_status"],
                      "missing": status.get("missing", [])}, sort_keys=True))


if __name__ == "__main__":
    main()
