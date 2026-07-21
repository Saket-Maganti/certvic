"""Resume helpers for prediction JSONL."""

from __future__ import annotations

from certvic.io import read_jsonl


def prediction_key(record: dict) -> tuple[str, str, str]:
    return (record["run_id"], record["item_id"], record["image_variant"])


def load_completed_keys(path: str) -> set[tuple[str, str, str]]:
    return {prediction_key(record) for record in read_jsonl(path)}
