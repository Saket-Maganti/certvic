"""Canonical result ledger + integrity audit (V7 prompt 01).

The first three-model pilot result is now valuable, so it must be impossible to
accidentally cite a stale, mock-labeled, or non-canonical artifact. This module:

* **builds** a ledger that maps every pilot number to its exact source artifact
  (task file, raw predictions, scoring files) with sha256 hashes, recomputed from
  disk -- never hand-entered; and
* **audits** an existing ledger against hard provenance gates.

The audit fails if:
  1. a row declares metrics but has no backing artifact path;
  2. a recorded artifact path does not exist;
  3. a recomputed sha256 mismatches the recorded one;
  4. a canonical / claim-eligible row cites ``final_report/`` or ``final_report_v2/``;
  5. an InternVL/LLaVA row references a Qwen (or any foreign provider) artifact;
  6. a mock/smoke/simulated artifact is marked claim-eligible.

Makes no evidence claims and runs no models.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.hashing import sha256_file
from certvic.io import read_json, write_json

# ---------------------------------------------------------------------------
# Canonical configuration
# ---------------------------------------------------------------------------

DEFAULT_LEDGER = "registry/results/main200_pilot_result_ledger.json"
DEFAULT_LEDGER_MD = "registry/results/main200_pilot_result_ledger.md"

# The three registered open VLM providers (see certvic/providers/registry.py).
PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")

# Shared task files that legitimately appear in every model's rows (they carry no
# provider token and are therefore not cross-model contamination).
SHARED_TASK_TOKENS = ("pilot_eval_taskitems", "absent_object_control", "pilot_eval_tasks_reviewed")

# Substrings that mark an artifact as non-evidence regardless of its numbers.
NON_CANONICAL_DIR_TOKENS = ("final_report", "final_report_v2")
MOCK_TOKENS = ("mock", "smoke", "synthetic", "simulated", "sim_matrix")

CLAIM_ELIGIBLE_LEVELS = {"pilot_only", "evidence_candidate"}

# Qwen2.5-VL files live in the *bare* report/prediction dirs (no provider suffix), so a
# token-in-path check cannot catch "InternVL row cites a Qwen file". Instead we resolve
# which provider an artifact path *belongs to* and compare it to the row's provider.


def _belongs_to(rel_path: str) -> str | None:
    """Resolve the owning provider of a per-model artifact path, or None if shared."""
    p = rel_path
    if "__internvl_8b" in p or "/pred_internvl_8b" in p or "internvl_8b_" in p:
        return "internvl_8b"
    if "__llava_onevision_7b" in p or "llava_onevision_7b" in p:
        return "llava_onevision_7b"
    if "qwen2_5_vl_7b" in p:
        return "qwen2_5_vl_7b"
    # Bare (unsuffixed) Qwen dirs.
    if "/pilot_report/" in p or "/raw_predictions/" in p:
        return "qwen2_5_vl_7b"
    return None
NON_EVIDENCE_STATUS_HARD = {"MOCK_ONLY", "SIMULATED_ONLY", "PLANNED_ONLY", "PREVIEW_ONLY"}

REGEN_CMD = (
    "scripts/pilot_report_from_raw.py --provider {provider} --model-name {model} "
    "--run-label {run_label} --raw-presence ... --raw-control ...  ;  "
    "scripts/build_multimodel_summary.py"
)


def _artifact(repo_root: Path, rel: str, recorded_sha: str | None = None) -> dict:
    """Build one artifact entry, recomputing the sha256 from disk if present."""
    abspath = repo_root / rel
    sha = sha256_file(abspath) if abspath.exists() else None
    entry = {"path": rel, "sha256": sha, "exists": abspath.exists()}
    if recorded_sha is not None:
        entry["provenance_sha256"] = recorded_sha
    return entry


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def _discover_reports(results_root: Path) -> dict[str, Path]:
    """provider -> its own pilot_result.json (keyed by the file's self-reported provider)."""
    found: dict[str, Path] = {}
    for jf in sorted(results_root.glob("pilot_report*/pilot_result.json")):
        try:
            data = json.loads(jf.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        provider = data.get("provider")
        if provider:
            found[provider] = jf
    return found


def _rows_for_report(repo_root: Path, report_path: Path) -> list[dict]:
    data = json.loads(report_path.read_text())
    provider = data["provider"]
    model = data.get("model", provider)
    run_label = data.get("run_label", provider)
    ts = data.get("generated_utc")
    ev = data.get("evidence_status", "HUMAN_REVIEWED_NON_EVIDENCE")
    report_dir = report_path.parent
    rel_report_dir = report_dir.relative_to(repo_root).as_posix()

    # Raw predictions, keyed by arm, discovered from the report's own provenance block.
    ingested = {i["arm"]: i for i in data.get("provenance", {}).get("ingested", [])}

    def raw_for(arm: str) -> list[dict]:
        info = ingested.get(arm)
        if not info:
            return []
        return [_artifact(repo_root, info["ingested_path"], info.get("sha256"))]

    generated_by = REGEN_CMD.format(provider=provider, model=model, run_label=run_label)
    rows: list[dict] = []

    # ---- presence intervention (the certified headline arm) ----
    ps = data["presence_intervention"]["summary"]
    pc = data["presence_intervention"]["certification"]
    rows.append({
        "result_id": f"{provider}__presence",
        "model": model, "provider": provider, "run_label": run_label,
        "task_set": "presence",
        "canonical": True,
        "claim_level": "pilot_only",
        "evidence_status": ev,
        "generated_by": generated_by,
        "timestamp": ts,
        "metrics": {
            "n": ps.get("n"),
            "original_accuracy": round(ps["original_accuracy"], 4),
            "consistency": round(ps["consistency_rate"], 4),
            "gap": round(ps["intervention_consistency_gap"], 4),
            "cs_lower_bound": pc.get("lower_bound"),
            "cs_upper_bound": pc.get("upper_bound"),
            "certified": bool(pc.get("certified")),
            "parse_failure_rate": ps.get("parse_failure_rate"),
        },
        "artifacts": {
            "task_file": _artifact(repo_root, "data/results/main_real_200/pilot_eval_taskitems_v2.jsonl"),
            "raw_predictions": raw_for("presence"),
            "scoring": [
                _artifact(repo_root, f"{rel_report_dir}/pilot_result.json"),
                _artifact(repo_root, f"{rel_report_dir}/presence_certification.json"),
                _artifact(repo_root, f"{rel_report_dir}/presence_scores_summary.json"),
            ],
        },
        "caveats": [
            "presence arm: high original accuracy => gap interpretable as visual-update failure",
            "certified under the pilot protocol only; single model's gap is not cross-model evidence",
            "spurious-flip/control_irrelevant specificity control not yet run",
        ],
    })

    # ---- absent-object control (natural absence, no edits) ----
    ctl = data["absent_object_control"]
    rows.append({
        "result_id": f"{provider}__absent_control",
        "model": model, "provider": provider, "run_label": run_label,
        "task_set": "absent_control",
        "canonical": True,
        "claim_level": "pilot_only",
        "evidence_status": ev,
        "generated_by": generated_by,
        "timestamp": ts,
        "metrics": {
            "n": ctl.get("n"),
            "absent_accuracy": ctl.get("absent_accuracy"),
            "absent": f"{ctl.get('absent_correct')}/{ctl.get('absent_n')}",
            "present_accuracy": ctl.get("present_accuracy"),
            "present": f"{ctl.get('present_correct')}/{ctl.get('present_n')}",
            "overall_accuracy": ctl.get("overall_accuracy"),
        },
        "artifacts": {
            "task_file": _artifact(repo_root, "data/edits/absent_object_control/pilot_eval_tasks_reviewed.jsonl"),
            "raw_predictions": raw_for("control"),
            "scoring": [_artifact(repo_root, f"{rel_report_dir}/absent_object_control.json")],
        },
        "caveats": [
            "natural absent-object perception (no edits) -- rules out the presupposition confound",
            "present-side accuracy < 1.0 reflects ordinary VLM error, not an edit",
        ],
    })
    return rows


def build_ledger(repo_root: str | Path = ".") -> dict:
    root = Path(repo_root)
    results_root = root / "data/results/main_real_200"
    found = _discover_reports(results_root)
    rows: list[dict] = []
    for provider in PROVIDERS:
        if provider in found:
            rows.extend(_rows_for_report(root, found[provider]))
    return {
        "schema": "certvic.result_ledger.v1",
        "title": "CertVIC main_real_200 pilot result ledger",
        "claim_level": "pilot_only",
        "evidence_status": "HUMAN_REVIEWED_NON_EVIDENCE",
        "paper_evidence": False,
        "note": (
            "Every metric traces to a sha256-locked artifact. Non-canonical reports are "
            "excluded by construction; see non_canonical_excluded."
        ),
        "non_canonical_excluded": {
            "data/results/main_real_200/final_report": "smoke-template markdown (MOCK_ONLY narrative); not canonical",
            "data/results/main_real_200/final_report_v2": "smoke-template markdown; not canonical",
            "affordance_intervention arm": "original accuracy ~chance; confounded; not certified",
        },
        "n_rows": len(rows),
        "rows": rows,
    }


def write_ledger(ledger: dict, repo_root: str | Path = ".",
                 json_rel: str = DEFAULT_LEDGER, md_rel: str = DEFAULT_LEDGER_MD) -> tuple[str, str]:
    root = Path(repo_root)
    write_json(root / json_rel, ledger)
    (root / md_rel).write_text(render_ledger_md(ledger), encoding="utf-8")
    return json_rel, md_rel


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def _iter_artifacts(row: dict):
    arts = row.get("artifacts", {})
    tf = arts.get("task_file")
    if isinstance(tf, dict):
        yield "task_file", tf
    for a in arts.get("raw_predictions", []) or []:
        yield "raw_predictions", a
    for a in arts.get("scoring", []) or []:
        yield "scoring", a


def audit_ledger(ledger: dict, repo_root: str | Path = ".") -> dict:
    root = Path(repo_root)
    failures: list[dict] = []

    def fail(gate: str, result_id: str, detail: str) -> None:
        failures.append({"gate": gate, "result_id": result_id, "detail": detail})

    rows = ledger.get("rows", [])
    if not rows:
        fail("empty_ledger", "-", "ledger has no rows")

    for row in rows:
        rid = row.get("result_id", "?")
        provider = row.get("provider", "")
        claim_level = row.get("claim_level", "")
        canonical = bool(row.get("canonical"))
        claim_eligible = canonical or claim_level in CLAIM_ELIGIBLE_LEVELS
        metrics = {k: v for k, v in (row.get("metrics") or {}).items() if v is not None}
        artifacts = list(_iter_artifacts(row))

        # Gate 1: a number must have a backing artifact path.
        if metrics:
            has_scoring = any(kind == "scoring" for kind, _ in artifacts)
            has_raw = any(kind == "raw_predictions" for kind, _ in artifacts)
            has_task = any(kind == "task_file" for kind, _ in artifacts)
            if not has_scoring:
                fail("number_without_artifact", rid, "metrics present but no scoring artifact")
            if not has_raw:
                fail("number_without_artifact", rid, "metrics present but no raw_predictions artifact")
            if not has_task:
                fail("number_without_artifact", rid, "metrics present but no task_file artifact")

        # Gates 2 & 3: path exists + hash matches.
        for kind, art in artifacts:
            rel = art.get("path", "")
            abspath = root / rel
            if not abspath.exists():
                fail("artifact_path_missing", rid, f"{kind}: {rel}")
                continue
            recomputed = sha256_file(abspath)
            if art.get("sha256") and recomputed != art["sha256"]:
                fail("hash_mismatch", rid, f"{kind}: {rel} recorded={art['sha256'][:12]} now={recomputed[:12]}")
            # Cross-check raw-pred provenance hash if recorded.
            if kind == "raw_predictions" and art.get("provenance_sha256") and recomputed != art["provenance_sha256"]:
                fail("hash_mismatch", rid,
                     f"raw_predictions {rel}: differs from report provenance sha256 (file changed since report)")

            # Gate 4: canonical/claim-eligible row may not cite non-canonical dirs.
            if claim_eligible and any(tok in rel for tok in NON_CANONICAL_DIR_TOKENS):
                fail("non_canonical_cited", rid, f"claim-eligible row cites non-canonical artifact: {rel}")

            # Gate 6: mock/smoke/simulated artifact marked claim-eligible.
            if claim_eligible and any(tok in rel.lower() for tok in MOCK_TOKENS):
                fail("mock_marked_claim_eligible", rid, f"claim-eligible row cites mock/smoke artifact: {rel}")

            # Gate 5: cross-model contamination -- a per-model artifact must belong to
            # this row's provider. Shared task files belong to no provider (skipped).
            if not any(tok in rel for tok in SHARED_TASK_TOKENS):
                owner = _belongs_to(rel)
                if owner is not None and owner != provider:
                    fail("cross_model_contamination", rid,
                         f"{provider} row references {owner} artifact: {rel}")

        # Gate 6b: evidence_status hard-non-evidence must be claim_level=blocked.
        ev = str(row.get("evidence_status", "")).upper()
        if ev in NON_EVIDENCE_STATUS_HARD and claim_level != "blocked":
            fail("mock_marked_claim_eligible", rid,
                 f"evidence_status {ev} but claim_level={claim_level} (must be 'blocked')")

    return {
        "audit": "v7_result_ledger",
        "passed": not failures,
        "n_rows": len(rows),
        "n_failures": len(failures),
        "failures": failures,
        "evidence_claims_made": False,
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_ledger_md(ledger: dict) -> str:
    L: list[str] = []
    A = L.append
    A("# CertVIC main_real_200 — Pilot Result Ledger")
    A("")
    A(f"**{ledger['claim_level'].upper()}** (`evidence_status={ledger['evidence_status']}`, "
      f"`paper_evidence={ledger['paper_evidence']}`). {ledger['note']}")
    A("")
    A("Every number below is recomputed from a sha256-locked artifact by "
      "`certvic.v7.result_ledger_audit`; nothing is hand-entered.")
    A("")
    A("| result_id | task_set | metrics | scoring artifact | sha256 (12) |")
    A("|---|---|---|---|---|")
    for row in ledger["rows"]:
        scoring = (row.get("artifacts", {}).get("scoring") or [{}])[0]
        sha = (scoring.get("sha256") or "")[:12]
        m = row.get("metrics", {})
        if row["task_set"] == "presence":
            mtxt = f"a={m.get('original_accuracy')} p={m.get('consistency')} Δ={m.get('gap')} CS_LB={round(m.get('cs_lower_bound'),4) if m.get('cs_lower_bound') else m.get('cs_lower_bound')} cert={m.get('certified')}"
        else:
            mtxt = f"absent={m.get('absent')} present={m.get('present')}"
        A(f"| `{row['result_id']}` | {row['task_set']} | {mtxt} | `{scoring.get('path','')}` | `{sha}` |")
    A("")
    A("## Excluded (non-canonical)")
    A("")
    for path, why in ledger.get("non_canonical_excluded", {}).items():
        A(f"- `{path}` — {why}")
    A("")
    A("Verify integrity:")
    A("")
    A("```bash")
    A("python3 -m certvic.v7.result_ledger_audit --ledger registry/results/main200_pilot_result_ledger.json")
    A("```")
    A("")
    return "\n".join(L)


def render_audit_report(result: dict) -> str:
    L = ["# V7 Result Ledger Audit", "", f"Passed: {result['passed']}",
         f"Rows: {result['n_rows']}  Failures: {result['n_failures']}", ""]
    if result["failures"]:
        L += ["| Gate | result_id | Detail |", "| --- | --- | --- |"]
        for f in result["failures"]:
            L.append(f"| {f['gate']} | `{f['result_id']}` | {f['detail']} |")
    else:
        L.append("All ledger integrity gates passed.")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build / audit the canonical pilot result ledger")
    parser.add_argument("--ledger", default=DEFAULT_LEDGER, help="ledger JSON path")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--rebuild", action="store_true", help="regenerate the ledger from canonical artifacts first")
    parser.add_argument("--out", help="optional audit report markdown path")
    parser.add_argument("--json-out", help="optional audit result JSON path")
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.repo_root)
    if args.rebuild:
        ledger = build_ledger(root)
        write_ledger(ledger, root, json_rel=args.ledger)
        print(json.dumps({"rebuilt": args.ledger, "n_rows": ledger["n_rows"]}, sort_keys=True))
    else:
        ledger = read_json(root / args.ledger)

    result = audit_ledger(ledger, root)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(render_audit_report(result), encoding="utf-8")
    if args.json_out:
        write_json(args.json_out, result)
    print(json.dumps({"passed": result["passed"], "n_rows": result["n_rows"],
                      "n_failures": result["n_failures"]}, sort_keys=True))
    if not result["passed"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
