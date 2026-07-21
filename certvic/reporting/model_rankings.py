"""Descriptive model rankings with no significance overclaim."""

from __future__ import annotations


def rank_models(rows: list[dict]) -> list[dict]:
    buckets: dict[str, list[dict]] = {}
    for row in rows:
        buckets.setdefault(str(row.get("provider_name") or row.get("model_name")), []).append(row)
    ranked: list[dict] = []
    for model, bucket in buckets.items():
        n = len(bucket)
        consistency = sum(1 for r in bucket if r.get("consistent")) / n if n else 0.0
        parse_ok = sum(1 for r in bucket if r.get("parse_ok")) / n if n else 0.0
        ranked.append(
            {
                "model": model,
                "n": n,
                "consistency_rate": round(consistency, 4),
                "parse_ok_rate": round(parse_ok, 4),
                "ranking_type": "descriptive_not_significance_tested",
            }
        )
    return sorted(ranked, key=lambda r: (-r["consistency_rate"], r["model"]))

