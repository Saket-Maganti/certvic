"""Build V8 mechanism-probe diagnostic reports from flat Kaggle prediction rows."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from certvic.io import write_json

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "data/results/main_real_200"
DEFAULT_PRED_DIR = RESULTS / "kaggle_mechanism"
DEFAULT_OUT_DIR = RESULTS / "v8_upgrade"
TASK_ROOT = RESULTS / "mechanism_probes"
PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")
FAMILIES = ("context_suppression", "object_list", "region_focused", "two_step")
SPEC_BLOCKED_FAMILIES = ("original_vs_edited",)
EXPECTED_ROWS = 364


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _pred_path(pred_dir: Path, provider: str) -> Path:
    return pred_dir / f"pred_{provider}_mechanism.jsonl"


def _round(v: float | None) -> float | None:
    return round(v, 4) if v is not None else None


def _load_task_specs(task_root: Path = TASK_ROOT) -> dict[tuple[str, str], dict]:
    specs: dict[tuple[str, str], dict] = {}
    for family in FAMILIES:
        path = task_root / family / "tasks.jsonl"
        if not path.exists():
            continue
        for row in _read_jsonl(path):
            specs[(family, str(row.get("item_id")))] = row
    return specs


def _last_yes_no(text: str | None) -> str | None:
    if not text:
        return None
    toks = re.findall(r"\b(yes|no)\b", text.lower())
    return toks[-1] if toks else None


def _target_mentioned(text: str | None, target: str | None) -> bool | None:
    if not text or not target:
        return None
    target_norm = target.lower().replace("_", " ").strip()
    words = [w.strip() for w in re.split(r"[,;\n]+", text.lower()) if w.strip()]
    if any(target_norm == w or target_norm in w.split() for w in words):
        return True
    return target_norm in text.lower()


def _decision_for(row: dict, family: str) -> str | None:
    parsed = row.get("parsed_answer")
    if family == "two_step":
        return _last_yes_no(row.get("raw_output") or parsed)
    if parsed in {"yes", "no"}:
        return parsed
    return None


def _summarize_provider(path: Path, provider: str, specs: dict[tuple[str, str], dict]) -> tuple[dict, list[dict]]:
    rows = _read_jsonl(path)
    ids = [r.get("prediction_id") or f"{r.get('item_id')}::{i}" for i, r in enumerate(rows)]
    dupes = sorted(k for k, n in Counter(ids).items() if n > 1)
    provider_names = sorted({r.get("provider_name") for r in rows})

    by_family: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        fam = (r.get("metadata") or {}).get("probe_family")
        by_family[str(fam)].append(r)

    blocked_rows = [fam for fam in SPEC_BLOCKED_FAMILIES if by_family.get(fam)]
    if blocked_rows:
        raise SystemExit(
            "REFUSED: mechanism predictions include SPEC_BLOCKED family/families: "
            + ", ".join(blocked_rows)
        )

    family_summaries: dict[str, dict] = {}
    csv_rows: list[dict] = []
    for family in FAMILIES:
        fr = by_family.get(family, [])
        n = len(fr)
        answer_counts = Counter(str(r.get("parsed_answer")) for r in fr)
        decision_rows = []
        decision_correct = 0
        target_rows = []
        target_mentions = 0
        false_target_mentions = 0
        for r in fr:
            spec = specs.get((family, str(r.get("item_id"))), {})
            scoring = spec.get("scoring") or {}
            gold = scoring.get("gold_post_edit_answer")
            decision = _decision_for(r, family)
            if decision in {"yes", "no"} and gold in {"yes", "no"}:
                decision_rows.append(r)
                decision_correct += int(decision == gold)
            if family == "object_list":
                mentioned = _target_mentioned(r.get("raw_output") or r.get("parsed_answer"), spec.get("target_object"))
                if mentioned is not None and gold in {"yes", "no"}:
                    target_rows.append(r)
                    target_mentions += int(mentioned)
                    false_target_mentions += int(mentioned and gold == "no")

        parse_ok = sum(1 for r in fr if r.get("parse_ok") is True)
        summary = {
            "n_rows": n,
            "expected_rows": EXPECTED_ROWS // len(FAMILIES),
            "raw_parse_ok": parse_ok,
            "raw_parse_rate": _round(parse_ok / n) if n else None,
            "answer_counts_top10": dict(answer_counts.most_common(10)),
            "decision_rows": len(decision_rows),
            "decision_parse_rate": _round(len(decision_rows) / n) if n else None,
            "decision_correct": decision_correct,
            "decision_accuracy": _round(decision_correct / len(decision_rows)) if decision_rows else None,
            "object_list_target_rows": len(target_rows),
            "object_list_target_mentions": target_mentions if family == "object_list" else None,
            "object_list_target_mention_rate": _round(target_mentions / len(target_rows)) if target_rows else None,
            "object_list_false_target_mentions": false_target_mentions if family == "object_list" else None,
            "object_list_false_target_mention_rate": _round(false_target_mentions / len(target_rows)) if target_rows else None,
        }
        family_summaries[family] = summary
        csv_rows.append({
            "provider": provider,
            "family": family,
            "n_rows": n,
            "raw_parse_rate": summary["raw_parse_rate"],
            "decision_parse_rate": summary["decision_parse_rate"],
            "decision_accuracy": summary["decision_accuracy"],
            "target_mention_rate": summary["object_list_target_mention_rate"],
            "false_target_mention_rate": summary["object_list_false_target_mention_rate"],
        })

    missing_families = [f for f in FAMILIES if not by_family.get(f)]
    extra_families = sorted(k for k in by_family if k not in FAMILIES)
    provider_summary = {
        "provider": provider,
        "path": _rel(path),
        "exists": path.exists(),
        "n_rows": len(rows),
        "expected_rows": EXPECTED_ROWS,
        "row_count_ok": len(rows) == EXPECTED_ROWS,
        "provider_names": provider_names,
        "provider_ok": provider_names == [provider],
        "duplicate_prediction_ids": dupes[:20],
        "n_duplicate_prediction_ids": len(dupes),
        "missing_families": missing_families,
        "extra_families": extra_families,
        "excluded_spec_blocked_families": list(SPEC_BLOCKED_FAMILIES),
        "families": family_summaries,
    }
    return provider_summary, csv_rows


def build(pred_dir: Path = DEFAULT_PRED_DIR, out_dir: Path = DEFAULT_OUT_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = _load_task_specs()
    summaries: dict[str, dict] = {}
    csv_rows: list[dict] = []
    missing: list[str] = []
    blocked = False

    for provider in PROVIDERS:
        path = _pred_path(pred_dir, provider)
        if not path.exists():
            missing.append(_rel(path))
            blocked = True
            summaries[provider] = {"provider": provider, "path": _rel(path), "exists": False}
            continue
        summary, rows = _summarize_provider(path, provider, specs)
        summaries[provider] = summary
        csv_rows.extend(rows)
        if not (summary["row_count_ok"] and summary["provider_ok"] and summary["n_duplicate_prediction_ids"] == 0):
            blocked = True

    result = {
        "schema": "certvic.v8.mechanism_probe_report.v1",
        "evidence_status": "DIAGNOSTIC_NON_EVIDENCE",
        "paper_evidence": False,
        "status": "blocked" if blocked else "complete",
        "pred_dir": _rel(pred_dir),
        "task_root": _rel(TASK_ROOT),
        "expected_providers": list(PROVIDERS),
        "expected_rows_per_provider": EXPECTED_ROWS,
        "missing_files": missing,
        "spec_blocked_families_excluded": list(SPEC_BLOCKED_FAMILIES),
        "providers": summaries,
        "interpretation_limits": [
            "Flat diagnostic rows; not a TaskItem run_eval certification path.",
            "Two-step yes/no decisions are parsed deterministically from the last yes/no token when present.",
            "Object-list target mentions are substring/list checks and are reported as diagnostic indicators.",
            "original_vs_edited is excluded because the spec marks it blocked.",
        ],
    }
    write_json(out_dir / "mechanism_probe_report.json", result)
    write_json(out_dir / "MECHANISM_PROBE_REPORT.json", result)
    _write_csv(out_dir / "v8_mechanism_probe_summary.csv", csv_rows)
    (out_dir / "MECHANISM_PROBE_REPORT.md").write_text(_render_md(result), encoding="utf-8")
    return result


def _write_csv(path: Path, rows: list[dict]) -> None:
    cols = [
        "provider", "family", "n_rows", "raw_parse_rate",
        "decision_parse_rate", "decision_accuracy",
        "target_mention_rate", "false_target_mention_rate",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: "" if row.get(c) is None else row.get(c) for c in cols})


def _render_md(result: dict) -> str:
    lines = [
        "# V8 Mechanism Probe Report",
        "",
        f"`status={result['status']}` `evidence_status={result['evidence_status']}` `paper_evidence=false`",
        "",
        "Mechanism probes are diagnostic only. The blocked two-image `original_vs_edited` family is excluded.",
        "",
        "| provider | family | rows | raw parse | decision parse | decision accuracy | target mention | false target mention |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for provider in PROVIDERS:
        pdata = result["providers"].get(provider, {})
        for family in FAMILIES:
            fam = (pdata.get("families") or {}).get(family, {})
            lines.append(
                f"| `{provider}` | {family} | {fam.get('n_rows', '')} | {fam.get('raw_parse_rate', '')} | "
                f"{fam.get('decision_parse_rate', '')} | {fam.get('decision_accuracy', '')} | "
                f"{fam.get('object_list_target_mention_rate', '')} | "
                f"{fam.get('object_list_false_target_mention_rate', '')} |"
            )
    lines += [
        "",
        "## Integrity",
        "",
    ]
    for provider in PROVIDERS:
        pdata = result["providers"].get(provider, {})
        lines.append(
            f"- `{provider}`: rows={pdata.get('n_rows')} expected={pdata.get('expected_rows')} "
            f"provider_ok={pdata.get('provider_ok')} duplicates={pdata.get('n_duplicate_prediction_ids')}"
        )
    lines += [
        "",
        "## Limits",
        "",
        "- Diagnostic-only, not paper evidence.",
        "- `original_vs_edited` remains SPEC_BLOCKED until the two-image interface exists.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pred-dir", default=str(DEFAULT_PRED_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args(argv)
    result = build(Path(args.pred_dir), Path(args.out_dir))
    print(json.dumps({"status": result["status"], "missing": result["missing_files"]}, sort_keys=True))


if __name__ == "__main__":
    main()
