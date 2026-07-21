"""Generate a data card from manifests (recipe-first, no pixels)."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from certvic.io import read_jsonl


def build_data_card(manifests_dir: str, out_path: str) -> dict:
    md = Path(manifests_dir)
    sources = 0
    masks = 0
    license_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    families: Counter[str] = Counter()
    for jsonl in sorted(md.glob("*.jsonl")):
        rows = read_jsonl(str(jsonl))
        for r in rows:
            if "source_id" in r and "mask_id" not in r and "edit_id" not in r:
                sources += 1
                license_counts[str(r.get("license_category", "unknown"))] += 1
            if "mask_id" in r:
                masks += 1
                if r.get("label_id") is not None:
                    label_counts[str(r.get("label_id"))] += 1
            if r.get("task_family"):
                families[str(r["task_family"])] += 1

    stats = {
        "sources": sources,
        "masks": masks,
        "license_categories": dict(license_counts),
        "top_labels": dict(label_counts.most_common(20)),
        "task_families": dict(families),
    }
    lines = [
        "# CertVIC Generated Data Card",
        "",
        "Recipe-first: this card describes pointers and metadata only. No pixels are redistributed.",
        "",
        f"- sources: {sources}",
        f"- masks: {masks}",
        f"- license categories: {dict(license_counts)}",
        f"- task families: {dict(families)}",
        "",
        "## Intended use",
        "Evaluation of decision consistency under controlled single-factor interventions. Stimuli only; no deployment claims.",
        "",
        "## Limitations",
        "Edits may contain artifacts; labels depend on edit validity; domains/edit families are limited; pixels must be regenerated from source pointers.",
        "",
    ]
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    return stats


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate a recipe-first data card")
    parser.add_argument("--manifests", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(build_data_card(args.manifests, args.out), sort_keys=True))


if __name__ == "__main__":
    main()
