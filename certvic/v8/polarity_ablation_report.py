"""Build V8 prompt-polarity diagnostic reports from flat Kaggle prediction rows.

The V8 polarity run is not a TaskItem pair run_eval artifact. It is a flat
diagnostic schema with one prediction row per prompt/image variant. This module
therefore scores only what the rows and deterministic task manifests contain:
parse rates, answer distributions, and row accuracy against the current
task-manifest gold. Raw predictions are immutable inputs; their embedded gold
metadata is audited but is not authoritative because task bugs may be repaired
after inference.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from certvic.io import write_json

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "data/results/main_real_200"
DEFAULT_PRED_DIR = RESULTS / "kaggle_polarity"
DEFAULT_TASK_DIR = RESULTS / "prompt_ablations"
DEFAULT_OUT_DIR = RESULTS / "v8_upgrade"
PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")
FAMILIES = ("negative", "pixel_only", "positive", "short")
EXPECTED_ROWS = 728


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _pred_path(pred_dir: Path, provider: str) -> Path:
    return pred_dir / f"pred_{provider}_polarity.jsonl"


def _round(v: float | None) -> float | None:
    return round(v, 4) if v is not None else None


def _load_task_gold(task_dir: Path) -> tuple[dict[tuple[str, str, str], str], dict]:
    gold: dict[tuple[str, str, str], str] = {}
    missing_files: list[str] = []
    duplicate_keys: list[str] = []
    invalid_gold: list[str] = []
    for family in FAMILIES:
        path = task_dir / family / "tasks.jsonl"
        if not path.exists():
            missing_files.append(_rel(path))
            continue
        for row in _read_jsonl(path):
            key = (family, str(row.get("item_id")), str(row.get("image_variant")))
            key_text = "::".join(key)
            if key in gold:
                duplicate_keys.append(key_text)
                continue
            answer = row.get("gold_answer")
            if answer not in {"yes", "no"}:
                invalid_gold.append(key_text)
                continue
            gold[key] = answer
    audit = {
        "task_dir": _rel(task_dir),
        "gold_source": "current_task_manifest",
        "n_task_gold_rows": len(gold),
        "expected_task_gold_rows": EXPECTED_ROWS,
        "row_count_ok": len(gold) == EXPECTED_ROWS,
        "missing_files": missing_files,
        "duplicate_keys": duplicate_keys[:20],
        "n_duplicate_keys": len(duplicate_keys),
        "invalid_gold_keys": invalid_gold[:20],
        "n_invalid_gold_keys": len(invalid_gold),
    }
    audit["valid"] = bool(
        audit["row_count_ok"]
        and not audit["missing_files"]
        and audit["n_duplicate_keys"] == 0
        and audit["n_invalid_gold_keys"] == 0
    )
    return gold, audit


def _summarize_provider(
    path: Path,
    provider: str,
    task_gold: dict[tuple[str, str, str], str],
) -> tuple[dict, list[dict]]:
    rows = _read_jsonl(path)
    ids = [r.get("prediction_id") or f"{r.get('item_id')}::{r.get('image_variant')}::{i}" for i, r in enumerate(rows)]
    dupes = sorted(k for k, n in Counter(ids).items() if n > 1)
    provider_names = sorted({r.get("provider_name") for r in rows})

    by_family: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        fam = (r.get("metadata") or {}).get("ablation_family") or (r.get("metadata") or {}).get("polarity")
        by_family[str(fam)].append(r)

    family_summaries: dict[str, dict] = {}
    csv_rows: list[dict] = []
    missing_task_gold_keys: list[str] = []
    raw_metadata_gold_mismatches: list[str] = []
    for family in FAMILIES:
        fr = by_family.get(family, [])
        n = len(fr)
        parse_ok = sum(1 for r in fr if r.get("parse_ok") is True and r.get("parsed_answer") in {"yes", "no"})
        answer_counts = Counter(str(r.get("parsed_answer")) for r in fr)
        gold_rows: list[tuple[dict, str]] = []
        family_missing_task_gold: list[str] = []
        family_raw_mismatches: list[str] = []
        for r in fr:
            key = (family, str(r.get("item_id")), str(r.get("image_variant")))
            key_text = "::".join(key)
            manifest_gold = task_gold.get(key)
            if manifest_gold not in {"yes", "no"}:
                family_missing_task_gold.append(key_text)
                missing_task_gold_keys.append(key_text)
                continue
            gold_rows.append((r, manifest_gold))
            raw_gold = (r.get("metadata") or {}).get("gold_answer")
            if raw_gold != manifest_gold:
                family_raw_mismatches.append(key_text)
                raw_metadata_gold_mismatches.append(key_text)
        correct = sum(
            1
            for r, manifest_gold in gold_rows
            if r.get("parse_ok") is True and r.get("parsed_answer") == manifest_gold
        )
        pairs: dict[tuple[str, str], dict[str, str | None]] = defaultdict(dict)
        gold_pairs: dict[tuple[str, str], dict[str, str | None]] = defaultdict(dict)
        for r in fr:
            key = (str(r.get("item_id")), family)
            variant = str(r.get("image_variant"))
            pairs[key][variant] = r.get("parsed_answer")
            gold_pairs[key][variant] = task_gold.get((family, str(r.get("item_id")), variant))
        pair_rows = [
            (pairs[k].get("original"), pairs[k].get("edited"), gold_pairs[k].get("original"), gold_pairs[k].get("edited"))
            for k in sorted(pairs)
            if "original" in pairs[k] and "edited" in pairs[k]
        ]
        changed = sum(1 for orig, edited, _, _ in pair_rows if orig in {"yes", "no"} and edited in {"yes", "no"} and orig != edited)
        both_correct = sum(
            1
            for orig, edited, gold_orig, gold_edited in pair_rows
            if orig == gold_orig and edited == gold_edited and orig in {"yes", "no"} and edited in {"yes", "no"}
        )
        summary = {
            "n_rows": n,
            "expected_rows": EXPECTED_ROWS // len(FAMILIES),
            "parse_ok": parse_ok,
            "parse_rate": _round(parse_ok / n) if n else None,
            "answer_counts": dict(sorted(answer_counts.items())),
            "gold_rows": len(gold_rows),
            "gold_source": "current_task_manifest",
            "n_missing_task_gold": len(family_missing_task_gold),
            "raw_metadata_gold_mismatches": len(family_raw_mismatches),
            "row_correct": correct,
            "row_accuracy": _round(correct / len(gold_rows)) if gold_rows else None,
            "paired_items": len(pair_rows),
            "answer_changed_pairs": changed,
            "answer_changed_rate": _round(changed / len(pair_rows)) if pair_rows else None,
            "both_rows_correct_pairs": both_correct,
            "both_rows_correct_rate": _round(both_correct / len(pair_rows)) if pair_rows else None,
        }
        family_summaries[family] = summary
        csv_rows.append({
            "provider": provider,
            "family": family,
            "n_rows": n,
            "parse_rate": summary["parse_rate"],
            "row_accuracy": summary["row_accuracy"],
            "paired_items": summary["paired_items"],
            "answer_changed_rate": summary["answer_changed_rate"],
            "both_rows_correct_rate": summary["both_rows_correct_rate"],
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
        "gold_source": "current_task_manifest",
        "n_missing_task_gold": len(missing_task_gold_keys),
        "missing_task_gold_keys": missing_task_gold_keys[:20],
        "raw_metadata_gold_mismatches": len(raw_metadata_gold_mismatches),
        "raw_metadata_gold_mismatch_keys": raw_metadata_gold_mismatches[:20],
        "missing_families": missing_families,
        "extra_families": extra_families,
        "families": family_summaries,
    }
    return provider_summary, csv_rows


def build(
    pred_dir: Path = DEFAULT_PRED_DIR,
    out_dir: Path = DEFAULT_OUT_DIR,
    task_dir: Path = DEFAULT_TASK_DIR,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    task_gold, task_manifest_audit = _load_task_gold(task_dir)
    summaries: dict[str, dict] = {}
    csv_rows: list[dict] = []
    missing: list[str] = []
    blocked = not task_manifest_audit["valid"]

    for provider in PROVIDERS:
        path = _pred_path(pred_dir, provider)
        if not path.exists():
            missing.append(_rel(path))
            blocked = True
            summaries[provider] = {"provider": provider, "path": _rel(path), "exists": False}
            continue
        summary, rows = _summarize_provider(path, provider, task_gold)
        summaries[provider] = summary
        csv_rows.extend(rows)
        if not (
            summary["row_count_ok"]
            and summary["provider_ok"]
            and summary["n_duplicate_prediction_ids"] == 0
            and summary["n_missing_task_gold"] == 0
        ):
            blocked = True

    result = {
        "schema": "certvic.v8.polarity_ablation_report.v2",
        "evidence_status": "DIAGNOSTIC_NON_EVIDENCE",
        "paper_evidence": False,
        "status": "blocked" if blocked else "complete",
        "pred_dir": _rel(pred_dir),
        "task_manifest_audit": task_manifest_audit,
        "expected_providers": list(PROVIDERS),
        "expected_rows_per_provider": EXPECTED_ROWS,
        "missing_files": missing,
        "providers": summaries,
        "interpretation_limits": [
            "Flat diagnostic rows; not a TaskItem run_eval certification path.",
            "The current deterministic task manifests are authoritative for gold labels.",
            "Embedded raw-prediction gold is preserved and audited; mismatches are not used for scoring.",
            "This does not promote any pilot result to paper evidence.",
        ],
    }
    write_json(out_dir / "polarity_ablation_report.json", result)
    write_json(out_dir / "POLARITY_ABLATION_REPORT.json", result)
    _write_csv(out_dir / "v8_polarity_ablation_summary.csv", csv_rows)
    (out_dir / "POLARITY_ABLATION_REPORT.md").write_text(_render_md(result), encoding="utf-8")
    return result


def _write_csv(path: Path, rows: list[dict]) -> None:
    cols = [
        "provider", "family", "n_rows", "parse_rate", "row_accuracy",
        "paired_items", "answer_changed_rate", "both_rows_correct_rate",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: "" if row.get(c) is None else row.get(c) for c in cols})


def _render_md(result: dict) -> str:
    lines = [
        "# V8 Prompt-Polarity Ablation Report",
        "",
        f"`status={result['status']}` `evidence_status={result['evidence_status']}` `paper_evidence=false`",
        "",
        "These are flat diagnostic predictions. Metrics below are parse rates, answer distributions, and row accuracy scored against the current deterministic task manifests.",
        "",
        "| provider | family | rows | parse rate | row accuracy | pair update rate | both rows correct |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for provider in PROVIDERS:
        pdata = result["providers"].get(provider, {})
        for family in FAMILIES:
            fam = (pdata.get("families") or {}).get(family, {})
            lines.append(
                f"| `{provider}` | {family} | {fam.get('n_rows', '')} | {fam.get('parse_rate', '')} | "
                f"{fam.get('row_accuracy', '')} | {fam.get('answer_changed_rate', '')} | "
                f"{fam.get('both_rows_correct_rate', '')} |"
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
            f"provider_ok={pdata.get('provider_ok')} duplicates={pdata.get('n_duplicate_prediction_ids')} "
            f"missing_task_gold={pdata.get('n_missing_task_gold')} "
            f"raw_gold_mismatches={pdata.get('raw_metadata_gold_mismatches')}"
        )
    lines += [
        "",
        "## Limits",
        "",
        "- Diagnostic-only, not paper evidence.",
        "- No accuracy metric is computed without task-manifest gold or a deterministic parse rule.",
        "- Embedded raw-prediction gold is an audited provenance field, not the scoring authority.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pred-dir", default=str(DEFAULT_PRED_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--task-dir", default=str(DEFAULT_TASK_DIR))
    args = parser.parse_args(argv)
    result = build(Path(args.pred_dir), Path(args.out_dir), Path(args.task_dir))
    print(json.dumps({"status": result["status"], "missing": result["missing_files"]}, sort_keys=True))


if __name__ == "__main__":
    main()
