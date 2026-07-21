"""Label-policy diagnostics over an ADE20K mask manifest.

Reads a masks manifest and a label policy, then reports label frequency,
per-family eligibility, blocked labels, and unresolved labels. No downloads,
no GPU, no inference. Output is descriptive only and makes no evidence claims.

    python3 -m certvic.data.label_policy_report \
        --masks data/manifests/ade20k_masks.jsonl \
        --policy configs/ade20k_label_policy.yaml \
        --out-dir data/results/label_policy_report
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from certvic.data.label_policy import (
    allowed_edits_for_label,
    block_reason,
    eligible_families_for_label,
    is_label_blocked,
    is_resolved,
    load_label_policy,
    policy_provenance,
    resolve_label_name,
)
from certvic.io import read_jsonl, write_json
from certvic.schema import TaskFamily


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def build_label_policy_report(masks_path: str, policy_path: str | None, out_dir: str) -> dict:
    masks = read_jsonl(masks_path)
    policy = load_label_policy(policy_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    label_counts: Counter[int] = Counter()
    masks_by_family: dict[str, int] = defaultdict(int)
    labels_by_family: dict[str, set[int]] = defaultdict(set)
    blocked_rows: list[list] = []
    unresolved_label_ids: set[int] = set()
    unresolved_mask_count = 0
    blocked_mask_count = 0

    for mask in masks:
        label_id = mask.get("label_id")
        try:
            label_id = int(label_id)
        except (TypeError, ValueError):
            unresolved_mask_count += 1
            continue
        label_counts[label_id] += 1
        if not is_resolved(policy, label_id):
            unresolved_label_ids.add(label_id)
            unresolved_mask_count += 1
        if is_label_blocked(policy, label_id):
            blocked_mask_count += 1
        for family in eligible_families_for_label(policy, label_id):
            masks_by_family[family] += 1
            labels_by_family[family].add(label_id)

    # label_frequency.csv
    freq_rows = []
    for label_id, count in label_counts.most_common():
        freq_rows.append(
            [
                label_id,
                resolve_label_name(policy, label_id),
                count,
                is_resolved(policy, label_id),
                is_label_blocked(policy, label_id),
                ";".join(eligible_families_for_label(policy, label_id)) or "-",
                ";".join(allowed_edits_for_label(policy, label_id)) or "-",
            ]
        )
    _write_csv(
        out / "label_frequency.csv",
        ["label_id", "label_name", "mask_count", "resolved", "blocked", "eligible_families", "allowed_edits"],
        freq_rows,
    )

    # eligible_by_family.csv
    family_rows = []
    for family in sorted({f.value for f in TaskFamily} | set(masks_by_family)):
        family_rows.append([family, len(labels_by_family.get(family, set())), masks_by_family.get(family, 0)])
    _write_csv(out / "eligible_by_family.csv", ["task_family", "n_eligible_labels", "n_eligible_masks"], family_rows)

    # blocked_labels.csv
    for label_id in sorted({lid for lid in label_counts if is_label_blocked(policy, lid)}):
        blocked_rows.append(
            [label_id, resolve_label_name(policy, label_id), label_counts[label_id], block_reason(policy, label_id) or "-"]
        )
    _write_csv(out / "blocked_labels.csv", ["label_id", "label_name", "mask_count", "block_reason"], blocked_rows)

    # unresolved_labels.csv
    unresolved_rows = [
        [label_id, label_counts[label_id], "conservative_fallback_control_only"]
        for label_id in sorted(unresolved_label_ids)
    ]
    _write_csv(out / "unresolved_labels.csv", ["label_id", "mask_count", "fallback"], unresolved_rows)

    summary = {
        "masks_path": masks_path,
        "out_dir": out_dir,
        "n_masks": len(masks),
        "n_distinct_labels": len(label_counts),
        "n_resolved_labels": sum(1 for lid in label_counts if is_resolved(policy, lid)),
        "n_unresolved_labels": len(unresolved_label_ids),
        "n_blocked_labels": len(blocked_rows),
        "unresolved_mask_count": unresolved_mask_count,
        "blocked_mask_count": blocked_mask_count,
        "eligible_masks_by_family": dict(sorted(masks_by_family.items())),
        "eligible_labels_by_family": {k: len(v) for k, v in sorted(labels_by_family.items())},
        **policy_provenance(policy),
        "evidence_status": "DESCRIPTIVE_ONLY",
        "zero_cost": True,
        "vlm_inference_run": False,
    }
    write_json(out / "label_policy_summary.json", summary)
    (out / "label_policy_report.md").write_text(_render_md(summary, policy), encoding="utf-8")
    return summary


def _render_md(summary: dict, policy: dict) -> str:
    verified = summary.get("label_policy_verified")
    lines = [
        "# Label Policy Report",
        "",
        f"Policy: `{summary.get('label_policy_version')}` "
        f"({summary.get('label_policy_hash')}), verified={verified}",
        "",
    ]
    if not verified:
        lines += [
            "> WARNING: the label policy is UNVERIFIED. Confirm the label_id -> name map",
            "> against your ADE20K release before any evidence run.",
            "",
        ]
    lines += [
        f"- masks: {summary['n_masks']}",
        f"- distinct labels: {summary['n_distinct_labels']} "
        f"(resolved {summary['n_resolved_labels']}, unresolved {summary['n_unresolved_labels']}, blocked {summary['n_blocked_labels']})",
        f"- unresolved masks: {summary['unresolved_mask_count']}, blocked masks: {summary['blocked_mask_count']}",
        "",
        "## Eligible masks by family",
        "",
        "| Task family | Eligible labels | Eligible masks |",
        "| --- | --- | --- |",
    ]
    for family in sorted({f.value for f in TaskFamily} | set(summary["eligible_masks_by_family"])):
        lines.append(
            f"| {family} | {summary['eligible_labels_by_family'].get(family, 0)} | {summary['eligible_masks_by_family'].get(family, 0)} |"
        )
    lines += ["", "Generated files: label_frequency.csv, eligible_by_family.csv, blocked_labels.csv, unresolved_labels.csv, label_policy_summary.json", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="ADE20K label-policy diagnostics")
    parser.add_argument("--masks", required=True)
    parser.add_argument("--policy")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    summary = build_label_policy_report(args.masks, args.policy, args.out_dir)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
