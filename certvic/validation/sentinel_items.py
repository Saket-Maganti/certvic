"""Optional sentinel-item helpers for human review QC."""

from __future__ import annotations


def sentinel_summary(rows: list[dict]) -> dict:
    sentinels = [row for row in rows if str(row.get("is_sentinel", "")).lower() in {"1", "true", "yes"}]
    failures = [row for row in sentinels if str(row.get("sentinel_pass", "")).lower() in {"0", "false", "no"}]
    return {
        "sentinels_optional": True,
        "n_sentinels": len(sentinels),
        "n_sentinel_failures": len(failures),
    }

