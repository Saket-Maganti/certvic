"""Aggregate per-model PILOT reports into a multi-model comparison (no fabrication).

Reads each model's ``pilot_result.json`` (real artifacts only, discovered by the
``provider`` field each file records about itself). The three registered open VLMs
always appear as rows; a model that has not been run shows ``status="not_run"`` with
**null** metrics -- never populated from another model's numbers. Every populated
row is sourced from that model's own report file (path recorded in ``source``).

PILOT ONLY. Makes no paper-grade claim. Comparing models is descriptive; it does not
upgrade any single-model certified gap into cross-model evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS_ROOT = REPO / "data/results/main_real_200"

# Registered open VLM providers we intend to compare (certvic/providers/registry.py).
MODELS = ["qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"]

_COLUMNS = [
    "provider", "model", "status", "n",
    "original_accuracy", "consistency", "gap",
    "cs_lower_bound", "cs_upper_bound", "certified",
    "control_absent", "control_present", "spurious_flip_rate", "source",
]


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def discover(results_root: Path) -> dict[str, Path]:
    """Map provider -> its own pilot_result.json (keyed by the file's self-reported provider)."""
    found: dict[str, Path] = {}
    for jf in sorted(results_root.glob("pilot_report*/pilot_result.json")):
        try:
            data = json.loads(jf.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        provider = data.get("provider")
        if provider:  # only trust files that self-identify their model
            found[provider] = jf
    return found


def _row_from_report(provider: str, path: Path) -> dict:
    data = json.loads(path.read_text())
    ps = data["presence_intervention"]["summary"]
    pc = data["presence_intervention"]["certification"]
    ctl = data["absent_object_control"]
    sp = data.get("spurious_flip_control") or {}
    return {
        "provider": provider,
        "model": data.get("model", provider),
        "status": "run",
        "n": ps.get("n"),
        "original_accuracy": round(ps["original_accuracy"], 4),
        "consistency": round(ps["consistency_rate"], 4),
        "gap": round(ps["intervention_consistency_gap"], 4),
        "cs_lower_bound": round(pc["lower_bound"], 4) if pc.get("lower_bound") is not None else None,
        "cs_upper_bound": round(pc["upper_bound"], 4) if pc.get("upper_bound") is not None else None,
        "certified": bool(pc["certified"]),
        "control_absent": f"{ctl['absent_correct']}/{ctl['absent_n']}",
        "control_present": f"{ctl['present_correct']}/{ctl['present_n']}",
        "spurious_flip_rate": sp.get("spurious_flip_rate"),
        "source": _rel(path),
    }


def _row_not_run(provider: str) -> dict:
    row = {c: None for c in _COLUMNS}
    row["provider"] = provider
    row["model"] = provider
    row["status"] = "not_run"
    return row


def build_summary(results_root: Path = RESULTS_ROOT, models: list[str] = MODELS) -> dict:
    found = discover(results_root)
    rows = [_row_from_report(p, found[p]) if p in found else _row_not_run(p) for p in models]
    n_run = sum(1 for r in rows if r["status"] == "run")
    summary = {
        "evidence_status": "HUMAN_REVIEWED_NON_EVIDENCE",
        "paper_evidence": False,
        "note": "Pilot-only multi-model comparison. not_run rows are null, never copied from another model.",
        "n_run": n_run,
        "n_models": len(models),
        "models": rows,
    }
    results_root.mkdir(parents=True, exist_ok=True)
    (results_root / "multimodel_pilot_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (results_root / "multimodel_pilot_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow({c: ("" if r.get(c) is None else r[c]) for c in _COLUMNS})
    (results_root / "multimodel_pilot_summary.md").write_text(_md(summary), encoding="utf-8")
    return summary


def _fmt(v) -> str:
    if v is None:
        return "--"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def _md(summary: dict) -> str:
    L: list[str] = []
    A = L.append
    A("# CertVIC Multi-Model Pilot Summary")
    A("")
    A(f"**PILOT ONLY (evidence_status={summary['evidence_status']}, paper_evidence=False).** "
      f"{summary['n_run']}/{summary['n_models']} models run. Rows marked `not_run` are placeholders "
      "with no numbers -- they are NOT filled from any other model.")
    A("")
    A("Presence-question intervention (same 91 reviewed items) + absent-object control (120 items). "
      "`gap = a - p`; `certified` = anytime-valid CS lower bound > 0.05 for that model's own run.")
    A("")
    A("| model | status | n | a (orig acc) | p (consistency) | gap | CS LB | certified | "
      "control absent | control present | spurious flip |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in summary["models"]:
        A("| " + " | ".join([
            r["model"], r["status"], _fmt(r["n"]),
            _fmt(r["original_accuracy"]), _fmt(r["consistency"]), _fmt(r["gap"]),
            _fmt(r["cs_lower_bound"]), _fmt(r["certified"]),
            _fmt(r["control_absent"]), _fmt(r["control_present"]), _fmt(r["spurious_flip_rate"]),
        ]) + " |")
    A("")
    A("Sources (per-model real reports):")
    A("")
    for r in summary["models"]:
        A(f"- `{r['provider']}`: {r['source'] if r['source'] else '(not run yet)'}")
    A("")
    A("Cross-model interpretation is descriptive only; a single model's certified gap is not "
      "cross-model evidence. Run the remaining models with `scripts/pilot_report_from_raw.py "
      "--provider <id> --model-name <hf-id> --run-label <id> --raw-presence ... --raw-control ...`.")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", default=str(RESULTS_ROOT))
    args = parser.parse_args(argv)
    summary = build_summary(Path(args.results_root))
    print(json.dumps({"n_run": summary["n_run"], "n_models": summary["n_models"],
                      "models": [r["provider"] + ":" + r["status"] for r in summary["models"]]},
                     sort_keys=True))


if __name__ == "__main__":
    sys.path.insert(0, str(REPO))
    main()
