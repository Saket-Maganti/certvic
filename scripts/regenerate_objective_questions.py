"""Regenerate objective, label-balanced questions for existing edits (no new diffusion).

The v1 templates asked subjective agent-action questions ("Should the agent
proceed?") and made every intervention a yes->no flip (answer_original 93% yes,
answer_edited 100% no) -- so fixed-answer baselines scored a huge gap and the
metric couldn't isolate visual updating. All our edits make the target object
absent/hidden (remove/occlude/displace-as-removal), so an OBJECTIVE presence/
visibility question works for every edit and directly tests edit perception.
Polarity is alternated for ~50/50 labels. CPU-only; no evidence claims.
"""

from __future__ import annotations

import argparse
import csv
import json

from certvic.io import read_jsonl, write_jsonl

YES_NO = "Respond with exactly one token: yes or no."


def load_names(objinfo_path: str) -> dict[int, str]:
    names: dict[int, str] = {}
    with open(objinfo_path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader, None)  # header: Idx Ratio Train Val Name
        for row in reader:
            if len(row) >= 5:
                names[int(row[0])] = row[4].split(",")[0].strip()
    return names


def _label_id(row: dict) -> int | None:
    mid = str(row.get("mask_id") or "")
    if "label_" in mid:
        try:
            return int(mid.split("label_")[-1])
        except ValueError:
            return None
    return row.get("label_id")


def regenerate(tasks_path: str, objinfo_path: str, out_path: str) -> dict:
    names = load_names(objinfo_path)
    rows = read_jsonl(tasks_path)
    # Alternate polarity over a stable ordering for an exact ~50/50 label balance.
    order = sorted(range(len(rows)), key=lambda i: rows[i].get("item_id", ""))
    polarity_a = {order[k]: (k % 2 == 0) for k in range(len(order))}
    n_unresolved = 0
    for i, r in enumerate(rows):
        lid = _label_id(r)
        obj = names.get(lid) if lid is not None else None
        if not obj:
            obj = "object"
            n_unresolved += 1
        if polarity_a[i]:
            q = f"Is there a clearly visible {obj} in the image? {YES_NO}"
            ao, ae = "yes", "no"
        else:
            q = f"Is the {obj} absent or not clearly visible in the image? {YES_NO}"
            ao, ae = "no", "yes"
        r["question_original"] = q
        r["question_edited"] = q
        r["answer_original"] = ao
        r["answer_edited"] = ae
        r["required_change"] = "change"
        r["question_object"] = obj
    write_jsonl(out_path, rows)
    import collections
    return {
        "in": tasks_path,
        "out": out_path,
        "n": len(rows),
        "answer_original_balance": dict(collections.Counter(r["answer_original"] for r in rows)),
        "answer_edited_balance": dict(collections.Counter(r["answer_edited"] for r in rows)),
        "objects": dict(collections.Counter(r["question_object"] for r in rows)),
        "n_unresolved_labels": n_unresolved,
        "evidence_claims_made": False,
    }


def main(argv: list[str] | None = None) -> None:
    import pathlib
    repo = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Regenerate objective balanced-polarity questions for existing edits")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--objinfo", default=str(repo / "ade20k_root/ADEChallengeData2016/objectInfo150.txt"))
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(regenerate(args.tasks, args.objinfo, args.out), sort_keys=True))


if __name__ == "__main__":
    main()
